# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import json
import os
import shutil
import tarfile
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import semver

from app.schemas.update import (
    ChannelSchema,
    ReleaseNotesSchema,
    UpdateCheckRequest,
    UpdateCheckResponse,
    UpdateDownloadResponse,
    UpdateHistoryResponse,
    UpdateInstallResponse,
    UpdateRollbackResponse,
    UpdateSettingsSchema,
    UpdateVerifyResponse,
    VersionInfoSchema,
)
from app.services.update_service import (
    DEFAULT_SETTINGS,
    ReleaseChannel,
    UpdateHistoryEntry,
    UpdateInfo,
    UpdateService,
    UpdateStatus,
    compare_versions,
    parse_semver,
)

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519, padding, rsa
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False


@pytest.fixture
def temp_service_dir(tmp_path):
    update_dir = tmp_path / "updates"
    history_file = tmp_path / "update-history.json"
    settings_file = tmp_path / "update-settings.json"
    releases_file = tmp_path / "update-releases.json"
    update_dir.mkdir(parents=True, exist_ok=True)
    return {
        "update_dir": update_dir,
        "history_file": history_file,
        "settings_file": settings_file,
        "releases_file": releases_file,
    }


@pytest.fixture
def update_service(temp_service_dir):
    service = UpdateService(
        current_version="1.0.0",
        repo_owner="amf",
        repo_name="automated-manuscript-formatter",
        update_dir=temp_service_dir["update_dir"],
        history_file=temp_service_dir["history_file"],
        settings_file=temp_service_dir["settings_file"],
        releases_file=temp_service_dir["releases_file"],
    )
    return service


class TestVersionComparisonAndSemver:
    """Test semver parsing and version comparison logic."""

    def test_parse_semver_valid(self):
        v1 = parse_semver("v1.2.3")
        assert v1 == semver.Version(1, 2, 3)

        v2 = parse_semver("2.0.0-beta.1")
        assert v2.major == 2
        assert v2.prerelease == "beta.1"

    def test_parse_semver_fallback(self):
        v = parse_semver("invalid.version.str")
        assert isinstance(v, semver.Version)

    def test_compare_versions(self):
        assert compare_versions("1.2.0", "1.1.0") == 1
        assert compare_versions("1.0.0", "1.0.0") == 0
        assert compare_versions("1.0.0", "2.0.0") == -1
        assert compare_versions("v2.1.0", "2.0.0") == 1

    def test_version_info_schema(self, update_service):
        info = update_service.get_version_info()
        schema = VersionInfoSchema(**info)
        assert schema.current_version == "1.0.0"
        assert schema.channel == "stable"
        assert isinstance(schema.history_count, int)


class TestUpdateChannels:
    """Test channel distribution configuration and filtering."""

    def test_get_channels(self, update_service):
        channels = update_service.get_channels()
        assert len(channels) >= 4
        channel_ids = [c["id"] for c in channels]
        assert "stable" in channel_ids
        assert "beta" in channel_ids
        assert "nightly" in channel_ids
        assert "pre-release" in channel_ids

    def test_update_settings_channel(self, update_service):
        res = update_service.update_settings({"channel": "beta"})
        assert res["channel"] == "beta"
        assert update_service.get_settings()["channel"] == "beta"

    def test_filter_by_channel(self, update_service):
        cand_stable = UpdateInfo(version="1.1.0", channel=ReleaseChannel.STABLE, prerelease=False)
        cand_beta = UpdateInfo(version="1.2.0-beta.1", channel=ReleaseChannel.BETA, prerelease=True)

        assert update_service._filter_by_channel(cand_stable, "stable") is True
        assert update_service._filter_by_channel(cand_beta, "stable") is False
        assert update_service._filter_by_channel(cand_beta, "beta") is True
        assert update_service._filter_by_channel(cand_beta, "nightly") is True


class TestGitHubReleasesAndFallback:
    """Test GitHub releases API integration, caching, and fallback logic."""

    @patch("httpx.Client")
    def test_fetch_github_releases_live(self, mock_client, update_service):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "tag_name": "v1.1.0",
                "name": "Release 1.1.0",
                "published_at": "2026-07-01T12:00:00Z",
                "prerelease": False,
                "draft": False,
                "body": "Bug fixes and performance improvements.",
                "assets": [
                    {
                        "name": "amf-1.1.0.zip",
                        "browser_download_url": "https://example.com/amf-1.1.0.zip",
                        "size": 1024,
                    }
                ],
            }
        ]
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response

        releases = update_service._fetch_github_releases(force_refresh=True)
        assert len(releases) == 1
        assert releases[0]["tag_name"] == "v1.1.0"

    @patch("httpx.Client")
    def test_fetch_github_releases_fallback(self, mock_client, update_service, temp_service_dir):
        mock_client.return_value.__enter__.return_value.get.side_effect = Exception("Network offline")

        # Populate local releases file fallback
        fallback_releases = [
            {
                "tag_name": "v1.0.5",
                "name": "Local Cached Release",
                "published_at": "2026-06-01T00:00:00Z",
                "prerelease": False,
                "draft": False,
                "assets": [],
            }
        ]
        temp_service_dir["releases_file"].write_text(json.dumps(fallback_releases), encoding="utf-8")
        update_service._cached_releases = []

        releases = update_service._fetch_github_releases(force_refresh=True)
        assert len(releases) == 1
        assert releases[0]["name"] == "Local Cached Release"


class TestChecksumAndIntegrityVerification:
    """Test SHA-256 checksum calculation and verification."""

    def test_verify_checksum(self, update_service, tmp_path):
        test_file = tmp_path / "test_artifact.bin"
        test_data = b"ScholarFormAI Update Content 2026"
        test_file.write_bytes(test_data)

        import hashlib
        expected_sha = hashlib.sha256(test_data).hexdigest()

        assert update_service._verify_checksum(test_file, expected_sha, "sha256") is True
        assert update_service._verify_checksum(test_file, "0" * 64, "sha256") is False

    def test_verify_asset_integrity(self, update_service, tmp_path):
        test_file = tmp_path / "asset.zip"
        content = b"Asset payload for verification"
        test_file.write_bytes(content)

        import hashlib
        sha = hashlib.sha256(content).hexdigest()

        res = update_service.verify_asset_integrity(
            file_path=test_file,
            expected_checksum=sha,
        )
        assert res["valid"] is True
        assert res["checksum_valid"] is True
        assert res["exists"] is True
        schema = UpdateVerifyResponse(**res)
        assert schema.valid is True


class TestDigitalSignatureVerification:
    """Test ED25519 and RSA digital signature validation routines."""

    @pytest.mark.skipif(not HAS_CRYPTOGRAPHY, reason="cryptography library not installed")
    def test_ed25519_signature_verification(self, update_service):
        data = b"Enterprise release package binary data"

        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        pub_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

        signature = private_key.sign(data)

        # Test verification with raw bytes public key
        valid = update_service.verify_signature(data, signature, public_key=pub_bytes)
        assert valid is True

        # Test invalid signature
        invalid = update_service.verify_signature(data, b"X" * len(signature), public_key=pub_bytes)
        assert invalid is False

    @pytest.mark.skipif(not HAS_CRYPTOGRAPHY, reason="cryptography library not installed")
    def test_rsa_signature_verification(self, update_service):
        data = b"Enterprise RSA signed release payload"

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = private_key.public_key()
        pem_pub = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")

        # Sign using RSA-PSS
        signature_pss = private_key.sign(
            data,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256(),
        )

        valid = update_service.verify_signature(data, signature_pss, public_key=pem_pub)
        assert valid is True

        # Sign using PKCS#1 v1.5
        signature_pkcs = private_key.sign(
            data,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )

        valid_pkcs = update_service.verify_signature(data, signature_pkcs, public_key=pem_pub)
        assert valid_pkcs is True


class TestDownloadUpdateWithRetry:
    """Test retry logic and exponential backoff in download_update_with_retry."""

    @patch("httpx.Client")
    def test_download_retry_success(self, mock_client, update_service, tmp_path):
        mock_stream = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.headers = {"content-length": "100"}
        mock_response.iter_bytes.return_value = [b"chunk1_", b"chunk2_"]
        mock_stream.__enter__.return_value = mock_response

        # Fail once, then succeed
        mock_client.return_value.__enter__.return_value.stream.side_effect = [
            Exception("Transient Network Timeout"),
            mock_stream,
        ]

        upd_info = UpdateInfo(
            version="1.2.0",
            download_url="https://example.com/amf-1.2.0.zip",
        )
        update_service._pending_update = upd_info

        progress_calls = []

        def progress_cb(dl, total):
            progress_calls.append((dl, total))

        res = update_service.download_update_with_retry(
            version="1.2.0",
            max_retries=3,
            backoff_factor=0.01,
            progress_callback=progress_cb,
        )

        assert res["success"] is True
        assert res["version"] == "1.2.0"
        assert len(progress_calls) > 0
        assert Path(res["path"]).exists()

    @patch("httpx.Client")
    def test_download_retry_exhausted(self, mock_client, update_service):
        mock_client.return_value.__enter__.return_value.stream.side_effect = Exception("Persistent connection error")

        upd_info = UpdateInfo(
            version="1.3.0",
            download_url="https://example.com/amf-1.3.0.zip",
        )
        update_service._pending_update = upd_info

        res = update_service.download_update_with_retry(
            version="1.3.0",
            max_retries=2,
            backoff_factor=0.01,
        )

        assert res["success"] is False
        assert "Download failed after 2 retries" in res["error"]


class TestOfflineUpdateInstallation:
    """Test offline archive (.zip / .tar.gz) installation logic."""

    def test_install_offline_zip_with_manifest(self, update_service, tmp_path):
        archive_dir = tmp_path / "package"
        archive_dir.mkdir()

        manifest = {"version": "2.0.0", "description": "Enterprise Offline Package"}
        (archive_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (archive_dir / "app_file.txt").write_text("Offline Application Content", encoding="utf-8")

        zip_path = tmp_path / "offline_update.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            for file in archive_dir.iterdir():
                zf.write(file, arcname=file.name)

        res = update_service.install_offline_update(archive_path=zip_path)
        assert res["success"] is True
        assert res["version"] == "2.0.0"
        assert update_service.current_version == "2.0.0"

    def test_install_offline_targz_with_manifest(self, update_service, tmp_path):
        archive_dir = tmp_path / "tar_package"
        archive_dir.mkdir()

        manifest = {"version": "2.1.0"}
        (archive_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (archive_dir / "module.py").write_text("# Offline module", encoding="utf-8")

        tar_path = tmp_path / "offline_update.tar.gz"
        with tarfile.open(tar_path, "w:gz") as tf:
            for file in archive_dir.iterdir():
                tf.add(file, arcname=file.name)

        res = update_service.install_offline_update(archive_path=tar_path)
        assert res["success"] is True
        assert res["version"] == "2.1.0"
        assert update_service.current_version == "2.1.0"

    def test_install_offline_missing_archive(self, update_service, tmp_path):
        missing_path = tmp_path / "non_existent.zip"
        res = update_service.install_offline_update(archive_path=missing_path)
        assert res["success"] is False
        assert "not found" in res["error"].lower()


class TestRollbackAndHistory:
    """Test rollback snapshot restoration and audit log history tracking."""

    def test_rollback_and_history(self, update_service, tmp_path):
        # Create initial fake installation state
        initial_version = update_service.current_version

        # Manually create backup snapshot directory for version 1.0.0
        backup_dir = update_service.update_dir / "backups" / f"v{initial_version}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        (backup_dir / "previous_version_marker.txt").write_text("V1 Backup Marker", encoding="utf-8")

        # Simulate update to 1.1.0
        entry = UpdateHistoryEntry(
            version="1.1.0",
            channel=ReleaseChannel.STABLE,
            success=True,
            from_version=initial_version,
        )
        update_service._save_history_entry(entry)
        update_service.current_version = "1.1.0"

        history = update_service.get_history()
        assert len(history) >= 1

        # Perform rollback to 1.0.0
        rollback_res = update_service.rollback(target_version=initial_version)
        assert rollback_res["success"] is True
        assert rollback_res["version"] == initial_version
        assert update_service.current_version == initial_version
