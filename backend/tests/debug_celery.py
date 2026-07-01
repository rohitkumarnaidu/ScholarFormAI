"""Debug celery task patching."""
import sys
for k in list(sys.modules):
    if 'celery_tasks' in k:
        del sys.modules[k]

from unittest.mock import MagicMock, patch, AsyncMock

# Try different patch targets
for target in [
    "app.tasks.celery_tasks.DocumentService.get_document",
]:
    sys.modules.pop("app.tasks.celery_tasks", None)
    sys.modules.pop("app.services.document_service", None)

    print(f"\n=== Trying patch target: {target} ===")
    with patch(target, return_value={"original_file_path": "/tmp/test.docx"}) as mock_gd, \
         patch("app.tasks.celery_tasks.DocumentService.update_document"), \
         patch("app.tasks.celery_tasks.DocumentService.mark_document_failed"), \
         patch("app.tasks.celery_tasks.PipelineOrchestrator") as MockOrch:

        from app.tasks.celery_tasks import process_document_task
        import app.tasks.celery_tasks as ct

        doc_service = ct.DocumentService
        print(f"  DocumentService is: {doc_service}")
        gd = getattr(doc_service, "get_document", None)
        print(f"  DocumentService.get_document is: {gd}")
        if gd:
            result = gd("doc-id")
            print(f"  Direct call to DocumentService.get_document('doc-id'): {result}")

        MockOrch.return_value.run_pipeline.return_value = None
        result = process_document_task("doc-id")
        print(f"  process_document_task result: {result}")
