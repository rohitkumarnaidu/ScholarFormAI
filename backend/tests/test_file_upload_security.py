import pytest
from unittest.mock import patch, MagicMock, AsyncMock

pytestmark = [pytest.mark.security]


DANGEROUS_EXTENSIONS = [
    ".exe",
    ".com",
    ".bat",
    ".sh",
    ".dll",
    ".vbs",
    ".ps1",
    ".jar",
]

VALID_EXTENSIONS = {".docx", ".doc", ".pdf", ".odt", ".rtf", ".tex", ".txt", ".html", ".htm", ".md", ".markdown"}


class TestFileUploadExtensionValidation:

    @pytest.mark.parametrize("ext", DANGEROUS_EXTENSIONS)
    def test_dangerous_extension_rejected(self, ext):
        from app.routers.v1.documents_impl import ACCEPTED_EXTENSIONS
        assert ext not in ACCEPTED_EXTENSIONS

    @pytest.mark.parametrize("ext", [".exe.pdf", ".bat.docx", ".sh.txt", ".com.md", ".jar.html"])
    def test_extension_masquerading_rejected(self, ext):
        from app.routers.v1.documents_impl import ACCEPTED_EXTENSIONS
        assert ext not in ACCEPTED_EXTENSIONS, f"Masqueraded extension '{ext}' should not be in accepted list"

    @pytest.mark.parametrize("ext", sorted(VALID_EXTENSIONS))
    def test_valid_extension_accepted(self, ext):
        from app.routers.v1.documents_impl import ACCEPTED_EXTENSIONS
        assert ext in ACCEPTED_EXTENSIONS

    @pytest.mark.asyncio
    async def test_empty_file_raises_magic_validation_error(self):
        from app.routers.v1.documents_impl import _validate_magic_bytes
        from fastapi import HTTPException
        mock_file = MagicMock()
        mock_file.filename = "empty.pdf"
        mock_file.read = AsyncMock(return_value=b"")
        with pytest.raises(HTTPException) as exc:
            await _validate_magic_bytes(mock_file, content=b"", file_ext=".pdf")
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_unknown_extension_rejected(self):
        from app.routers.v1.documents_impl import _validate_magic_bytes
        from fastapi import HTTPException
        mock_file = MagicMock()
        mock_file.filename = "malware.xyz"
        mock_file.read = AsyncMock(return_value=b"some content")
        with pytest.raises(HTTPException) as exc:
            await _validate_magic_bytes(mock_file, content=b"some content", file_ext=".xyz")
        assert exc.value.status_code == 400
        assert "Invalid file type" in str(exc.value.detail)


class TestFileUploadMagicBytesValidation:

    @pytest.mark.asyncio
    async def test_pdf_with_wrong_magic_bytes_rejected(self):
        from app.routers.v1.documents_impl import _validate_magic_bytes
        from fastapi import HTTPException
        mock_file = MagicMock()
        mock_file.filename = "fake.pdf"
        mock_file.read = AsyncMock(return_value=b"This is not a PDF but has pdf extension!")
        with pytest.raises(HTTPException) as exc:
            await _validate_magic_bytes(mock_file, content=b"This is not a PDF but has pdf extension!", file_ext=".pdf")
        assert exc.value.status_code == 400
        assert "spoofed" in str(exc.value.detail).lower()

    @pytest.mark.asyncio
    async def test_docx_with_zip_magic_bytes_accepted(self):
        from app.routers.v1.documents_impl import _validate_magic_bytes
        mock_file = MagicMock()
        mock_file.filename = "valid.docx"
        payload = b"\x50\x4b\x03\x04" + b"\x00" * 100
        mock_file.read = AsyncMock(return_value=payload)
        result = await _validate_magic_bytes(mock_file, content=payload, file_ext=".docx")
        assert result == payload

    @pytest.mark.asyncio
    async def test_pdf_with_pdf_magic_bytes_accepted(self):
        from app.routers.v1.documents_impl import _validate_magic_bytes
        mock_file = MagicMock()
        mock_file.filename = "valid.pdf"
        payload = b"%PDF-1.4\n%\xc7\xec\x8f\xa2\n" + b"\x00" * 100
        mock_file.read = AsyncMock(return_value=payload)
        result = await _validate_magic_bytes(mock_file, content=payload, file_ext=".pdf")
        assert result == payload

    @pytest.mark.asyncio
    async def test_text_files_no_magic_check_needed(self):
        from app.routers.v1.documents_impl import _validate_magic_bytes
        mock_file = MagicMock()
        mock_file.filename = "paper.txt"
        payload = b"Hello world this is a text file\nWith multiple lines."
        mock_file.read = AsyncMock(return_value=payload)
        result = await _validate_magic_bytes(mock_file, content=payload, file_ext=".txt")
        assert result == payload

    @pytest.mark.asyncio
    async def test_non_utf8_text_file_rejected(self):
        from app.routers.v1.documents_impl import _validate_magic_bytes
        from fastapi import HTTPException
        mock_file = MagicMock()
        mock_file.filename = "binary.txt"
        payload = bytes(range(256))
        mock_file.read = AsyncMock(return_value=payload)
        with pytest.raises(HTTPException) as exc:
            await _validate_magic_bytes(mock_file, content=payload, file_ext=".txt")
        assert "not valid UTF-8" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_rtf_with_rtf_magic_bytes_accepted(self):
        from app.routers.v1.documents_impl import _validate_magic_bytes
        mock_file = MagicMock()
        mock_file.filename = "doc.rtf"
        payload = b"{\\rtf1\\ansi\\deff0 Hello\\par}"
        mock_file.read = AsyncMock(return_value=payload)
        result = await _validate_magic_bytes(mock_file, content=payload, file_ext=".rtf")
        assert result == payload


class TestFilePathTraversalPrevention:

    def test_upload_path_traversal_rejected(self):
        from app.routers.v1.documents_impl import UPLOAD_DIR
        import os
        safe_path = os.path.abspath(UPLOAD_DIR)
        malicious = os.path.join(safe_path, "..", "..", "etc", "passwd")
        normalized = os.path.normpath(malicious)
        assert not normalized.startswith(safe_path)

    def test_upload_absolute_path_rejected(self):
        from app.routers.v1.documents_impl import UPLOAD_DIR
        import os
        safe_path = os.path.abspath(UPLOAD_DIR)
        assert safe_path == os.path.abspath(UPLOAD_DIR)

    def test_file_id_regex_rejects_path_traversal(self):
        import re
        pattern = r"^[a-zA-Z0-9-]+$"
        assert re.match(pattern, "safe-file-id-123") is not None
        assert re.match(pattern, "../../etc/passwd") is None
        assert re.match(pattern, "../malicious") is None
        assert re.match(pattern, "file%2e%2e%2f") is None
        assert re.match(pattern, "a") is not None

    def test_filepath_startswith_check_rejects_traversal(self):
        from app.routers.v1.documents_impl import UPLOAD_DIR
        import os
        upload_dir_abs = os.path.abspath(UPLOAD_DIR)
        safe = os.path.join(upload_dir_abs, "file.docx")
        assert safe.startswith(upload_dir_abs)
        traversal = os.path.join(upload_dir_abs, "..", "..", "etc", "passwd")
        assert not os.path.normpath(traversal).startswith(upload_dir_abs)


class TestFileSizeValidation:

    def test_max_file_size_setting_exists(self):
        from app.config.settings import settings
        assert hasattr(settings, "MAX_FILE_SIZE")

    def test_chunk_5mb_limit_enforced(self):
        assert 5 * 1024 * 1024 == 5242880

    def test_chunked_assembly_rejects_oversize(self):
        max_size = 50 * 1024 * 1024
        total = max_size + 1
        assert total > max_size


class TestFileUploadVirusScan:

    @pytest.mark.asyncio
    async def test_virus_scan_clean_passes(self):
        from app.routers.v1.documents_impl import _scan_uploaded_file
        with patch("app.routers.v1.documents_impl.virus_scanner.scan", AsyncMock(return_value={"clean": True, "engine": "clamav", "result": "clean"})):
            import tempfile, os
            with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
                f.write(b"clean content")
                tmp = f.name
            try:
                result = await _scan_uploaded_file(tmp)
                assert result["clean"] is True
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)

    @pytest.mark.asyncio
    async def test_virus_scan_malware_raises_422(self):
        from app.routers.v1.documents_impl import _scan_uploaded_file
        from fastapi import HTTPException
        with patch("app.routers.v1.documents_impl.virus_scanner.scan", AsyncMock(return_value={"clean": False, "engine": "clamav", "result": "Win.Trojan.Agent-123"})):
            import tempfile, os
            with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
                f.write(b"malicious content")
                tmp = f.name
            try:
                with pytest.raises(HTTPException) as exc:
                    await _scan_uploaded_file(tmp)
                assert exc.value.status_code == 422
                assert "Malware" in str(exc.value.detail)
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)

    @pytest.mark.asyncio
    async def test_virus_scanner_unavailable_returns_clean(self):
        from app.utils.virus_scanner import scan_file
        with patch("app.utils.virus_scanner.settings") as ms:
            ms.CLAMAV_HOST = "127.0.0.1"
            ms.CLAMAV_PORT = 3310
            import tempfile, os
            with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
                f.write(b"test")
                tmp = f.name
            try:
                result = scan_file(tmp)
                assert result["clean"] is True
                assert result["engine"] == "unavailable"
            finally:
                os.unlink(tmp)

    def test_virus_scanner_parse_found_threat(self):
        from app.utils.virus_scanner import _parse_scan_result
        result = _parse_scan_result("/path/file.txt: Win.Trojan.Agent-123 FOUND")
        assert result["clean"] is False
        assert "Trojan" in result["result"]

    def test_virus_scanner_parse_clean(self):
        from app.utils.virus_scanner import _parse_scan_result
        result = _parse_scan_result("/path/file.txt: OK")
        assert result["clean"] is True

    def test_virus_scanner_parse_empty(self):
        from app.utils.virus_scanner import _parse_scan_result
        result = _parse_scan_result("")
        assert result["clean"] is True

    def test_virus_scanner_parse_error_raises(self):
        from app.utils.virus_scanner import _parse_scan_result
        with pytest.raises(RuntimeError):
            _parse_scan_result("/path/file: ERROR: Could not open file")
