"""
Adversarial SSRF Test Harness for _sanitize_url in app.routers.v1.providers
"""
import pytest
from fastapi import HTTPException
from app.routers.v1.providers import _sanitize_url

MALICIOUS_PAYLOADS = [
    # Loopback
    ("http://127.0.0.1/", "Loopback IPv4"),
    ("http://localhost/", "Loopback localhost domain"),
    ("http://0.0.0.0/", "Loopback 0.0.0.0"),
    ("http://[::1]/", "Loopback IPv6"),
    ("http://127.0.0.1:8080/v1", "Loopback IPv4 with port"),
    ("http://sub.localhost/", "Subdomain of localhost"),

    # Numeric encodings
    ("http://0x7f000001/", "Hex encoded IP 0x7f000001 (127.0.0.1)"),
    ("http://0177.0.0.1/", "Octal encoded IP 0177.0.0.1 (127.0.0.1)"),
    ("http://2130706433/", "DWORD integer IP 2130706433 (127.0.0.1)"),
    ("http://0x7f.0.0.1/", "Mixed hex/dec IP"),

    # IPv4-mapped IPv6
    ("http://[::ffff:127.0.0.1]/", "IPv4-mapped IPv6 loopback"),
    ("http://[::ffff:10.0.0.1]/", "IPv4-mapped IPv6 private 10.0.0.1"),
    ("http://[::ffff:7f00:1]/", "IPv4-mapped IPv6 hex loopback"),

    # Private networks
    ("http://10.0.0.1/", "Private network 10.0.0.0/8"),
    ("http://172.16.0.1/", "Private network 172.16.0.0/12"),
    ("http://192.168.1.1/", "Private network 192.168.0.0/16"),
    ("http://100.64.0.1/", "CGNAT network 100.64.0.0/10"),
    ("http://10.255.255.255/", "Private network 10.x boundary"),
    ("http://172.31.255.255/", "Private network 172.x boundary"),

    # Cloud metadata
    ("http://169.254.169.254/", "AWS/GCP/Azure link-local metadata IP"),
    ("http://metadata.google.internal/", "GCP metadata domain"),
    ("http://sub.metadata.google.internal/", "GCP metadata subdomain"),
    ("http://169.254.169.254/latest/meta-data/", "AWS metadata endpoint"),

    # Dangerous schemes
    ("file:///etc/passwd", "file:// scheme"),
    ("gopher://127.0.0.1:25/", "gopher:// scheme"),
    ("ftp://example.com/", "ftp:// scheme"),
    ("dict://127.0.0.1/", "dict:// scheme"),
    ("data:text/html,secret", "data: scheme"),
    ("ldap://127.0.0.1/", "ldap:// scheme"),
    ("javascript:alert(1)", "javascript: scheme"),

    # Userinfo credentials
    ("http://admin:secret@127.0.0.1/", "Userinfo credentials pointing to loopback"),
    ("http://user:pass@10.0.0.1:8080/path", "Userinfo credentials pointing to private IP"),

    # Invalid / Empty
    ("", "Empty string"),
    ("   ", "Whitespace string"),
]

VALID_PUBLIC_URLS = [
    ("https://example.com/", "Standard HTTPS domain"),
    ("https://api.github.com/", "Standard HTTPS API endpoint"),
    ("http://8.8.8.8/", "Public DNS IPv4 address"),
    ("https://openai.com/v1", "HTTPS API path"),
    ("http://1.1.1.1/", "Public Cloudflare DNS IPv4 address"),
    ("https://api.anthropic.com/v1/messages", "Public HTTPS endpoint"),
]


@pytest.mark.parametrize("url,description", MALICIOUS_PAYLOADS)
def test_sanitize_url_rejects_malicious_payloads(url, description):
    with pytest.raises(HTTPException) as exc_info:
        _sanitize_url(url)
    assert exc_info.value.status_code == 422, f"Failed for {description} ({url}): status was {exc_info.value.status_code}"


@pytest.mark.parametrize("url,description", VALID_PUBLIC_URLS)
def test_sanitize_url_allows_valid_public_urls(url, description):
    sanitized = _sanitize_url(url)
    assert sanitized is not None
    assert not sanitized.endswith("/") or sanitized in ("http:", "https:")
