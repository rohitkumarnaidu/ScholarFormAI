from __future__ import annotations


class TestProcessingStatus:
    def test_tablename(self):
        from app.models.processing_status import ProcessingStatus

        assert ProcessingStatus.__tablename__ == "processing_status"

    def test_columns_defined(self):
        from app.models.processing_status import ProcessingStatus

        cols = ProcessingStatus.__table__.columns
        assert "id" in cols
        assert "document_id" in cols
        assert "phase" in cols
        assert "status" in cols
        assert "progress_percentage" in cols
        assert "message" in cols

    def test_document_id_indexed(self):
        from app.models.processing_status import ProcessingStatus

        col = ProcessingStatus.__table__.columns["document_id"]
        assert col.index is True

    def test_phase_and_status_not_nullable(self):
        from app.models.processing_status import ProcessingStatus

        assert ProcessingStatus.__table__.columns["phase"].nullable is False
        assert ProcessingStatus.__table__.columns["status"].nullable is False
