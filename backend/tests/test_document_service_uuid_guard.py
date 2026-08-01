# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from unittest.mock import patch

import pytest

from app.services.document_service import DocumentService


@pytest.mark.asyncio
async def test_get_document_skips_supabase_for_non_uuid_id():
    with patch("app.services.document_service.get_supabase_client", side_effect=AssertionError("should not query")):
        result = await DocumentService.get_document("formatter-e2e")
        assert result is None


@pytest.mark.asyncio
async def test_get_document_result_skips_supabase_for_non_uuid_id():
    with patch("app.services.document_service.get_supabase_client", side_effect=AssertionError("should not query")):
        result = await DocumentService.get_document_result("formatter-e2e")
        assert result is None


@pytest.mark.asyncio
async def test_get_processing_statuses_skips_supabase_for_non_uuid_id():
    with patch("app.services.document_service.get_supabase_client", side_effect=AssertionError("should not query")):
        result = await DocumentService.get_processing_statuses("formatter-e2e")
        assert result == []
