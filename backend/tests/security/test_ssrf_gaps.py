# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Enterprise SSRF gap coverage — validates that _sanitize_url blocks
private / internal IP ranges and hostnames in addition to the original
metadata-service blocklist.

Reference
---------
- ``app/routers/v1/providers.py`` : SSRF_BLOCKED_HOSTS, _sanitize_url
- ``tests/test_ssrf_prevention.py`` — gap tests upgraded from "not blocked"
  to "now blocked" assertions.

Known Limitations
-----------------
- DNS rebinding: hostnames that resolve to a private IP at connect-time are
  NOT detected because _sanitize_url only inspects the literal URL string.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.security]


class TestSSRFPrivateRangeBlocking:
    """RFC 1918 and loopback ranges must be rejected by _sanitize_url."""

    def test_block_10_dot_range(self):
        from app.routers.v1.providers import _sanitize_url

        for ip in ("10.0.0.1", "10.255.255.255", "10.1.2.3", "10.0.0.0"):
            with pytest.raises(Exception) as exc:
                _sanitize_url(f"http://{ip}/api")
            assert "host not allowed" in str(exc.value.detail).lower()

    def test_block_172_16_dot_range(self):
        from app.routers.v1.providers import _sanitize_url

        for ip in ("172.16.0.1", "172.20.0.1", "172.31.255.255"):
            with pytest.raises(Exception) as exc:
                _sanitize_url(f"http://{ip}/api")
            assert "host not allowed" in str(exc.value.detail).lower()

    def test_block_172_32_is_public(self):
        from app.routers.v1.providers import _sanitize_url

        result = _sanitize_url("http://172.32.0.1/api")
        assert result is not None

    def test_block_192_168_range(self):
        from app.routers.v1.providers import _sanitize_url

        for ip in ("192.168.0.1", "192.168.255.255", "192.168.1.100"):
            with pytest.raises(Exception) as exc:
                _sanitize_url(f"http://{ip}/api")
            assert "host not allowed" in str(exc.value.detail).lower()

    def test_block_127_0_0_1(self):
        from app.routers.v1.providers import _sanitize_url

        with pytest.raises(Exception) as exc:
            _sanitize_url("http://127.0.0.1:8000/api")
        assert "host not allowed" in str(exc.value.detail).lower()

    def test_block_localhost_hostname(self):
        from app.routers.v1.providers import _sanitize_url

        with pytest.raises(Exception) as exc:
            _sanitize_url("http://localhost:8080/api")
        assert "host not allowed" in str(exc.value.detail).lower()

    def test_block_0_0_0_0(self):
        from app.routers.v1.providers import _sanitize_url

        with pytest.raises(Exception) as exc:
            _sanitize_url("http://0.0.0.0:8000/api")
        assert "host not allowed" in str(exc.value.detail).lower()

    def test_block_ipv6_localhost(self):
        from app.routers.v1.providers import _sanitize_url

        with pytest.raises(Exception) as exc:
            _sanitize_url("http://[::1]:8000/api")
        assert "host not allowed" in str(exc.value.detail).lower()

    def test_block_url_with_credentials_at_loopback(self):
        from app.routers.v1.providers import _sanitize_url

        with pytest.raises(Exception) as exc:
            _sanitize_url("http://user:pass@127.0.0.1:8000/api")
        assert "host not allowed" in str(exc.value.detail).lower()


class TestSSRFValidExternalIPs:
    """Non-private, non-loopback IPs must still be accepted."""

    def test_accept_public_dns_8_8_8_8(self):
        from app.routers.v1.providers import _sanitize_url

        result = _sanitize_url("http://8.8.8.8/dns-query")
        assert result is not None

    def test_accept_public_cloudflare_1_1_1_1(self):
        from app.routers.v1.providers import _sanitize_url

        result = _sanitize_url("https://1.1.1.1/dns-query")
        assert result is not None

    def test_accept_public_aws_54_dot(self):
        from app.routers.v1.providers import _sanitize_url

        result = _sanitize_url("https://54.239.28.85/health")
        assert result is not None


class TestSSRFKnownLimitations:
    """Documented gaps that _sanitize_url does not address."""

    def test_dns_rebinding_not_blocked_by_url_check(self):
        from app.routers.v1.providers import _sanitize_url

        result = _sanitize_url("http://rebind.example.com/api")
        assert result is not None

    def test_redirect_url_not_validated_for_downstream(self):
        from app.routers.v1.providers import _sanitize_url

        result = _sanitize_url("http://evil.com/redirect?url=http://169.254.169.254/latest/")
        assert "evil.com" in result


class TestSSRFConstantsExtended:
    """Verify new constants are present alongside original ones."""

    def test_new_blocked_hosts_present(self):
        from app.routers.v1.providers import SSRF_BLOCKED_HOSTS

        assert "127.0.0.1" in SSRF_BLOCKED_HOSTS
        assert "localhost" in SSRF_BLOCKED_HOSTS
        assert "0.0.0.0" in SSRF_BLOCKED_HOSTS
        assert "::1" in SSRF_BLOCKED_HOSTS

    def test_original_blocked_hosts_still_present(self):
        from app.routers.v1.providers import SSRF_BLOCKED_HOSTS

        assert "169.254.169.254" in SSRF_BLOCKED_HOSTS
        assert "metadata.google.internal" in SSRF_BLOCKED_HOSTS
        assert "100.100.100.200" in SSRF_BLOCKED_HOSTS
