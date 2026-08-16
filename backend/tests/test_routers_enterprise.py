from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

# ── documents_impl: error paths ─────────────────────────────────────────


class TestDocumentsImplEditDocument:
    @pytest.mark.asyncio
    async def test_missing_edited_data(self):
        from app.routers.v1.documents_impl import edit_document

        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"
        doc = {"id": "d1", "user_id": "u1", "filename": "test.docx", "template": "ieee"}
        with (
            patch(
                "app.services.document_crud_service.DocumentCrudService.get_document",
                new_callable=AsyncMock,
                return_value=doc,
            ),
            patch("app.routers.v1.documents_impl._require_db"),
        ):
            with pytest.raises(HTTPException) as exc:
                await edit_document(
                    mock_request, "d1", {"not_edited_data": {}}, MagicMock(), current_user=MagicMock(id="u1")
                )
            assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_doc_not_found(self):
        from app.routers.v1.documents_impl import edit_document

        mock_request = MagicMock()
        with (
            patch(
                "app.services.document_crud_service.DocumentCrudService.get_document",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch("app.routers.v1.documents_impl._require_db"),
        ):
            with pytest.raises(HTTPException) as exc:
                await edit_document(
                    mock_request,
                    "nonexistent",
                    {"edited_structured_data": {"k": "v"}},
                    MagicMock(),
                    current_user=MagicMock(id="u1"),
                )
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_not_authorized(self):
        from app.routers.v1.documents_impl import edit_document

        mock_request = MagicMock()
        doc = {"id": "d1", "user_id": "other-user", "filename": "test.docx", "template": "ieee"}
        with (
            patch(
                "app.services.document_crud_service.DocumentCrudService.get_document",
                new_callable=AsyncMock,
                return_value=doc,
            ),
            patch("app.routers.v1.documents_impl._require_db"),
        ):
            with pytest.raises(HTTPException) as exc:
                await edit_document(
                    mock_request,
                    "d1",
                    {"edited_structured_data": {"k": "v"}},
                    MagicMock(),
                    current_user=MagicMock(id="u1"),
                )
            assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_unexpected_error(self):
        from app.routers.v1.documents_impl import edit_document

        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"
        doc = {"id": "d1", "user_id": "u1", "filename": "test.docx", "template": "ieee"}
        with (
            patch(
                "app.services.document_crud_service.DocumentCrudService.get_document",
                new_callable=AsyncMock,
                return_value=doc,
            ),
            patch("app.routers.v1.documents_impl._require_db"),
            patch("app.routers.v1.documents_impl.PipelineOrchestrator", side_effect=ValueError("boom")),
        ):
            with pytest.raises(HTTPException) as exc:
                await edit_document(
                    mock_request,
                    "d1",
                    {"edited_structured_data": {"k": "v"}},
                    MagicMock(),
                    current_user=MagicMock(id="u1"),
                )
            assert exc.value.status_code == 500


class TestDocumentsImplPreview:
    @pytest.mark.asyncio
    async def test_no_result(self):
        from app.routers.v1.documents_impl import get_preview

        mock_user = MagicMock(id="u1")
        doc = {
            "id": "d1",
            "user_id": "u1",
            "filename": "p.pdf",
            "template": "apa",
            "status": "COMPLETED",
            "created_at": "now",
        }
        with (
            patch(
                "app.services.document_crud_service.DocumentCrudService.get_document",
                new_callable=AsyncMock,
                return_value=doc,
            ),
            patch(
                "app.services.document_crud_service.DocumentCrudService.get_document_result",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            with pytest.raises(HTTPException) as exc:
                await get_preview("d1", current_user=mock_user)
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_doc_not_found(self):
        from app.routers.v1.documents_impl import get_preview

        with patch(
            "app.services.document_crud_service.DocumentCrudService.get_document",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc:
                await get_preview("nonexistent", current_user=None)
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_not_authorized(self):
        from app.routers.v1.documents_impl import get_preview

        doc = {
            "id": "d1",
            "user_id": "other-user",
            "filename": "p.pdf",
            "template": "apa",
            "status": "COMPLETED",
            "created_at": "now",
        }
        with patch(
            "app.services.document_crud_service.DocumentCrudService.get_document",
            new_callable=AsyncMock,
            return_value=doc,
        ):
            with pytest.raises(HTTPException) as exc:
                await get_preview("d1", current_user=MagicMock(id="u1"))
            assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_unexpected_error(self):
        from app.routers.v1.documents_impl import get_preview

        with patch(
            "app.services.document_crud_service.DocumentCrudService.get_document",
            new_callable=AsyncMock,
            side_effect=ValueError("boom"),
        ):
            with pytest.raises(HTTPException) as exc:
                await get_preview("d1", current_user=None)
            assert exc.value.status_code == 500


class TestDocumentsImplComparison:
    @pytest.mark.asyncio
    async def test_doc_not_found(self):
        from app.routers.v1.documents_impl import get_comparison_data

        with patch(
            "app.services.document_crud_service.DocumentCrudService.get_document",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc:
                await get_comparison_data("nonexistent", current_user=None)
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_not_authorized(self):
        from app.routers.v1.documents_impl import get_comparison_data

        doc = {"id": "d1", "user_id": "other-user", "status": "COMPLETED"}
        with patch(
            "app.services.document_crud_service.DocumentCrudService.get_document",
            new_callable=AsyncMock,
            return_value=doc,
        ):
            with pytest.raises(HTTPException) as exc:
                await get_comparison_data("d1", current_user=MagicMock(id="u1"))
            assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_not_ready(self):
        from app.routers.v1.documents_impl import get_comparison_data

        doc = {"id": "d1", "user_id": "u1", "status": "PROCESSING"}
        with patch(
            "app.services.document_crud_service.DocumentCrudService.get_document",
            new_callable=AsyncMock,
            return_value=doc,
        ):
            with pytest.raises(HTTPException) as exc:
                await get_comparison_data("d1", current_user=MagicMock(id="u1"))
            assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_result_not_found(self):
        from app.routers.v1.documents_impl import get_comparison_data

        doc = {"id": "d1", "user_id": "u1", "status": "COMPLETED", "raw_text": "original"}
        with (
            patch(
                "app.services.document_crud_service.DocumentCrudService.get_document",
                new_callable=AsyncMock,
                return_value=doc,
            ),
            patch(
                "app.services.document_crud_service.DocumentCrudService.get_document_result",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            with pytest.raises(HTTPException) as exc:
                await get_comparison_data("d1", current_user=MagicMock(id="u1"))
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_unexpected_error(self):
        from app.routers.v1.documents_impl import get_comparison_data

        with patch(
            "app.services.document_crud_service.DocumentCrudService.get_document", side_effect=ValueError("boom")
        ):
            with pytest.raises(HTTPException) as exc:
                await get_comparison_data("d1", current_user=None)
            assert exc.value.status_code == 500


class TestDocumentsImplDownload:
    @pytest.mark.asyncio
    async def test_doc_not_found(self):
        from app.routers.v1.documents_impl import download_document

        mock_request = MagicMock()
        with patch(
            "app.services.document_crud_service.DocumentCrudService.get_document",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc:
                await download_document(mock_request, "nonexistent", format="docx", current_user=None)
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_unsupported_format(self):
        from app.routers.v1.documents_impl import download_document

        mock_request = MagicMock()
        doc = {"id": "d1", "status": "COMPLETED"}
        with patch(
            "app.services.document_crud_service.DocumentCrudService.get_document",
            new_callable=AsyncMock,
            return_value=doc,
        ):
            with pytest.raises(HTTPException) as exc:
                await download_document(mock_request, "d1", format="svg", current_user=None)
            assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_not_authorized(self):
        from app.routers.v1.documents_impl import download_document

        mock_request = MagicMock()
        doc = {"id": "d1", "user_id": "other-user", "status": "COMPLETED"}
        with (
            patch(
                "app.services.document_crud_service.DocumentCrudService.get_document",
                new_callable=AsyncMock,
                return_value=doc,
            ),
            patch("app.routers.v1.documents_impl.settings.SIGNED_URL_SECRET", "secret"),
        ):
            with pytest.raises(HTTPException) as exc:
                await download_document(
                    mock_request, "d1", format="docx", token=None, expires=None, current_user=MagicMock(id="u1")
                )
            assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_signed_token_missing_expires(self):
        from app.routers.v1.documents_impl import download_document

        mock_request = MagicMock()
        doc = {"id": "d1", "user_id": None, "status": "COMPLETED"}
        with (
            patch(
                "app.services.document_crud_service.DocumentCrudService.get_document",
                new_callable=AsyncMock,
                return_value=doc,
            ),
            patch("app.routers.v1.documents_impl.settings.SIGNED_URL_SECRET", "secret"),
        ):
            with pytest.raises(HTTPException) as exc:
                await download_document(mock_request, "d1", format="docx", token="abc", expires=None, current_user=None)
            assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_not_ready(self):
        from app.routers.v1.documents_impl import download_document

        mock_request = MagicMock()
        doc = {"id": "d1", "user_id": None, "status": "PROCESSING"}
        with (
            patch(
                "app.services.document_crud_service.DocumentCrudService.get_document",
                new_callable=AsyncMock,
                return_value=doc,
            ),
            patch("app.routers.v1.documents_impl.settings.SIGNED_URL_SECRET", "secret"),
        ):
            with pytest.raises(HTTPException) as exc:
                await download_document(mock_request, "d1", format="docx", token=None, expires=None, current_user=None)
            assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_output_path_missing(self):
        from app.routers.v1.documents_impl import download_document

        mock_request = MagicMock()
        doc = {"id": "d1", "user_id": None, "status": "COMPLETED", "output_path": None}
        with (
            patch(
                "app.services.document_crud_service.DocumentCrudService.get_document",
                new_callable=AsyncMock,
                return_value=doc,
            ),
            patch("app.services.document_export_service.os.path.exists", return_value=True),
            patch("app.routers.v1.documents_impl.settings.SIGNED_URL_SECRET", "secret"),
        ):
            with pytest.raises(HTTPException) as exc:
                await download_document(mock_request, "d1", format="docx", token=None, expires=None, current_user=None)
            assert exc.value.status_code == 500

    @pytest.mark.asyncio
    async def test_output_file_missing_on_disk(self):
        from app.routers.v1.documents_impl import download_document

        mock_request = MagicMock()
        doc = {"id": "d1", "user_id": None, "status": "COMPLETED", "output_path": "/tmp/missing.docx"}
        with (
            patch(
                "app.services.document_crud_service.DocumentCrudService.get_document",
                new_callable=AsyncMock,
                return_value=doc,
            ),
            patch("app.services.document_export_service.os.path.exists", return_value=False),
            patch("app.routers.v1.documents_impl.settings.SIGNED_URL_SECRET", "secret"),
        ):
            with pytest.raises(HTTPException) as exc:
                await download_document(mock_request, "d1", format="docx", token=None, expires=None, current_user=None)
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_hash_mismatch(self):
        from app.routers.v1.documents_impl import download_document

        mock_request = MagicMock()
        mock_request.url = MagicMock()
        mock_request.url.path = "/api/v1/documents/d1/download"
        doc = {
            "id": "d1",
            "user_id": None,
            "status": "COMPLETED",
            "output_path": "/tmp/doc.docx",
            "output_hash": "abc123",
            "filename": "paper.docx",
        }
        with (
            patch(
                "app.services.document_crud_service.DocumentCrudService.get_document",
                new_callable=AsyncMock,
                return_value=doc,
            ),
            patch("app.services.document_export_service.os.path.exists", return_value=True),
            patch("app.routers.v1.documents_impl.settings.SIGNED_URL_SECRET", "secret"),
            patch("app.routers.v1.documents_impl._compute_sha256", return_value="def456"),
            patch(
                "app.services.document_export_service.DocumentExportService.verify_signed_download", return_value=True
            ),
        ):
            with pytest.raises(HTTPException) as exc:
                await download_document(
                    mock_request, "d1", format="docx", token="valid", expires=9999999999, current_user=None
                )
            assert exc.value.status_code == 500

    @pytest.mark.asyncio
    async def test_pdf_export_runtime_error(self):
        from app.routers.v1.documents_impl import download_document

        mock_request = MagicMock()
        mock_request.url = MagicMock()
        mock_request.url.path = "/api/v1/documents/d1/download"
        doc = {
            "id": "d1",
            "user_id": None,
            "status": "COMPLETED",
            "output_path": "/tmp/doc.docx",
            "output_hash": None,
            "filename": "paper.docx",
        }

        def _exists_side_effect(path):
            return ".docx" in str(path)

        with (
            patch(
                "app.services.document_crud_service.DocumentCrudService.get_document",
                new_callable=AsyncMock,
                return_value=doc,
            ),
            patch("app.services.document_export_service.os.path.exists", side_effect=_exists_side_effect),
            patch("app.routers.v1.documents_impl.settings.SIGNED_URL_SECRET", "secret"),
            patch(
                "app.services.document_export_service.DocumentExportService.verify_signed_download", return_value=True
            ),
            patch("app.services.document_export_service.PDFExporter") as mock_exporter,
        ):
            mock_exporter.return_value.convert_to_pdf.side_effect = RuntimeError("no wkhtmltopdf")
            with pytest.raises(HTTPException) as exc:
                await download_document(
                    mock_request, "d1", format="pdf", token="valid", expires=9999999999, current_user=None
                )
            assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_tex_export_runtime_error(self):
        from app.routers.v1.documents_impl import download_document

        mock_request = MagicMock()
        mock_request.url = MagicMock()
        mock_request.url.path = "/api/v1/documents/d1/download"
        doc = {
            "id": "d1",
            "user_id": None,
            "status": "COMPLETED",
            "output_path": "/tmp/doc.docx",
            "output_hash": None,
            "filename": "paper.docx",
        }

        def _tex_exists_side_effect(path):
            return ".docx" in str(path)

        with (
            patch(
                "app.services.document_crud_service.DocumentCrudService.get_document",
                new_callable=AsyncMock,
                return_value=doc,
            ),
            patch("app.services.document_export_service.os.path.exists", side_effect=_tex_exists_side_effect),
            patch("app.routers.v1.documents_impl.settings.SIGNED_URL_SECRET", "secret"),
            patch(
                "app.services.document_export_service.DocumentExportService.verify_signed_download", return_value=True
            ),
            patch("app.services.document_export_service.LaTeXExporter") as mock_exporter,
        ):
            mock_exporter.return_value.convert_to_latex.side_effect = RuntimeError("no pdflatex")
            with pytest.raises(HTTPException) as exc:
                await download_document(
                    mock_request, "d1", format="tex", token="valid", expires=9999999999, current_user=None
                )
            assert exc.value.status_code == 400


class TestDocumentsImplDelete:
    @pytest.mark.asyncio
    async def test_not_authorized(self):
        from app.routers.v1.documents_impl import delete_document

        mock_request = MagicMock()
        doc = {"id": "d1", "user_id": "other-user"}
        with (
            patch(
                "app.services.document_crud_service.DocumentCrudService.get_document",
                new_callable=AsyncMock,
                return_value=doc,
            ),
            patch("app.routers.v1.documents_impl._require_db"),
        ):
            with pytest.raises(HTTPException) as exc:
                await delete_document(mock_request, "d1", current_user=MagicMock(id="u1"))
            assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_not_found(self):
        from app.routers.v1.documents_impl import delete_document

        mock_request = MagicMock()
        with (
            patch(
                "app.services.document_crud_service.DocumentCrudService.get_document",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch("app.routers.v1.documents_impl._require_db"),
        ):
            with pytest.raises(HTTPException) as exc:
                await delete_document(mock_request, "nonexistent", current_user=MagicMock(id="u1"))
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_output_remove_os_error(self):
        from app.routers.v1.documents_impl import delete_document

        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"
        doc = {
            "id": "d1",
            "user_id": "u1",
            "output_path": "/tmp/doc.docx",
            "original_file_path": "/tmp/orig.docx",
            "filename": "test.docx",
        }
        with (
            patch(
                "app.services.document_crud_service.DocumentCrudService.get_document",
                new_callable=AsyncMock,
                return_value=doc,
            ),
            patch("app.services.document_crud_service.DocumentCrudService.delete_document", new_callable=AsyncMock),
            patch("app.routers.v1.documents_impl.audit_log_service.log", new_callable=AsyncMock),
            patch("app.services.document_export_service.os.path.exists", return_value=True),
            patch("app.services.document_crud_service.os.remove", side_effect=OSError("permission")),
            patch("app.routers.v1.documents_impl._require_db"),
        ):
            result = await delete_document(mock_request, "d1", current_user=MagicMock(id="u1"))
            assert result["status"] == "deleted"

    @pytest.mark.asyncio
    async def test_unexpected_error(self):
        from app.routers.v1.documents_impl import delete_document

        mock_request = MagicMock()
        with (
            patch(
                "app.services.document_crud_service.DocumentCrudService.get_document", side_effect=ValueError("boom")
            ),
            patch("app.routers.v1.documents_impl._require_db"),
        ):
            with pytest.raises(HTTPException) as exc:
                await delete_document(mock_request, "d1", current_user=MagicMock(id="u1"))
            assert exc.value.status_code == 500


class TestDocumentsImplUpload:
    @pytest.mark.asyncio
    async def test_path_traversal_detected(self):
        from app.routers.v1.documents_impl import upload_document

        content = b"\x50\x4b\x03\x04" + b"\x00" * 100
        file = MagicMock()
        file.filename = "../../etc/passwd"
        file.read = AsyncMock(return_value=content)
        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"
        with (
            patch("app.routers.v1.documents_impl._require_db"),
            patch("app.routers.v1.documents_impl._enforce_daily_upload_quota"),
            patch("app.routers.v1.documents_impl.settings.MAX_FILE_SIZE", 10485760),
            patch("app.routers.v1.documents_impl.settings.DEFAULT_TEMPLATE", "ieee"),
        ):
            with pytest.raises(HTTPException) as exc:
                await upload_document(mock_request, MagicMock(), file=file, template="ieee", current_user=None)
            assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_empty_file(self):
        from app.routers.v1.documents_impl import upload_document

        file = MagicMock()
        file.filename = "empty.docx"
        file.read = AsyncMock(return_value=b"")
        mock_request = MagicMock()
        with (
            patch("app.routers.v1.documents_impl._require_db"),
            patch("app.routers.v1.documents_impl._enforce_daily_upload_quota"),
            patch("app.routers.v1.documents_impl.settings.MAX_FILE_SIZE", 10485760),
            patch("app.routers.v1.documents_impl.settings.DEFAULT_TEMPLATE", "ieee"),
        ):
            with pytest.raises(HTTPException) as exc:
                await upload_document(mock_request, MagicMock(), file=file, template="ieee", current_user=None)
            assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_unexpected_error(self):
        from app.routers.v1.documents_impl import upload_document

        file = MagicMock()
        file.filename = "test.docx"
        file.read = AsyncMock(side_effect=ValueError("read error"))
        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"
        with (
            patch("app.routers.v1.documents_impl._require_db"),
            patch("app.routers.v1.documents_impl._enforce_daily_upload_quota"),
            patch("app.routers.v1.documents_impl.settings.MAX_FILE_SIZE", 10485760),
            patch("app.routers.v1.documents_impl.settings.DEFAULT_TEMPLATE", "ieee"),
        ):
            with pytest.raises(HTTPException) as exc:
                await upload_document(mock_request, MagicMock(), file=file, template="ieee", current_user=None)
            assert exc.value.status_code == 500

    @pytest.mark.asyncio
    async def test_db_unavailable_after_file_save(self):
        from app.routers.v1.documents_impl import upload_document

        content = b"\x50\x4b\x03\x04" + b"\x00" * 100
        file = MagicMock()
        file.filename = "test.docx"
        file.read = AsyncMock(return_value=content)
        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"
        with (
            patch("app.routers.v1.documents_impl._require_db"),
            patch("app.routers.v1.documents_impl._enforce_daily_upload_quota"),
            patch("app.routers.v1.documents_impl._validate_magic_bytes", return_value=content),
            patch("app.routers.v1.documents_impl._scan_uploaded_file", return_value={"clean": True}),
            patch(
                "app.services.document_crud_service.DocumentCrudService.create_document",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch("app.services.document_crud_service.os.remove"),
            patch("app.routers.v1.documents_impl.settings.MAX_FILE_SIZE", 10485760),
            patch("app.routers.v1.documents_impl.settings.DEFAULT_TEMPLATE", "ieee"),
            patch("app.services.document_pipeline_service.uuid.uuid4", return_value="job-abc"),
        ):
            with pytest.raises(HTTPException) as exc:
                await upload_document(
                    mock_request, MagicMock(), file=file, template="ieee", current_user=MagicMock(id="u1")
                )
            assert exc.value.status_code == 503


class TestDocumentsImplBatchUpload:
    @pytest.mark.asyncio
    async def test_too_many_files(self):
        from app.routers.v1.documents_impl import batch_upload

        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"
        files = [MagicMock() for _ in range(3)]
        with (
            patch("app.routers.v1.documents_impl._require_db"),
            patch("app.routers.v1.documents_impl._enforce_daily_upload_quota"),
            patch("app.routers.v1.documents_impl.settings.MAX_BATCH_FILES", 2),
        ):
            with pytest.raises(HTTPException) as exc:
                await batch_upload(
                    mock_request, MagicMock(), files=files, template="ieee", current_user=MagicMock(id="u1")
                )
            assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_invalid_extension(self):
        from app.routers.v1.documents_impl import batch_upload

        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"
        file1 = MagicMock()
        file1.filename = "bad.exe"
        file1.read = AsyncMock(return_value=b"data")
        with (
            patch("app.routers.v1.documents_impl._require_db"),
            patch("app.routers.v1.documents_impl._enforce_daily_upload_quota"),
            patch("app.routers.v1.documents_impl.settings.MAX_BATCH_FILES", 10),
            patch("app.routers.v1.documents_impl.settings.MAX_FILE_SIZE", 10485760),
            patch("app.routers.v1.documents_impl.audit_log_service.log", new_callable=AsyncMock),
        ):
            result = await batch_upload(
                mock_request, MagicMock(), files=[file1], template="ieee", current_user=MagicMock(id="u1")
            )
            assert result["jobs"][0]["status"] == "rejected"

    @pytest.mark.asyncio
    async def test_file_too_large(self):
        from app.routers.v1.documents_impl import batch_upload

        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"
        file1 = MagicMock()
        file1.filename = "big.docx"
        file1.read = AsyncMock(return_value=b"x" * 99999999)
        with (
            patch("app.routers.v1.documents_impl._require_db"),
            patch("app.routers.v1.documents_impl._enforce_daily_upload_quota"),
            patch("app.routers.v1.documents_impl.settings.MAX_BATCH_FILES", 10),
            patch("app.routers.v1.documents_impl.settings.MAX_FILE_SIZE", 100),
            patch("app.routers.v1.documents_impl.audit_log_service.log", new_callable=AsyncMock),
        ):
            result = await batch_upload(
                mock_request, MagicMock(), files=[file1], template="ieee", current_user=MagicMock(id="u1")
            )
            assert result["jobs"][0]["status"] == "rejected"


class TestDocumentsImplChunkedUpload:
    @pytest.mark.asyncio
    async def test_db_unavailable(self):
        from app.routers.v1.documents_impl import upload_document_chunked

        mock_request = MagicMock()
        with patch(
            "app.routers.v1.documents_impl._require_db",
            side_effect=HTTPException(status_code=503, detail="DB not configured"),
        ):
            with pytest.raises(HTTPException) as exc:
                await upload_document_chunked(
                    mock_request,
                    MagicMock(),
                    file_id="safe",
                    chunk_index=0,
                    total_chunks=1,
                    file=MagicMock(),
                    current_user=MagicMock(id="u1"),
                )
            assert exc.value.status_code == 503


# ── helpers: get_status edge cases ──────────────────────────────────────


class TestGetStatusEdgeCases:
    @pytest.mark.asyncio
    async def test_status_from_processing_statuses(self):
        from app.routers.v1.documents_impl import _STATUS_CACHE_MISS, get_status

        statuses = [
            {
                "status": "PROCESSING",
                "phase": "PARSING",
                "message": "Parsing...",
                "progress_percentage": 50,
                "updated_at": "now",
                "created_at": "now",
            },
        ]
        with (
            patch(
                "app.services.document_crud_service.DocumentCrudService.get_document",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.document_crud_service.DocumentCrudService.get_processing_statuses",
                new_callable=AsyncMock,
                return_value=statuses,
            ),
            patch("app.routers.v1.documents_impl._get_stale_status_response", return_value=_STATUS_CACHE_MISS),
            patch("app.routers.v1.documents_impl._set_cached_status_response"),
            patch("app.routers.v1.documents_impl._require_db"),
        ):
            result = await get_status(job_id="job-1", current_user=None)
            assert result["status"] == "PROCESSING"

    @pytest.mark.asyncio
    async def test_status_stale_response(self):
        from app.routers.v1.documents_impl import get_status

        stale = {"status": "PROCESSING", "progress_percentage": 30}
        with (
            patch(
                "app.services.document_crud_service.DocumentCrudService.get_document",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.document_crud_service.DocumentCrudService.get_processing_statuses",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch("app.routers.v1.documents_impl._get_stale_status_response", return_value=stale),
            patch("app.routers.v1.documents_impl._require_db"),
        ):
            result = await get_status(job_id="job-1", current_user=None)
            assert result["stale"] is True

    @pytest.mark.asyncio
    async def test_status_doc_with_user_id_mismatch(self):
        from app.routers.v1.documents_impl import _STATUS_CACHE_MISS, get_status

        doc = {"user_id": "other-user", "status": "COMPLETED"}
        with (
            patch(
                "app.services.document_crud_service.DocumentCrudService.get_document",
                new_callable=AsyncMock,
                return_value=doc,
            ),
            patch("app.routers.v1.documents_impl._get_stale_status_response", return_value=_STATUS_CACHE_MISS),
            patch("app.routers.v1.documents_impl._require_db"),
        ):
            with pytest.raises(HTTPException) as exc:
                await get_status(job_id="job-1", current_user=MagicMock(id="u1"))
            assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_status_db_unavailable_error(self):
        from app.exceptions import DatabaseUnavailableError
        from app.routers.v1.documents_impl import get_status

        with (
            patch(
                "app.services.document_crud_service.DocumentCrudService.get_document",
                side_effect=DatabaseUnavailableError("DB down"),
            ),
            patch("app.routers.v1.documents_impl._require_db"),
        ):
            with pytest.raises(HTTPException) as exc:
                await get_status(job_id="job-1", current_user=None)
            assert exc.value.status_code == 503

    @pytest.mark.asyncio
    async def test_status_internal_error(self):
        from app.routers.v1.documents_impl import get_status

        with (
            patch(
                "app.services.document_crud_service.DocumentCrudService.get_document",
                side_effect=ValueError("internal"),
            ),
            patch("app.routers.v1.documents_impl._require_db"),
        ):
            with pytest.raises(HTTPException) as exc:
                await get_status(job_id="job-1", current_user=None)
            assert exc.value.status_code == 500


class TestGetDocumentSummaryEdgeCases:
    @pytest.mark.asyncio
    async def test_not_authorized(self):
        from app.routers.v1.documents_impl import get_document_summary

        doc = {"id": "d1", "user_id": "other-user", "filename": "paper.docx", "template": "ieee", "status": "COMPLETED"}
        with (
            patch(
                "app.services.document_crud_service.DocumentCrudService.get_document",
                new_callable=AsyncMock,
                return_value=doc,
            ),
            patch("app.routers.v1.documents_impl._require_db"),
        ):
            with pytest.raises(HTTPException) as exc:
                await get_document_summary("d1", current_user=MagicMock(id="u1"))
            assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_not_found(self):
        from app.routers.v1.documents_impl import get_document_summary

        with (
            patch(
                "app.services.document_crud_service.DocumentCrudService.get_document",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch("app.routers.v1.documents_impl._require_db"),
        ):
            with pytest.raises(HTTPException) as exc:
                await get_document_summary("nonexistent", current_user=None)
            assert exc.value.status_code == 404


class TestListDocumentsEdgeCases:
    @pytest.mark.asyncio
    async def test_db_unavailable_error(self):
        from app.exceptions import DatabaseUnavailableError
        from app.routers.v1.documents_impl import list_documents

        mock_user = MagicMock(id="user-1")
        with (
            patch("app.routers.v1.documents_impl._require_db"),
            patch(
                "app.services.document_crud_service.DocumentCrudService.list_documents",
                side_effect=DatabaseUnavailableError("DB down"),
            ),
        ):
            with pytest.raises(HTTPException) as exc:
                await list_documents(status=None, template=None, limit=50, offset=0, current_user=mock_user)
            assert exc.value.status_code == 503

    @pytest.mark.asyncio
    async def test_internal_error(self):
        from app.routers.v1.documents_impl import list_documents

        mock_user = MagicMock(id="user-1")
        with (
            patch("app.routers.v1.documents_impl._require_db"),
            patch(
                "app.services.document_crud_service.DocumentCrudService.list_documents",
                side_effect=ValueError("internal"),
            ),
        ):
            with pytest.raises(HTTPException) as exc:
                await list_documents(status=None, template=None, limit=50, offset=0, current_user=mock_user)
            assert exc.value.status_code == 500


# ── generator helpers ───────────────────────────────────────────────────


class TestGeneratorGetOrchestrator:
    def test_lazy_init(self):
        import app.routers.v1.generator as gen_mod

        gen_mod._orchestrator = None
        from app.routers.v1.generator import _get_orchestrator

        with patch("app.routers.v1.generator.PipelineOrchestrator", return_value=MagicMock()):
            orch = _get_orchestrator()
            assert orch is not None

    def test_cached(self):
        import app.routers.v1.generator as gen_mod

        gen_mod._orchestrator = MagicMock()
        from app.routers.v1.generator import _get_orchestrator

        orch = _get_orchestrator()
        assert orch is gen_mod._orchestrator


class TestGeneratorGetAgentPipeline:
    def test_lazy_init(self):
        import app.routers.v1.generator as gen_mod

        gen_mod._agent_pipeline = None
        from app.routers.v1.generator import _get_agent_pipeline

        with patch("app.routers.v1.generator.AgentPipeline", return_value=MagicMock()):
            pipeline = _get_agent_pipeline()
            assert pipeline is not None


class TestGeneratorGetSynthesizer:
    def test_lazy_init(self):
        import app.routers.v1.generator as gen_mod

        gen_mod._synthesizer = None
        from app.routers.v1.generator import _get_synthesizer

        with patch("app.routers.v1.generator.MultiDocSynthesizer", return_value=MagicMock()):
            synth = _get_synthesizer()
            assert synth is not None


# ── provider helpers ────────────────────────────────────────────────────


class TestProviderHelpers:
    def test_sanitize_url_ssrf_blocked(self):
        from app.routers.v1.providers import _sanitize_url

        with pytest.raises(HTTPException) as exc:
            _sanitize_url("file:///etc/passwd")
        assert exc.value.status_code == 422
        with pytest.raises(HTTPException) as exc:
            _sanitize_url("ftp://example.com/file")
        assert exc.value.status_code == 422
        with pytest.raises(HTTPException) as exc:
            _sanitize_url("http://169.254.169.254/latest")
        assert exc.value.status_code == 422

    def test_sanitize_url_invalid_scheme(self):
        from app.routers.v1.providers import _sanitize_url

        with pytest.raises(HTTPException) as exc:
            _sanitize_url("gopher://example.com")
        assert exc.value.status_code == 422

    def test_sanitize_url_strips_trailing_slash(self):
        from app.routers.v1.providers import _sanitize_url

        result = _sanitize_url("http://localhost:8080/v1/", allow_local=True)
        assert not result.endswith("/")

    def test_sanitize_url_valid(self):
        from app.routers.v1.providers import _sanitize_url

        result = _sanitize_url("https://api.openai.com/v1")
        assert result == "https://api.openai.com/v1"

    def test_record_provider_metrics(self):
        from app.routers.v1.providers import _record_provider_metrics

        with patch("app.middleware.prometheus_metrics.MetricsManager") as mock_mm:
            _record_provider_metrics("test", "openai", "success")
            mock_mm.record_provider_operation.assert_called_once_with("test", "success")

    def test_record_provider_metrics_exception(self):
        from app.routers.v1.providers import _record_provider_metrics

        with patch(
            "app.middleware.prometheus_metrics.MetricsManager.record_provider_operation", side_effect=Exception("fail")
        ):
            _record_provider_metrics("test", "openai", "success")

    def test_get_user_id_with_attr(self):
        from app.routers.v1.providers import _get_user_id

        user = MagicMock(id="u1")
        assert _get_user_id(user) == "u1"

    def test_get_user_id_string(self):
        from app.routers.v1.providers import _get_user_id

        assert _get_user_id("u1") == "u1"


class TestProviderHealth:
    @pytest.mark.asyncio
    async def test_provider_health(self):
        from app.routers.v1.providers import provider_health

        mock_builtin = {
            "openai": {"env_key": "OPENAI_API_KEY"},
            "ollama": {"env_key": None},
        }
        with (
            patch("app.services.provider_registry.BUILTIN_PROVIDERS", mock_builtin),
            patch("app.config.settings.settings") as mock_s,
        ):
            mock_s.OPENAI_API_KEY = "sk-test"
            result = await provider_health()
            assert result["status"] == "ok"
            assert result["providers"]["openai"] == "configured"
            assert result["providers"]["ollama"] == "local"


class TestDiscoverModels:
    @pytest.mark.asyncio
    async def test_custom_not_found(self):
        from app.routers.v1.providers import discover_models

        mock_db = MagicMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        with patch("app.routers.v1.providers.get_provider_info", return_value=None):
            with pytest.raises(HTTPException) as exc:
                await discover_models("nonexistent", base_url=None, db=mock_db, user=MagicMock(id="u1"))
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_no_base_url(self):
        from app.routers.v1.providers import discover_models

        info = {"name": "test_provider"}
        with patch("app.routers.v1.providers.get_provider_info", return_value=info):
            with pytest.raises(HTTPException) as exc:
                await discover_models("test", base_url=None, db=MagicMock(), user=MagicMock(id="u1"))
            assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_ollama_api_error(self):
        from app.routers.v1.providers import discover_models

        info = {"base_url": "http://localhost:11434"}
        with (
            patch("app.routers.v1.providers.get_provider_info", return_value=info),
            patch("app.routers.v1.providers.resolve_user_api_key", return_value=None),
            patch("httpx.AsyncClient") as mock_client,
        ):
            mock_resp = MagicMock(status_code=500)
            mock_instance = MagicMock()
            mock_instance.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
            mock_client.return_value = mock_instance
            result = await discover_models("ollama", base_url=None, db=MagicMock(), user=MagicMock(id="u1"))
            assert result["error"] == "Status 500"


class TestSyncModels:
    @pytest.mark.asyncio
    async def test_success(self):
        from app.routers.v1.providers import sync_discovered_models

        mock_request = MagicMock()
        mock_request.models = ["model1", "model2"]
        with (
            patch("app.routers.v1.providers.cache_discovered_models"),
            patch("app.routers.v1.providers._record_provider_metrics"),
            patch("app.routers.v1.providers._log_audit", new_callable=AsyncMock),
        ):
            result = await sync_discovered_models("test", mock_request, user=MagicMock(id="u1"))
            assert result["status"] == "ok"
            assert result["models_count"] == 2


# ── documents.py router helpers ─────────────────────────────────────────


class TestDocumentsRouterHelpers:
    def test_normalize_provider_name_all_variants(self):
        from app.routers.v1.documents_impl import _normalize_provider_name

        assert _normalize_provider_name(None) is None
        assert _normalize_provider_name("") is None
        assert _normalize_provider_name("nvidia_nim/test") == "nvidia"
        assert _normalize_provider_name("groq/llama") == "groq"
        assert _normalize_provider_name("ollama/deepseek") == "ollama"
        assert _normalize_provider_name("deepseek-r1") == "ollama"
        assert _normalize_provider_name("gpt-4") == "openai"
        assert _normalize_provider_name("claude-3") == "anthropic"
        assert _normalize_provider_name("rule_based") == "rule_based"
        assert _normalize_provider_name("custom_provider") == "custom_provider"

    def test_extract_quality_payload_none(self):
        from app.routers.v1.documents_impl import _extract_quality_payload

        result = _extract_quality_payload(None)
        assert result["quality_score"] is None
        assert result["quality"] is None

    def test_extract_quality_payload_fallback_keys(self):
        from app.routers.v1.documents_impl import _extract_quality_payload

        result_in = {
            "validation_results": {
                "quality_summary": {
                    "template_compliance_pct": 85.0,
                    "content_completeness_pct": 75.0,
                    "llm_provider_used": "nvidia_nim/test",
                },
            }
        }
        result = _extract_quality_payload(result_in)
        assert result["quality"]["template_compliance"] == 85.0
        assert result["quality"]["content_quality"] == 75.0
        assert result["quality"]["llm_provider_used"] == "nvidia"

    def test_build_initial_status_payload(self):
        from app.routers.v1.documents_impl import _build_initial_status_payload

        payload = _build_initial_status_payload("job-1")
        assert payload["job_id"] == "job-1"
        assert payload["status"] == "PROCESSING"
        assert payload["current_phase"] == "UPLOAD"

    def test_enforce_daily_upload_quota(self):
        from app.routers.v1.documents_impl import _enforce_daily_upload_quota

        _enforce_daily_upload_quota(None)
        _enforce_daily_upload_quota(MagicMock(id="u1"))

    def test_record_upload_ack_duration(self):
        from app.routers.v1.documents_impl import _record_upload_ack_duration

        with patch("app.middleware.prometheus_metrics.MetricsManager") as mock_mm:
            _record_upload_ack_duration(0.0)
            mock_mm.record_upload_ack_duration.assert_called_once()

    def test_record_upload_ack_duration_exception(self):
        from app.routers.v1.documents_impl import _record_upload_ack_duration

        with patch(
            "app.middleware.prometheus_metrics.MetricsManager.record_upload_ack_duration", side_effect=Exception("fail")
        ):
            _record_upload_ack_duration(0.0)


# ── _helpers ────────────────────────────────────────────────────────────


class TestUnderscoreHelpers:
    def test_resolve_persona(self):
        from app.routers.v1._helpers import _resolve_persona

        assert _resolve_persona("/api/v1/documents/upload") == "formatter"
        assert _resolve_persona("/api/v1/generator/sessions") == "authoring"
        assert _resolve_persona("/api/v1/synthesis/sessions") == "synthesis"
        assert _resolve_persona("/api/v1/billing/webhook") == "billing"
        assert _resolve_persona("/api/v1/templates/custom") == "templates"
        assert _resolve_persona("/api/v1/health") == "platform"
        assert _resolve_persona("") == "platform"
        assert _resolve_persona(None) == "platform"

    def test_metric_safe_label(self):
        from app.routers.v1._helpers import _metric_safe_label

        assert _metric_safe_label("Hello World!") == "hello_world"
        assert _metric_safe_label("") == "unknown"
        assert _metric_safe_label("abc123") == "abc123"
        assert _metric_safe_label("___") == "unknown"

    def test_record_persona_kpis(self):
        from app.routers.v1._helpers import _record_persona_kpis

        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/documents/upload"
        with patch("app.middleware.prometheus_metrics.MetricsManager") as mock_mm:
            _record_persona_kpis(mock_request, "upload", True, 0.5)
            mock_mm.record_persona_event.assert_called_once()
            mock_mm.record_persona_latency.assert_called_once()

    def test_record_persona_kpis_exception(self):
        from app.routers.v1._helpers import _record_persona_kpis

        mock_request = MagicMock()
        with patch(
            "app.middleware.prometheus_metrics.MetricsManager.record_persona_event", side_effect=Exception("fail")
        ):
            _record_persona_kpis(mock_request, "test", True, 0.5)

    def test_http_exception_to_response(self):
        from app.routers.v1._helpers import http_exception_to_response

        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"
        exc = HTTPException(status_code=404, detail="Not found")
        response = http_exception_to_response(mock_request, exc)
        assert response.status_code == 404

    def test_http_exception_with_code_map(self):
        from app.routers.v1._helpers import http_exception_to_response

        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"
        exc = HTTPException(status_code=422, detail="Bad input")
        response = http_exception_to_response(mock_request, exc, code_map={422: "CUSTOM_ERROR"})
        assert response.status_code == 422

    def test_http_exception_with_detail_dict(self):
        from app.routers.v1._helpers import http_exception_to_response

        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"
        exc = HTTPException(status_code=400, detail={"field": "error"})
        response = http_exception_to_response(mock_request, exc)
        assert response.status_code == 400

    def test_build_success_response(self):
        from app.routers.v1._helpers import build_success_response

        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"
        response = build_success_response(mock_request, {"key": "value"})
        assert response.status_code == 200

    def test_build_error_response(self):
        from app.routers.v1._helpers import build_error_response

        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"
        response = build_error_response(mock_request, status_code=400, code="BAD_REQUEST", message="bad")
        assert response.status_code == 400

    def test_build_error_response_with_details(self):
        from app.routers.v1._helpers import build_error_response

        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"
        response = build_error_response(
            mock_request, status_code=422, code="VALIDATION", message="invalid", details={"field": "name"}
        )
        assert response.status_code == 422

    def test_run_enveloped_success(self):
        from app.routers.v1._helpers import run_enveloped

        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"
        mock_request.url.path = "/api/v1/test"

        async def op():
            return {"ok": True}

        result = asyncio_run(run_enveloped(mock_request, op, operation_name="test"))
        assert result.status_code == 200

    def test_run_enveloped_http_exception(self):
        from app.routers.v1._helpers import run_enveloped

        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"
        mock_request.url.path = "/api/v1/test"

        async def op():
            raise HTTPException(status_code=404, detail="Not found")

        result = asyncio_run(run_enveloped(mock_request, op, code_map={404: "NOT_FOUND"}, operation_name="test"))
        assert result.status_code == 404

    def test_run_enveloped_unhandled_exception(self):
        from app.routers.v1._helpers import run_enveloped

        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"
        mock_request.url.path = "/api/v1/test"

        async def op():
            raise ValueError("unexpected")

        result = asyncio_run(run_enveloped(mock_request, op, operation_name="test"))
        assert result.status_code == 500


def asyncio_run(coro):
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    return asyncio.run_coroutine_threadsafe(coro, loop).result()


# ── deprecation.py (0% coverage) ────────────────────────────────────────


class TestDeprecation:
    def test_build_deprecation_headers(self):
        from app.routers.deprecation import build_deprecation_headers

        headers = build_deprecation_headers("/api/v2/documents")
        assert headers["Deprecation"] == "true"
        assert "Sunset" in headers
        assert "Link" in headers
        assert "successor-version" in headers["Link"]

    def test_build_deprecation_headers_no_successor(self):
        from app.routers.deprecation import build_deprecation_headers

        headers = build_deprecation_headers(None)
        assert headers["Deprecation"] == "true"
        assert "Link" not in headers

    def test_normalize_path(self):
        from app.routers.deprecation import normalize_path

        assert normalize_path("/api/v1/documents/") == "/api/v1/documents"
        assert normalize_path("/api/v1/documents") == "/api/v1/documents"
        assert normalize_path("/") == "/"
        assert normalize_path("") == ""

    def test_deprecated_route_successor_map_path_format(self):
        from app.routers.deprecation import DeprecatedRoute

        route = DeprecatedRoute(path="/api/v1/old", endpoint=lambda: None)
        route.successor_map = {"/api/v1/old": "/api/v2/new"}
        successor = route._successor_path()
        assert successor == "/api/v2/new"

    def test_deprecated_route_normalized_lookup(self):
        from app.routers.deprecation import DeprecatedRoute

        route = DeprecatedRoute(path="/api/v1/old/", endpoint=lambda: None)
        route.successor_map = {"/api/v1/old": "/api/v2/new"}
        successor = route._successor_path()
        assert successor == "/api/v2/new"

    def test_deprecated_route_no_successor(self):
        from app.routers.deprecation import DeprecatedRoute

        route = DeprecatedRoute(path="/api/v1/unknown", endpoint=lambda: None)
        route.successor_map = {}
        successor = route._successor_path()
        assert successor is None

    def test_deprecated_route_handler_adds_headers(self):
        from fastapi import Response
        from fastapi.routing import APIRoute

        from app.routers.deprecation import DeprecatedRoute

        async def mock_inner(req):
            return Response("ok")

        with patch.object(APIRoute, "get_route_handler", return_value=mock_inner):
            route = DeprecatedRoute(path="/api/v1/old", endpoint=lambda: Response("ok"))
            route.successor_map = {}
            handler = route.get_route_handler()
            response = asyncio_run(handler(MagicMock()))
            assert response.headers.get("Deprecation") == "true"
            assert "Sunset" in response.headers

    def test_deprecated_route_handler_preserves_http_exception_headers(self):
        from fastapi import HTTPException
        from fastapi.routing import APIRoute

        from app.routers.deprecation import DeprecatedRoute

        async def mock_inner(req):
            raise HTTPException(status_code=403, detail="Forbidden", headers={"X-Custom": "val"})

        with patch.object(APIRoute, "get_route_handler", return_value=mock_inner):
            route = DeprecatedRoute(path="/api/v1/old", endpoint=lambda: None)
            route.successor_map = {}
            handler = route.get_route_handler()
            with pytest.raises(HTTPException) as exc:
                asyncio_run(handler(MagicMock()))
            assert exc.value.status_code == 403
            assert exc.value.headers.get("Deprecation") == "true"


# ── stream.py ───────────────────────────────────────────────────────────


class TestStreamEmitEvent:
    @pytest.mark.asyncio
    async def test_emit_event_with_request_id(self):
        from app.routers.v1.stream import emit_event

        mock_pubsub = MagicMock()
        mock_pubsub.publish = AsyncMock()
        with (
            patch("app.routers.v1.stream._pubsub", mock_pubsub),
            patch("app.routers.v1.stream.get_request_id_context", return_value="req-123"),
        ):
            emit_event("job-1", "progress", {"progress": 50, "phase": "EXPORT"})
            mock_pubsub.publish.assert_called_once()
            args = mock_pubsub.publish.call_args[0]
            assert args[0] == "job:job-1"

    @pytest.mark.asyncio
    async def test_emit_event_no_request_id(self):
        from app.routers.v1.stream import emit_event

        mock_pubsub = MagicMock()
        mock_pubsub.publish = AsyncMock()
        with (
            patch("app.routers.v1.stream._pubsub", mock_pubsub),
            patch("app.routers.v1.stream.get_request_id_context", return_value=None),
        ):
            emit_event("job-1", "progress", {"progress": 50})
            mock_pubsub.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_emit_event_runtime_error_fallback(self):
        from app.routers.v1.stream import emit_event

        mock_pubsub = MagicMock()
        mock_pubsub.publish = AsyncMock()
        with (
            patch("app.routers.v1.stream._pubsub", mock_pubsub),
            patch("app.routers.v1.stream.get_request_id_context", return_value=None),
            patch("app.routers.v1.stream.asyncio.get_running_loop", side_effect=RuntimeError("no loop")),
        ):
            with pytest.raises(RuntimeError, match="cannot be called from a running event loop"):
                emit_event("job-1", "progress", {"progress": 50})


# ── preview.py helpers ──────────────────────────────────────────────────


class TestPreviewHelpers:
    def test_valid_session_id(self):
        from app.routers.preview import _valid_session_id

        assert _valid_session_id("abc-123_def")
        assert _valid_session_id("ABC_123")
        assert not _valid_session_id("")
        assert not _valid_session_id("ab")
        assert not _valid_session_id("x" * 65)

    def test_hash_html(self):
        from app.routers.preview import _hash_html

        h1 = _hash_html("hello")
        h2 = _hash_html("hello")
        h3 = _hash_html("world")
        assert h1 == h2
        assert h1 != h3
        assert len(h1) == 12

    def test_chunk_text_empty(self):
        from app.routers.preview import _chunk_text

        assert list(_chunk_text("")) == []
        assert list(_chunk_text(None)) == []

    def test_chunk_text(self):
        from app.routers.preview import _chunk_text

        chunks = list(_chunk_text("a" * 1000, chunk_size=320))
        assert len(chunks) == 4
        assert all(len(c) <= 320 for c in chunks)

    def test_build_ai_messages(self):
        from app.routers.preview import _build_ai_messages

        messages = _build_ai_messages("some content", "IEEE")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert "some content" in messages[1]["content"]

    @pytest.mark.asyncio
    async def test_preview_live(self):
        from app.routers.preview import preview_live

        mock_result = {"html": "<p>hi</p>", "latency_ms": 5, "warnings": []}
        with patch("app.routers.preview.preview_renderer") as mock_pr:
            mock_pr.render_preview.return_value = mock_result
            payload = MagicMock()
            payload.content = "hello"
            payload.templateId = "IEEE"
            result = await preview_live(payload)
        assert result["html"] == "<p>hi</p>"
        assert result["latencyMs"] == 5

    @pytest.mark.asyncio
    async def test_ai_suggest_invalid_session(self):
        from app.routers.preview import ai_suggest

        mock_request = MagicMock()
        with pytest.raises(HTTPException) as exc:
            await ai_suggest(mock_request, sessionId="ab", content="test")
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_ai_suggest_valid(self):
        from app.routers.preview import ai_suggest

        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"

        async def _mock_to_thread(fn, *args, **kwargs):
            return fn(*args, **kwargs)

        with (
            patch(
                "app.routers.preview.generate_with_fallback",
                return_value={"text": " suggestion text ", "model": "gpt-4", "tier": "nvidia"},
            ),
            patch("app.routers.preview.asyncio.to_thread", new=_mock_to_thread),
        ):
            response = await ai_suggest(mock_request, "valid-session", "test", "IEEE")
            events = []
            async for raw in response.body_iterator:
                events.append(raw)
                if raw.get("event") == "done":
                    break
        assert any(e.get("event") == "status" for e in events)
        assert any(e.get("event") == "done" for e in events)

    @pytest.mark.asyncio
    async def test_ai_suggest_llm_unavailable(self):
        from app.routers.preview import LLMUnavailableError, ai_suggest

        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"

        async def _mock_to_thread(fn, *args, **kwargs):
            return fn(*args, **kwargs)

        with (
            patch("app.routers.preview.generate_with_fallback", side_effect=LLMUnavailableError("LLM down")),
            patch("app.routers.preview.asyncio.to_thread", new=_mock_to_thread),
        ):
            response = await ai_suggest(mock_request, "valid-session", "test", "IEEE")
            events = []
            async for raw in response.body_iterator:
                events.append(raw)
                if raw.get("event") == "error":
                    break
        assert any(e.get("event") == "error" for e in events)

    @pytest.mark.asyncio
    async def test_preview_ws_invalid_session(self):
        from app.routers.preview import preview_ws

        ws_mock = MagicMock()
        ws_mock.close = AsyncMock()
        await preview_ws(ws_mock, "ab")
        ws_mock.close.assert_called_once_with(code=1008)

    @pytest.mark.asyncio
    async def test_heartbeat(self):
        from app.routers.preview import _heartbeat

        ws_mock = AsyncMock()
        ws_mock.send_json.side_effect = [None, Exception("stop")]
        with pytest.raises(Exception):
            await _heartbeat(ws_mock)


# ── billing helpers ─────────────────────────────────────────────────────


class TestBillingHelpers:
    def test_get_user_id_from_metadata(self):
        from app.routers.v1.billing import _get_user_id_from_metadata

        assert _get_user_id_from_metadata({"metadata": {"user_id": "u1"}}) == "u1"
        assert _get_user_id_from_metadata({"metadata": None}) is None
        assert _get_user_id_from_metadata({}) is None

    def test_legacy_profile_updates(self):
        from app.routers.v1.billing import _legacy_profile_updates

        assert _legacy_profile_updates({"plan_tier": "pro"}) == {"plan": "pro"}
        assert _legacy_profile_updates({"billing_status": "active"}) == {}

    def test_lookup_user_id_by_customer_no_customer_id(self):
        from app.routers.v1.billing import _lookup_user_id_by_customer

        assert _lookup_user_id_by_customer(MagicMock(), None) is None

    def test_lookup_user_id_by_customer_not_found(self):
        from app.routers.v1.billing import _lookup_user_id_by_customer

        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = (
            MagicMock(data=None)
        )
        assert _lookup_user_id_by_customer(sb, "cus_1") is None

    def test_lookup_user_id_by_customer_found(self):
        from app.routers.v1.billing import _lookup_user_id_by_customer

        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = (
            MagicMock(data={"id": "user-1"})
        )
        assert _lookup_user_id_by_customer(sb, "cus_1") == "user-1"

    def test_lookup_user_id_by_customer_exception(self):
        from app.routers.v1.billing import _lookup_user_id_by_customer

        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.side_effect = (
            Exception("fail")
        )
        assert _lookup_user_id_by_customer(sb, "cus_1") is None


# ── auth helpers ────────────────────────────────────────────────────────


class TestAuthHelper:
    def test_router_defined(self):
        from app.routers.v1.auth import router

        assert router is not None
        routes = [r.path for r in router.routes]
        assert "/me" in routes
        assert "/signup" in routes
        assert "/login" in routes
        assert "/forgot-password" in routes
        assert "/verify-otp" in routes
        assert "/reset-password" in routes


# ── health helpers ──────────────────────────────────────────────────────


class TestHealthRouter:
    def test_health_build_success(self):
        from app.routers.v1.health import health

        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"
        result = asyncio_run(health(mock_request))
        assert result.status_code == 200

    def test_live(self):
        from app.routers.v1.health import live

        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"
        result = asyncio_run(live(mock_request))
        assert result.status_code == 200

    def test_ready_success(self):
        from app.routers.v1.health import ready

        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"
        with patch("app.routers.v1.health.get_readiness_payload", return_value=({"db": "healthy"}, 200)):
            result = asyncio_run(ready(mock_request))
        assert result.status_code == 200

    def test_ready_exception(self):
        from app.routers.v1.health import ready

        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"
        with patch("app.routers.v1.health.get_readiness_payload", side_effect=Exception("fail")):
            result = asyncio_run(ready(mock_request))
        assert result.status_code == 500

    def test_admin_health(self):
        from app.routers.v1.health import admin_health

        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"
        result = asyncio_run(admin_health(mock_request, _admin_user=MagicMock()))
        assert result.status_code == 200


# ── metrics helpers ─────────────────────────────────────────────────────


class TestMetricsHelpers:
    def test_log_frontend_error(self):
        from app.routers.v1.metrics import log_frontend_error

        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"
        with patch("app.routers.v1.metrics.run_enveloped") as mock_run:
            mock_run.return_value = MagicMock()
            result = asyncio_run(log_frontend_error(mock_request, {"message": "test"}, current_user=None))
            assert result is not None

    def test_log_frontend_error_minimal(self):
        from app.routers.v1.metrics import log_frontend_error

        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"
        with patch("app.routers.v1.metrics.run_enveloped") as mock_run:
            mock_run.return_value = MagicMock()
            result = asyncio_run(log_frontend_error(mock_request, {"message": "test"}, current_user=None))
            assert result is not None

    def test_metrics_db_requires_admin(self):
        from app.routers.v1.metrics import get_database_metrics

        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"
        with patch("app.routers.v1.metrics.run_enveloped") as mock_run:
            mock_run.return_value = MagicMock()
            result = asyncio_run(get_database_metrics(mock_request, admin_user=MagicMock()))
            assert result is not None

    def test_enhancement_metrics(self):
        from app.routers.v1.metrics import get_enhancement_metrics

        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"
        with patch("app.routers.v1.metrics.run_enveloped") as mock_run:
            mock_run.return_value = MagicMock()
            result = asyncio_run(get_enhancement_metrics(mock_request, admin_user=MagicMock()))
            assert result is not None

    def test_vllm_readiness(self):
        from app.routers.v1.metrics import get_vllm_readiness

        mock_request = MagicMock()
        mock_request.state.request_id = "req-1"
        with patch("app.routers.v1.metrics.run_enveloped") as mock_run:
            mock_run.return_value = MagicMock()
            result = asyncio_run(get_vllm_readiness(mock_request, admin_user=MagicMock()))
            assert result is not None


# ── templates helpers ───────────────────────────────────────────────────


class TestTemplateHelpers:
    def test_canonical_template_id(self):
        from app.routers.v1.templates import _canonical_template_id

        assert _canonical_template_id("My Template") == "my_template"
        assert _canonical_template_id(" IEEE ") == "ieee"
        assert _canonical_template_id("") == ""
        assert _canonical_template_id(None) == ""

    def test_template_display_name(self):
        from app.routers.v1.templates import _template_display_name

        assert _template_display_name("none") == "None"
        assert _template_display_name("ieee") == "IEEE"
        assert _template_display_name("apa") == "APA"
        assert _template_display_name("acm") == "ACM"
        assert _template_display_name("mla") == "MLA"
        assert _template_display_name("springer") == "Springer"
        assert _template_display_name("modern_blue") == "Modern Blue"

    def test_require_db_unavailable(self):
        from app.routers.v1.templates import _require_db

        with patch("app.routers.v1.templates.get_supabase_client", return_value=None):
            with pytest.raises(HTTPException) as exc:
                _require_db()
            assert exc.value.status_code == 503

    def test_require_user_none(self):
        from app.routers.v1.templates import _require_user

        with pytest.raises(HTTPException) as exc:
            _require_user(None)
        assert exc.value.status_code == 401

    def test_extract_payload_non_dict(self):
        from app.routers.v1.templates import _extract_template_payload

        with pytest.raises(HTTPException) as exc:
            _extract_template_payload("not a dict")
        assert exc.value.status_code == 422

    def test_extract_payload_no_name(self):
        from app.routers.v1.templates import _extract_template_payload

        with pytest.raises(HTTPException) as exc:
            _extract_template_payload({"config": {}})
        assert exc.value.status_code == 422

    def test_extract_payload_config_as_list(self):
        from app.routers.v1.templates import _extract_template_payload

        with pytest.raises(HTTPException) as exc:
            _extract_template_payload({"name": "Test", "config": ["not", "object"]})
        assert exc.value.status_code == 422

    def test_extract_payload_from_template_key(self):
        from app.routers.v1.templates import _extract_template_payload

        result = _extract_template_payload({"template": {"name": "Nested", "settings": {"font": "serif"}}})
        assert result["config"] == {"font": "serif"}
        assert result["name"] == "Nested"

    def test_extract_payload_description_none(self):
        from app.routers.v1.templates import _extract_template_payload

        result = _extract_template_payload({"template": {"name": "Desc", "description": None, "config": {}}})
        assert result["description"] == ""

    def test_list_builtin_templates(self):
        from app.routers.v1.templates import _list_builtin_templates

        with (
            patch("app.routers.v1.templates.Path.exists", return_value=True),
            patch("app.routers.v1.templates.Path.iterdir") as mock_iter,
        ):
            mock_dir = MagicMock()
            mock_dir.name = "ieee"
            mock_dir.is_dir.return_value = True
            mock_iter.return_value = [mock_dir]
            result = asyncio_run(_list_builtin_templates())
            assert len(result["templates"]) == 1
            assert result["templates"][0]["id"] == "ieee"

    def test_list_builtin_no_dir(self):
        from app.routers.v1.templates import _list_builtin_templates

        with patch("app.routers.v1.templates.Path.exists", return_value=False):
            result = asyncio_run(_list_builtin_templates())
            assert result == {"templates": []}

    def test_csl_search_empty(self):
        from app.routers.v1.templates import _csl_search

        with pytest.raises(HTTPException) as exc:
            asyncio_run(_csl_search())
        assert exc.value.status_code == 422

    def test_csl_search_with_query(self):
        from app.routers.v1.templates import _csl_search

        with patch("app.routers.v1.templates.search_styles", new=AsyncMock(return_value=[{"slug": "nature"}])):
            result = asyncio_run(_csl_search(q="nature"))
            assert result["query"] == "nature"

    def test_csl_fetch_value_error(self):
        from app.routers.v1.templates import _fetch_csl_style

        with (
            patch("app.routers.v1.templates.fetch_style", new=AsyncMock(side_effect=ValueError("bad"))),
        ):
            with pytest.raises(HTTPException) as exc:
                asyncio_run(_fetch_csl_style("bad"))
            assert exc.value.status_code == 400

    def test_csl_fetch_exception(self):
        from app.routers.v1.templates import _fetch_csl_style

        with (
            patch("app.routers.v1.templates.fetch_style", new=AsyncMock(side_effect=Exception("fail"))),
        ):
            with pytest.raises(HTTPException) as exc:
                asyncio_run(_fetch_csl_style("fail"))
            assert exc.value.status_code == 502


# ── api_keys helpers ────────────────────────────────────────────────────


class TestApiKeysHelpers:
    def test_apply_rate_limit_headers(self):
        from app.routers.v1.api_keys import apply_rate_limit_headers
        from app.services.api_key_rate_limiter import RateLimitResult

        response = MagicMock()
        response.headers = {}
        result = RateLimitResult(allowed=True, limit=100, remaining=50, reset_at=1000.0, retry_after=5.0)
        apply_rate_limit_headers(response, result)
        assert response.headers["X-RateLimit-Limit"] == "100"
        assert response.headers["X-RateLimit-Remaining"] == "50"
        assert response.headers["Retry-After"] == "6"

    def test_apply_rate_limit_no_retry(self):
        from app.routers.v1.api_keys import apply_rate_limit_headers
        from app.services.api_key_rate_limiter import RateLimitResult

        response = MagicMock()
        response.headers = {}
        result = RateLimitResult(allowed=True, limit=60, remaining=30, reset_at=2000.0, retry_after=None)
        apply_rate_limit_headers(response, result)
        assert "Retry-After" not in response.headers

    def test_get_supported_providers(self):
        from app.routers.v1.api_keys import get_supported_providers

        mock_providers = {
            "openai": {"name": "OpenAI", "default_rpm": 60, "default_rph": 1000, "default_daily": 10000},
        }
        with patch("app.routers.v1.api_keys.ApiKeyService.get_supported_providers", return_value=mock_providers):
            result = asyncio_run(get_supported_providers())
            assert "openai" in result
            assert result["openai"].name == "OpenAI"


# ── synthesis helpers (reuse existing pattern) ──────────────────────────


class TestSynthesisHelpers:
    def test_parse_config_valid(self):
        from app.routers.v1.synthesis import _parse_config

        assert _parse_config('{"key": "val"}') == {"key": "val"}

    def test_parse_config_empty(self):
        from app.routers.v1.synthesis import _parse_config

        assert _parse_config("") == {}

    def test_parse_config_invalid(self):
        from app.routers.v1.synthesis import _parse_config

        with pytest.raises(HTTPException) as exc:
            _parse_config("{bad json}")
        assert exc.value.status_code == 422

    def test_assert_session_owner_match(self):
        from app.routers.v1.synthesis import _assert_session_owner

        _assert_session_owner({"user_id": "u1"}, MagicMock(id="u1"))

    def test_assert_session_owner_mismatch(self):
        from app.routers.v1.synthesis import _assert_session_owner

        with pytest.raises(HTTPException) as exc:
            _assert_session_owner({"user_id": "other"}, MagicMock(id="u1"))
        assert exc.value.status_code == 403

    def test_get_orchestrator(self):
        import app.routers.v1.synthesis as syn

        syn._orchestrator = None
        from app.routers.v1.synthesis import _get_orchestrator

        with patch("app.routers.v1.synthesis.PipelineOrchestrator", return_value=MagicMock()):
            assert _get_orchestrator() is not None

    def test_get_synthesizer(self):
        import app.routers.v1.synthesis as syn

        syn._orchestrator = None
        syn._synthesizer = None
        from app.routers.v1.synthesis import _get_synthesizer

        with patch("app.routers.v1.synthesis.MultiDocSynthesizer", return_value=MagicMock()):
            assert _get_synthesizer() is not None
