from unittest.mock import MagicMock, patch


class TestProcessDocumentTask:
    def test_process_document_success(self):
        from app.tasks.celery_tasks import process_document_task
        with patch("app.tasks.celery_tasks.DocumentService.get_document", return_value={"original_file_path": "/tmp/test.docx"}), \
             patch("app.tasks.celery_tasks.DocumentService.update_document"), \
             patch("app.tasks.celery_tasks.DocumentService.mark_document_failed"), \
             patch("app.tasks.celery_tasks.PipelineOrchestrator") as MockOrch:
            MockOrch.return_value.run_pipeline.return_value = None
            result = process_document_task("doc-id")
        assert result is True

    def test_process_document_not_found(self):
        from app.tasks.celery_tasks import process_document_task
        with patch("app.tasks.celery_tasks.DocumentService.get_document", return_value=None):
            result = process_document_task("doc-id")
        assert result is False

    def test_process_document_exception(self):
        from app.tasks.celery_tasks import process_document_task
        with patch("app.tasks.celery_tasks.DocumentService.get_document", return_value={"original_file_path": "/tmp/test.docx"}), \
             patch("app.tasks.celery_tasks.DocumentService.update_document"), \
             patch("app.tasks.celery_tasks.DocumentService.mark_document_failed"), \
             patch("app.tasks.celery_tasks.PipelineOrchestrator") as MockOrch:
            MockOrch.return_value.run_pipeline.side_effect = Exception("pipeline error")
            result = process_document_task("doc-id")
        assert result is False

    def test_process_generation_success(self):
        from app.tasks.celery_tasks import process_generation_task
        import app.tasks.celery_tasks as ct
        with patch.object(ct, "asyncio") as mock_asyncio, \
             patch("app.tasks.celery_tasks.DocumentService.mark_document_failed"):
            mock_asyncio.run.return_value = None
            result = process_generation_task("job-1")
        assert result is True

    def test_process_generation_exception(self):
        from app.tasks.celery_tasks import process_generation_task
        import app.tasks.celery_tasks as ct
        with patch.object(ct, "asyncio") as mock_asyncio, \
             patch("app.tasks.celery_tasks.DocumentService.mark_document_failed"):
            mock_asyncio.run.side_effect = Exception("gen error")
            result = process_generation_task("job-1")
        assert result is False

    def test_process_synthesis_success(self):
        from app.tasks.celery_tasks import process_synthesis_task
        import app.tasks.celery_tasks as ct
        with patch.object(ct, "asyncio") as mock_asyncio:
            mock_asyncio.run.return_value = None
            result = process_synthesis_task("sess-1", ["/f1.docx"], "IEEE")
        assert result is True

    def test_agent_pipeline_success(self):
        from app.tasks.celery_tasks import process_agent_pipeline_task
        import app.tasks.celery_tasks as ct
        with patch.object(ct, "asyncio") as mock_asyncio, \
             patch("app.tasks.celery_tasks.DocumentService.mark_document_failed"):
            mock_asyncio.run.return_value = None
            result = process_agent_pipeline_task("sess-1", "write")
        assert result is True

    def test_agent_resume_success(self):
        from app.tasks.celery_tasks import process_agent_resume_task
        import app.tasks.celery_tasks as ct
        with patch.object(ct, "asyncio") as mock_asyncio, \
             patch("app.tasks.celery_tasks.DocumentService.mark_document_failed"):
            mock_asyncio.run.return_value = None
            result = process_agent_resume_task("sess-1")
        assert result is True

    def test_agent_rewrite_success(self):
        from app.tasks.celery_tasks import process_agent_rewrite_task
        import app.tasks.celery_tasks as ct
        with patch.object(ct, "asyncio") as mock_asyncio, \
             patch("app.tasks.celery_tasks.DocumentService.mark_document_failed"):
            mock_asyncio.run.return_value = None
            result = process_agent_rewrite_task("sess-1", "intro", "shorter")
        assert result is True

    def test_edit_document_success(self):
        from app.tasks.celery_tasks import process_edit_document_task
        with patch("app.tasks.celery_tasks.PipelineOrchestrator") as MockOrch:
            MockOrch.return_value.run_edit_flow.return_value = {"status": "success"}
            result = process_edit_document_task("job-1", {"key": "val"}, "IEEE")
        assert result is True

    def test_edit_document_not_success(self):
        from app.tasks.celery_tasks import process_edit_document_task
        with patch("app.tasks.celery_tasks.PipelineOrchestrator") as MockOrch:
            MockOrch.return_value.run_edit_flow.return_value = {"status": "error"}
            result = process_edit_document_task("job-1", {}, "IEEE")
        assert result is False

    def test_edit_document_exception(self):
        from app.tasks.celery_tasks import process_edit_document_task
        with patch("app.tasks.celery_tasks.PipelineOrchestrator") as MockOrch, \
             patch("app.tasks.celery_tasks.DocumentService.mark_document_failed"):
            MockOrch.return_value.run_edit_flow.side_effect = Exception("edit error")
            result = process_edit_document_task("job-1", {}, "IEEE")
        assert result is False

    def test_cleanup_uploads(self):
        from app.tasks.celery_tasks import cleanup_uploads_task
        with patch("app.tasks.celery_tasks.cleanup_stranded_uploads", return_value={"deleted_files": 5, "removed_dirs": 2}), \
             patch("app.tasks.celery_tasks.settings.RETENTION_DAYS", 30):
            result = cleanup_uploads_task(upload_dir="uploads", retention_days=7)
        assert result["deleted"] == 5
        assert result["retention_days"] == 7

    def test_cleanup_uploads_default_retention(self):
        from app.tasks.celery_tasks import cleanup_uploads_task
        with patch("app.tasks.celery_tasks.cleanup_stranded_uploads", return_value={"deleted_files": 0, "removed_dirs": 0}), \
             patch("app.tasks.celery_tasks.settings.RETENTION_DAYS", 30):
            result = cleanup_uploads_task()
        assert result["retention_days"] == 30

    def test_scibert_missing_fixtures(self):
        from app.tasks.celery_tasks import scibert_benchmark_task
        with patch("app.tasks.celery_tasks.settings"):  # ensure settings mock is active
            with patch("pathlib.Path.exists", return_value=False):
                result = scibert_benchmark_task(fixtures_dir="/nonexistent")
        assert result["status"] == "missing_fixtures"

    def test_scibert_full_run(self, tmp_path):
        labels = tmp_path / "labels.json"
        labels.write_text('{"paper1.pdf": {"labels": ["abstract"]}}', encoding="utf-8")
        (tmp_path / "paper1.pdf").write_text("fake", encoding="utf-8")

        from app.tasks.celery_tasks import scibert_benchmark_task
        with patch("app.pipeline.parsing.parser_factory.ParserFactory") as MockPF:
            parser = MagicMock()
            parser.parse.return_value.blocks = []
            MockPF.return_value.get_parser.return_value = parser
            with patch("app.pipeline.intelligence.semantic_parser.SemanticParser") as MockSP:
                MockSP.return_value.analyze_blocks.return_value = [{"predicted_section_type": "abstract"}]
                with patch("app.tasks.celery_tasks.persist_scibert_benchmark_result"):
                    result = scibert_benchmark_task(fixtures_dir=str(tmp_path))
        assert result["status"] == "ok"

    def test_scibert_label_mismatch(self, tmp_path):
        labels = tmp_path / "labels.json"
        labels.write_text('{"paper1.pdf": {"labels": ["abstract", "methods"]}}', encoding="utf-8")
        (tmp_path / "paper1.pdf").write_text("fake", encoding="utf-8")

        from app.tasks.celery_tasks import scibert_benchmark_task
        with patch("app.pipeline.parsing.parser_factory.ParserFactory") as MockPF:
            parser = MagicMock()
            parser.parse.return_value.blocks = []
            MockPF.return_value.get_parser.return_value = parser
            with patch("app.pipeline.intelligence.semantic_parser.SemanticParser") as MockSP:
                MockSP.return_value.analyze_blocks.return_value = [{"predicted_section_type": "abstract"}]
                with patch("app.tasks.celery_tasks.persist_scibert_benchmark_result"):
                    result = scibert_benchmark_task(fixtures_dir=str(tmp_path))
        assert "status" in result

    def test_scibert_no_parser(self, tmp_path):
        labels = tmp_path / "labels.json"
        labels.write_text('{"paper1.pdf": {"labels": ["abstract"]}}', encoding="utf-8")
        (tmp_path / "paper1.pdf").write_text("fake", encoding="utf-8")

        from app.tasks.celery_tasks import scibert_benchmark_task
        with patch("app.pipeline.parsing.parser_factory.ParserFactory") as MockPF:
            MockPF.return_value.get_parser.return_value = None
            with patch("app.tasks.celery_tasks.persist_scibert_benchmark_result"):
                result = scibert_benchmark_task(fixtures_dir=str(tmp_path))
        assert "status" in result


class TestMacroF1:
    def test_perfect(self):
        def _macro_f1(y_true, y_pred):
            labels = sorted(set(y_true) | set(y_pred))
            f1s = []
            for label in labels:
                tp = sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
                fp = sum(1 for t, p in zip(y_true, y_pred) if t != label and p == label)
                fn = sum(1 for t, p in zip(y_true, y_pred) if t == label and p != label)
                if tp == 0 and fp == 0 and fn == 0:
                    continue
                precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
                recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
                f1 = 0.0 if (precision + recall) == 0 else (2 * precision * recall) / (precision + recall)
                f1s.append(f1)
            return sum(f1s) / len(f1s) if f1s else 0.0

        assert _macro_f1(["a", "b"], ["a", "b"]) == 1.0
        assert _macro_f1(["a", "b"], ["c", "d"]) == 0.0
        assert _macro_f1([], []) == 0.0
