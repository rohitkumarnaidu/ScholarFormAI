"""
Empirical SSRF Adversarial Test Harness for ScholarFormAI backend
Tests `_sanitize_url` in app.routers.v1.providers against SSRF payloads.
"""

import os
import sys

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import HTTPException

from app.routers.v1.providers import _sanitize_url

# Categorized Test Suite
MALICIOUS_PAYLOADS = [
    # 1. Loopback
    ("http://127.0.0.1/", "Loopback IPv4 (127.0.0.1)", "Loopback"),
    ("http://localhost/", "Loopback localhost domain", "Loopback"),
    ("http://0.0.0.0/", "Loopback 0.0.0.0", "Loopback"),
    ("http://[::1]/", "Loopback IPv6 ([::1])", "Loopback"),
    ("http://127.0.0.1:8080/v1", "Loopback with port 8080", "Loopback"),
    ("http://sub.localhost/", "Subdomain of localhost", "Loopback"),
    # 2. Numeric Encodings
    ("http://0x7f000001/", "Hex encoded IP 0x7f000001", "Numeric Encodings"),
    ("http://0177.0.0.1/", "Octal encoded IP 0177.0.0.1", "Numeric Encodings"),
    ("http://2130706433/", "DWORD integer IP 2130706433", "Numeric Encodings"),
    ("http://0x7f.0.0.1/", "Mixed hex/dec IP", "Numeric Encodings"),
    # 3. IPv4-mapped IPv6
    ("http://[::ffff:127.0.0.1]/", "IPv4-mapped IPv6 loopback [::ffff:127.0.0.1]", "IPv4-mapped IPv6"),
    ("http://[::ffff:10.0.0.1]/", "IPv4-mapped IPv6 private [::ffff:10.0.0.1]", "IPv4-mapped IPv6"),
    # 4. Private Networks
    ("http://10.0.0.1/", "Private network 10.0.0.1 (Class A)", "Private Networks"),
    ("http://172.16.0.1/", "Private network 172.16.0.1 (Class B)", "Private Networks"),
    ("http://192.168.1.1/", "Private network 192.168.1.1 (Class C)", "Private Networks"),
    ("http://100.64.0.1/", "CGNAT network 100.64.0.1", "Private Networks"),
    # 5. Cloud Metadata
    ("http://169.254.169.254/", "AWS/GCP/Azure link-local metadata IP", "Cloud Metadata"),
    ("http://metadata.google.internal/", "GCP metadata domain", "Cloud Metadata"),
    # 6. Dangerous Schemes
    ("file:///etc/passwd", "file:// scheme", "Dangerous Schemes"),
    ("gopher://127.0.0.1:25/", "gopher:// scheme", "Dangerous Schemes"),
    ("ftp://example.com/", "ftp:// scheme", "Dangerous Schemes"),
    ("dict://127.0.0.1/", "dict:// scheme", "Dangerous Schemes"),
    ("data:text/html,secret", "data: scheme", "Dangerous Schemes"),
    # 7. Userinfo Credentials
    ("http://admin:secret@127.0.0.1/", "Userinfo credentials pointing to 127.0.0.1", "Userinfo Credentials"),
]

VALID_PUBLIC_URLS = [
    ("https://example.com/", "Standard HTTPS public domain", "Public Safe URLs"),
    ("https://api.github.com/", "Standard HTTPS API endpoint", "Public Safe URLs"),
    ("http://8.8.8.8/", "Public DNS IPv4 address", "Public Safe URLs"),
]


def run_ssrf_test_harness():
    print("=" * 80)
    print("  SCHOLARFORMAI SSRF ADVERSARIAL TEST HARNESS - _sanitize_url")
    print("=" * 80)
    print()

    total_tests = 0
    passed_tests = 0
    failed_tests = 0

    results = []

    # 1. Malicious Payloads Test
    print("--> Testing Malicious Payloads (Expecting HTTP 422 Rejection)...")
    print("-" * 80)
    for url, desc, category in MALICIOUS_PAYLOADS:
        total_tests += 1
        try:
            res = _sanitize_url(url)
            # If no exception raised, sanitization failed!
            failed_tests += 1
            results.append((category, url, desc, "ALLOWED (VULNERABLE)", f"Sanitized to: {res}", "FAIL"))
            print(f"[FAIL] {category:20s} | {url:35s} | ALLOWED! Sanitized: {res}")
        except HTTPException as exc:
            if exc.status_code == 422:
                passed_tests += 1
                results.append((category, url, desc, f"HTTP {exc.status_code}", exc.detail, "PASS"))
                print(f"[PASS] {category:20s} | {url:35s} | Rejected: HTTP 422 ({exc.detail})")
            else:
                failed_tests += 1
                results.append((category, url, desc, f"HTTP {exc.status_code}", exc.detail, "FAIL"))
                print(f"[FAIL] {category:20s} | {url:35s} | Unexpected Status: HTTP {exc.status_code}")
        except Exception as exc:
            failed_tests += 1
            results.append((category, url, desc, "EXCEPTION", str(exc), "FAIL"))
            print(f"[FAIL] {category:20s} | {url:35s} | Exception: {exc}")

    print()
    # 2. Valid Public URLs Test
    print("--> Testing Valid Public URLs (Expecting Successful Sanitization)...")
    print("-" * 80)
    for url, desc, category in VALID_PUBLIC_URLS:
        total_tests += 1
        try:
            res = _sanitize_url(url)
            passed_tests += 1
            results.append((category, url, desc, "ALLOWED", f"Sanitized to: {res}", "PASS"))
            print(f"[PASS] {category:20s} | {url:35s} | Allowed -> '{res}'")
        except HTTPException as exc:
            failed_tests += 1
            results.append((category, url, desc, f"HTTP {exc.status_code}", exc.detail, "FAIL"))
            print(f"[FAIL] {category:20s} | {url:35s} | Unexpected HTTP {exc.status_code}: {exc.detail}")
        except Exception as exc:
            failed_tests += 1
            results.append((category, url, desc, "EXCEPTION", str(exc), "FAIL"))
            print(f"[FAIL] {category:20s} | {url:35s} | Exception: {exc}")

    print()
    print("=" * 80)
    print(f"  SUMMARY: Total: {total_tests} | Passed: {passed_tests} | Failed: {failed_tests}")
    print(f"  SUCCESS RATE: {(passed_tests / total_tests) * 100:.2f}%")
    print("=" * 80)

    return total_tests, passed_tests, failed_tests, results


if __name__ == "__main__":
    t, p, f, res = run_ssrf_test_harness()
    if f > 0:
        sys.exit(1)
    sys.exit(0)
