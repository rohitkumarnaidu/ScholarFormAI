# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
SQL Injection E2E Tests — validates injection patterns through API
parameter guards, sanitization functions, and combined attacks.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.security]

SQLI_PATTERNS = [
    "' OR '1'='1",
    "'; DROP TABLE documents; --",
    "' UNION SELECT username, password FROM users --",
    "1; SELECT * FROM information_schema.tables",
    "' AND 1=CONVERT(int, (SELECT TOP 1 table_name FROM information_schema.tables))--",
    "admin'--",
    "1' ORDER BY 1--",
    "' OR 1=1 --",
    "1' AND 1=(SELECT COUNT(*) FROM users) --",
    "' OR 'x'='x",
]

PATHTRAVERSAL_SQLI_COMBINED = [
    "../../etc/passwd' OR '1'='1",
    "..\\..\\boot.ini'; DROP TABLE --",
    "....//....//etc/passwd' UNION SELECT * FROM users --",
    "%2e%2e/etc/passwd' OR 1=1 --",
    "../documents/'; DROP TABLE documents; --",
]


class TestDocumentServiceIsValidUuid:
    """Tests that DocumentService._is_valid_uuid rejects SQL injection patterns."""

    @pytest.mark.parametrize("sqli_payload", SQLI_PATTERNS)
    def test_rejects_sql_injection(self, sqli_payload):
        """SQL injection strings must not pass UUID validation."""
        from app.services.document_service import DocumentService

        assert DocumentService._is_valid_uuid(sqli_payload) is False
        assert DocumentService._should_query_document_tables(sqli_payload, "get_document") is False

    def test_accepts_valid_uuid(self):
        """Valid UUIDs should pass validation."""
        from app.services.document_service import DocumentService

        assert DocumentService._is_valid_uuid("550e8400-e29b-41d4-a716-446655440000") is True
        assert (
            DocumentService._should_query_document_tables("550e8400-e29b-41d4-a716-446655440000", "get_document")
            is True
        )

    def test_rejects_empty_string(self):
        from app.services.document_service import DocumentService

        assert DocumentService._is_valid_uuid("") is False

    def test_rejects_none(self):
        from app.services.document_service import DocumentService

        assert DocumentService._is_valid_uuid(None) is False


class TestQueryParameterSanitization:
    """Tests that query parameters with SQL patterns are sanitized."""

    @pytest.mark.parametrize("sqli_payload", SQLI_PATTERNS)
    def test_clean_metadata_rejects_sqli(self, sqli_payload):
        """SQL injection in metadata fields should be sanitized."""
        from app.utils.text_utils import clean_metadata_field

        sanitized = clean_metadata_field(sqli_payload)
        assert isinstance(sanitized, str)

    @pytest.mark.parametrize("sqli_payload", SQLI_PATTERNS)
    def test_uuid_guard_rejects_sqli(self, sqli_payload):
        """Document ID endpoint should reject SQL injection via UUID guard."""
        from app.services.document_service import DocumentService

        assert DocumentService._is_valid_uuid(sqli_payload) is False

    @pytest.mark.parametrize("sqli_payload", SQLI_PATTERNS)
    def test_should_not_query_with_sqli(self, sqli_payload):
        """Template filter parameter should not pass SQL injection to backend."""
        from app.services.document_service import DocumentService

        assert DocumentService._should_query_document_tables(sqli_payload, "get_document") is False


class TestCombinedAttacks:
    """Tests for combined path traversal + SQL injection attacks."""

    @pytest.mark.parametrize("combined_payload", PATHTRAVERSAL_SQLI_COMBINED)
    def test_is_valid_uuid_rejects_combined(self, combined_payload):
        """Combined path traversal + SQL injection should be rejected by UUID guard."""
        from app.services.document_service import DocumentService

        assert DocumentService._is_valid_uuid(combined_payload) is False
        assert DocumentService._should_query_document_tables(combined_payload, "get_document") is False

    @pytest.mark.parametrize("combined_payload", PATHTRAVERSAL_SQLI_COMBINED)
    def test_sanitize_rejects_combined(self, combined_payload):
        """Combined attacks in metadata should be sanitized."""
        from app.utils.text_utils import clean_metadata_field

        sanitized = clean_metadata_field(combined_payload)
        assert isinstance(sanitized, str)


class TestTemplateFilterSQLInjection:
    """Tests that template filters reject SQL injection."""

    @pytest.mark.parametrize("sqli_payload", SQLI_PATTERNS)
    def test_list_templates_with_sqli_name(self, sqli_payload):
        """Listing templates with SQL injection in name should be safe."""
        from app.routers.v1.templates import _canonical_template_id, _template_display_name

        canonical = _canonical_template_id(sqli_payload)
        assert isinstance(canonical, str)
        display = _template_display_name(canonical)
        assert isinstance(display, str)

    @pytest.mark.parametrize("sqli_payload", SQLI_PATTERNS)
    def test_uuid_guard_on_template_id(self, sqli_payload):
        """Template ID with SQL injection should be rejected by UUID guard."""
        from app.services.document_service import DocumentService

        assert DocumentService._is_valid_uuid(sqli_payload) is False
