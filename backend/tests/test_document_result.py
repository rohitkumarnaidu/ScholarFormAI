from __future__ import annotations
import pytest
from unittest.mock import patch, MagicMock


class TestDocumentResult:
    def test_tablename(self):
        from app.models.document_result import DocumentResult
        assert DocumentResult.__tablename__ == "document_results"

    def test_has_id_column(self):
        from app.models.document_result import DocumentResult
        assert hasattr(DocumentResult, "id")
        assert hasattr(DocumentResult, "document_id")
        assert hasattr(DocumentResult, "structured_data")
        assert hasattr(DocumentResult, "validation_results")

    def test_columns_defined(self):
        from app.models.document_result import DocumentResult
        from sqlalchemy import Column
        cols = DocumentResult.__table__.columns
        assert "id" in cols
        assert "document_id" in cols
        assert "structured_data" in cols
        assert "validation_results" in cols

    def test_document_id_indexed(self):
        from app.models.document_result import DocumentResult
        col = DocumentResult.__table__.columns["document_id"]
        assert col.index is True
