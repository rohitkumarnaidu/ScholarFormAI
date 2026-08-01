from __future__ import annotations


class TestDocumentVersion:
    def test_tablename(self):
        from app.models.document_version import DocumentVersion
        assert DocumentVersion.__tablename__ == "document_versions"

    def test_columns_defined(self):
        from app.models.document_version import DocumentVersion
        cols = DocumentVersion.__table__.columns
        assert "id" in cols
        assert "document_id" in cols
        assert "version_number" in cols
        assert "edited_structured_data" in cols
        assert "output_path" in cols

    def test_document_id_indexed(self):
        from app.models.document_version import DocumentVersion
        col = DocumentVersion.__table__.columns["document_id"]
        assert col.index is True

    def test_version_number_not_nullable(self):
        from app.models.document_version import DocumentVersion
        col = DocumentVersion.__table__.columns["version_number"]
        assert col.nullable is False
