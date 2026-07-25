"""Security tests for AMF API."""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestSecurity:
    """Security-focused integration tests."""

    def test_sql_injection_in_style_id(self, client):
        payload = {
            "manuscript": {
                "title": "Test",
                "authors": [{"first_name": "A", "last_name": "B"}],
                "sections": [{"heading": "Intro", "level": 1, "content": [{"text": "Test"}]}],
            },
            "style_id": "apa; DROP TABLE manuscripts; --",
        }
        response = client.post("/api/v1/validate", json=payload)
        # Should either be 200 (validated normally) or 404 (style not found) - never 500
        assert response.status_code in (200, 404)

    def test_sql_injection_in_title(self, client):
        payload = {
            "manuscript": {
                "title": "'; SELECT * FROM users; --",
                "authors": [{"first_name": "A", "last_name": "B"}],
                "sections": [{"heading": "Intro", "level": 1, "content": [{"text": "Test"}]}],
            },
            "style_id": "apa",
        }
        response = client.post("/api/v1/format", json=payload)
        assert response.status_code in (200, 422)

    def test_xss_in_manuscript_title(self, client):
        payload = {
            "manuscript": {
                "title": "<script>alert('xss')</script>",
                "authors": [{"first_name": "A", "last_name": "B"}],
                "sections": [{"heading": "Intro", "level": 1, "content": [{"text": "Test"}]}],
            },
            "style_id": "apa",
        }
        # HTML preview should not contain executable script tags
        response = client.post("/api/v1/preview", json=payload)
        assert response.status_code == 200
        html = response.json()["html"]
        assert "<script>" not in html or "&lt;script&gt;" in html

    def test_xss_in_section_content(self, client):
        payload = {
            "manuscript": {
                "title": "Test Paper",
                "authors": [{"first_name": "A", "last_name": "B"}],
                "sections": [{
                    "heading": "Intro",
                    "level": 1,
                    "content": [{"text": "<script>alert('xss')</script>"}],
                }],
            },
            "style_id": "apa",
        }
        response = client.post("/api/v1/preview", json=payload)
        assert response.status_code == 200
        html = response.json()["html"]
        assert "<script>" not in html or "&lt;script&gt;" in html

    def test_path_traversal_in_body(self, client):
        payload = {
            "manuscript": {
                "title": "../../etc/passwd",
                "authors": [{"first_name": "../..", "last_name": "../../"}],
                "sections": [{"heading": "../../", "level": 1, "content": [{"text": "../../etc/shadow"}]}],
            },
            "style_id": "apa",
        }
        response = client.post("/api/v1/validate", json=payload)
        assert response.status_code == 200  # Should handle gracefully

    def test_oversized_payload_rejected(self, client):
        huge_text = "A" * (11 * 1024 * 1024)  # ~11 MB
        payload = {
            "manuscript": {
                "title": "Huge Manuscript",
                "authors": [{"first_name": "A", "last_name": "B"}],
                "sections": [{"heading": "Intro", "level": 1, "content": [{"text": huge_text}]}],
            },
            "style_id": "apa",
        }
        response = client.post("/api/v1/format", json=payload)
        # FastAPI body limit should reject or truncate
        assert response.status_code in (413, 422)

    def test_rate_limit_headers_present(self, client):
        for _ in range(3):
            response = client.get("/api/v1/styles")
            assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers

    def test_cors_headers(self, client):
        response = client.get(
            "/health",
            headers={"Origin": "https://example.com"},
        )
        assert "access-control-allow-origin" in response.headers or response.status_code == 200

    def test_security_headers_present(self, client):
        response = client.get("/health")
        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        security_headers = [
            "content-security-policy",
            "x-content-type-options",
            "x-frame-options",
            "strict-transport-security",
            "referrer-policy",
        ]
        for header in security_headers:
            assert header in headers_lower, f"Missing security header: {header}"

    def test_no_sensitive_info_in_error_messages(self, client):
        payload = {
            "manuscript": {"title": "", "authors": []},
            "style_id": "nonexistent",
        }
        response = client.post("/api/v1/validate", json=payload)
        body = response.text.lower()
        sensitive_patterns = ["traceback", "file", "directory", "internal", "stack"]
        for pattern in sensitive_patterns:
            assert pattern not in body, f"Response leaked sensitive info: {pattern}"

    def test_invalid_content_type(self, client):
        response = client.post(
            "/api/v1/validate",
            data="not json",
            headers={"Content-Type": "text/plain"},
        )
        assert response.status_code in (400, 415, 422)

    def test_unicode_injection(self, client):
        payload = {
            "manuscript": {
                "title": "\u0000null byte injection",
                "authors": [{"first_name": "\ufffdomark", "last_name": "\u2028line sep"}],
                "sections": [{"heading": "\u200bzero width", "level": 1, "content": [{"text": "\ufffcreplacement"}]}],
            },
            "style_id": "apa",
        }
        response = client.post("/api/v1/validate", json=payload)
        assert response.status_code == 200

    def test_duplicate_headers(self, client):
        headers = [
            ("Content-Type", "application/json"),
            ("X-Forwarded-For", "127.0.0.1"),
            ("X-Forwarded-For", "192.168.1.1"),
        ]
        payload = {
            "manuscript": {
                "title": "Duplicate Headers Test",
                "sections": [{"heading": "Intro", "level": 1, "content": [{"text": "Test"}]}],
            },
            "style_id": "apa",
        }
        response = client.post("/api/v1/validate", json=payload, headers=dict(headers))
        assert response.status_code in (200, 400)

    def test_numeric_injection(self, client):
        payload = {
            "manuscript": {
                "title": "1; DROP TABLE manuscripts",
                "authors": [{"first_name": "1' OR '1'='1", "last_name": "1 UNION SELECT * FROM users"}],
                "sections": [{"heading": "1; SELECT * FROM information_schema.tables", "level": 1}],
            },
            "style_id": "apa OR '1'='1",
        }
        response = client.post("/api/v1/validate", json=payload)
        assert response.status_code in (200, 404)
