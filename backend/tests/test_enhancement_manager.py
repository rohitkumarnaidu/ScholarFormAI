from unittest.mock import MagicMock, patch, call

import pytest


class TestCoerceBool:
    def test_none_returns_default(self):
        from app.services.enhancement_manager import _coerce_bool
        assert _coerce_bool(None) is False
        assert _coerce_bool(None, True) is True

    def test_bool_passthrough(self):
        from app.services.enhancement_manager import _coerce_bool
        assert _coerce_bool(True) is True
        assert _coerce_bool(False) is False

    def test_numeric(self):
        from app.services.enhancement_manager import _coerce_bool
        assert _coerce_bool(1) is True
        assert _coerce_bool(0) is False

    def test_string_values(self):
        from app.services.enhancement_manager import _coerce_bool
        assert _coerce_bool("true") is True
        assert _coerce_bool("yes") is True
        assert _coerce_bool("on") is True
        assert _coerce_bool("false") is False
        assert _coerce_bool("off") is False
        assert _coerce_bool("maybe") is False


class TestModuleAvailable:
    def test_found(self):
        from app.services.enhancement_manager import _module_available
        with patch("importlib.util.find_spec", return_value=object()):
            assert _module_available("some_module") is True

    def test_not_found(self):
        from app.services.enhancement_manager import _module_available
        with patch("importlib.util.find_spec", return_value=None):
            assert _module_available("some_module") is False

    def test_find_spec_raises(self):
        from app.services.enhancement_manager import _module_available
        with patch("importlib.util.find_spec", side_effect=ValueError):
            assert _module_available("some_module") is False


class TestSplitCsv:
    def test_none_or_empty(self):
        from app.services.enhancement_manager import _split_csv
        assert _split_csv(None, ["a"]) == ["a"]
        assert _split_csv("", ["a"]) == ["a"]

    def parses_csv(self):
        from app.services.enhancement_manager import _split_csv
        result = _split_csv("a,b,c", ["x"])
        assert result == ["a", "b", "c"]

    def test_strips_and_lowers(self):
        from app.services.enhancement_manager import _split_csv
        result = _split_csv("  Alpha , BETA ", ["x"])
        assert result == ["alpha", "beta"]

    def test_filters_empty(self):
        from app.services.enhancement_manager import _split_csv
        result = _split_csv("a,,b,", ["x"])
        assert result == ["a", "b"]


class TestEnhancementProfile:
    def test_to_dict(self):
        from app.services.enhancement_manager import EnhancementProfile
        p = EnhancementProfile(
            enabled=True, queue_enabled=False, queue_provider="local",
            queue_available=False, ocr_enabled=True, ocr_backends=["tesseract"],
            keyword_enabled=True, keyword_backends=["basic"],
        )
        d = p.to_dict()
        assert d["enabled"] is True
        assert d["queue_enabled"] is False
        assert d["ocr_backends"] == ["tesseract"]
        assert d["keyword_backends"] == ["basic"]


class TestProfile:
    @pytest.fixture
    def mgr(self):
        from app.services.enhancement_manager import EnhancementManager
        m = EnhancementManager()
        m._profile = None
        return m

    def test_lazy_initialization(self, mgr):
        assert mgr._profile is None
        p = mgr.profile
        assert p is not None
        assert mgr._profile is p

    def test_refresh_rebuilds(self, mgr):
        p1 = mgr.profile
        p2 = mgr.refresh()
        assert p2 is not p1

    def test_is_celery_active(self, mgr):
        mgr._profile = MagicMock(
            enabled=True, queue_enabled=True, queue_provider="celery", queue_available=True
        )
        assert mgr.is_celery_queue_active() is True

    def test_is_celery_not_active_when_disabled(self, mgr):
        mgr._profile = MagicMock(enabled=False)
        assert mgr.is_celery_queue_active() is False

    def test_queue_threshold_default(self, mgr):
        assert mgr._queue_threshold_seconds() == 5.0

    def test_queue_threshold_from_settings(self, mgr):
        with patch("app.services.enhancement_manager.settings") as mock_s:
            mock_s.ENHANCEMENT_QUEUE_MIN_SECONDS = 10
            assert mgr._queue_threshold_seconds() == 10.0

    def test_should_queue_job_celery_active(self, mgr):
        mgr._profile = MagicMock(
            enabled=True, queue_enabled=True, queue_provider="celery", queue_available=True
        )
        assert mgr.should_queue_job(20.0) is True
        assert mgr.should_queue_job(3.0) is False
        assert mgr.should_queue_job(None) is True

    def test_should_queue_job_celery_not_active(self, mgr):
        mgr._profile = MagicMock(enabled=False)
        assert mgr.should_queue_job(20.0) is False

    def test_get_ocr_backends(self, mgr):
        mgr._profile = MagicMock(ocr_backends=["a", "b"])
        assert mgr.get_ocr_backends() == ["a", "b"]

    def test_get_keyword_backends(self, mgr):
        mgr._profile = MagicMock(keyword_backends=["x"])
        assert mgr.get_keyword_backends() == ["x"]


class TestDispatchDocumentPipeline:
    @pytest.fixture
    def mgr(self):
        from app.services.enhancement_manager import EnhancementManager
        m = EnhancementManager()
        m._profile = MagicMock(
            enabled=True, queue_enabled=True, queue_provider="celery", queue_available=True
        )
        return m

    def test_celery_path(self, mgr):
        bt = MagicMock()
        orc = MagicMock()
        mock_task = MagicMock()
        mock_task.apply_async.return_value = MagicMock(id="task-1")
        with patch("app.tasks.celery_tasks.process_document_task", mock_task):
            result = mgr.dispatch_document_pipeline(
                background_tasks=bt, orchestrator=orc,
                input_path="/in", job_id="j1", template_name="ieee",
            )
        assert result == {"mode": "celery", "task_id": "task-1"}
        bt.add_task.assert_not_called()

    def test_background_fallback(self, mgr):
        bt = MagicMock()
        orc = MagicMock()
        mock_task = MagicMock()
        mock_task.apply_async.side_effect = RuntimeError("celery down")
        with patch("app.tasks.celery_tasks.process_document_task", mock_task):
            result = mgr.dispatch_document_pipeline(
                background_tasks=bt, orchestrator=orc,
                input_path="/in", job_id="j1", template_name="ieee",
            )
        assert result == {"mode": "background", "task_id": None}
        bt.add_task.assert_called_once()

    def test_background_when_queue_not_active(self, mgr):
        mgr._profile = MagicMock(enabled=False)
        bt = MagicMock()
        orc = MagicMock()
        result = mgr.dispatch_document_pipeline(
            background_tasks=bt, orchestrator=orc,
            input_path="/in", job_id="j1", template_name="ieee",
        )
        assert result == {"mode": "background", "task_id": None}


class TestDispatchGenerationPipeline:
    @pytest.fixture
    def mgr(self):
        from app.services.enhancement_manager import EnhancementManager
        m = EnhancementManager()
        m._profile = MagicMock(
            enabled=True, queue_enabled=True, queue_provider="celery", queue_available=True
        )
        return m

    def test_celery_path(self, mgr):
        bt = MagicMock()
        mock_task = MagicMock()
        mock_task.apply_async.return_value = MagicMock(id="gen-1")
        with patch("app.tasks.celery_tasks.process_generation_task", mock_task):
            result = mgr.dispatch_generation_pipeline(
                background_tasks=bt, run_pipeline=MagicMock(), job_id="j1",
            )
        assert result == {"mode": "celery", "task_id": "gen-1"}

    def test_background_fallback(self, mgr):
        bt = MagicMock()
        mock_task = MagicMock()
        mock_task.apply_async.side_effect = RuntimeError("celery down")
        run_pipe = MagicMock()
        with patch("app.tasks.celery_tasks.process_generation_task", mock_task):
            result = mgr.dispatch_generation_pipeline(
                background_tasks=bt, run_pipeline=run_pipe, job_id="j1",
            )
        assert result == {"mode": "background", "task_id": None}
        bt.add_task.assert_called_once_with(run_pipe, "j1")


class TestDispatchEditFlow:
    @pytest.fixture
    def mgr(self):
        from app.services.enhancement_manager import EnhancementManager
        m = EnhancementManager()
        m._profile = MagicMock(
            enabled=True, queue_enabled=True, queue_provider="celery", queue_available=True
        )
        return m

    def test_celery_path(self, mgr):
        bt = MagicMock()
        mock_task = MagicMock()
        mock_task.apply_async.return_value = MagicMock(id="edit-1")
        with patch("app.tasks.celery_tasks.process_edit_document_task", mock_task):
            result = mgr.dispatch_edit_flow(
                background_tasks=bt, orchestrator=MagicMock(),
                job_id="j1", edited_structured_data={"key": "val"}, template_name="ieee",
            )
        assert result == {"mode": "celery", "task_id": "edit-1"}

    def test_background_fallback(self, mgr):
        bt = MagicMock()
        orc = MagicMock()
        orc.run_edit_flow = MagicMock()
        mock_task = MagicMock()
        mock_task.apply_async.side_effect = RuntimeError("celery down")
        with patch("app.tasks.celery_tasks.process_edit_document_task", mock_task):
            result = mgr.dispatch_edit_flow(
                background_tasks=bt, orchestrator=orc,
                job_id="j1", edited_structured_data={}, template_name="ieee",
            )
        assert result == {"mode": "background", "task_id": None}
        bt.add_task.assert_called_once_with(
            orc.run_edit_flow,
            job_id="j1", edited_structured_data={}, template_name="ieee",
        )


class TestDispatchSynthesisPipeline:
    @pytest.fixture
    def mgr(self):
        from app.services.enhancement_manager import EnhancementManager
        m = EnhancementManager()
        m._profile = MagicMock(
            enabled=True, queue_enabled=True, queue_provider="celery", queue_available=True
        )
        return m

    def test_celery_path(self, mgr):
        bt = MagicMock()
        mock_task = MagicMock()
        mock_task.apply_async.return_value = MagicMock(id="syn-1")
        with patch("app.tasks.celery_tasks.process_synthesis_task", mock_task):
            result = mgr.dispatch_synthesis_pipeline(
                background_tasks=bt, run_pipeline=MagicMock(),
                session_id="s1", file_paths=["/a.pdf"], template="ieee",
            )
        assert result == {"mode": "celery", "task_id": "syn-1"}

    def test_background_fallback(self, mgr):
        bt = MagicMock()
        run_pipe = MagicMock()
        mock_task = MagicMock()
        mock_task.apply_async.side_effect = RuntimeError("celery down")
        with patch("app.tasks.celery_tasks.process_synthesis_task", mock_task):
            result = mgr.dispatch_synthesis_pipeline(
                background_tasks=bt, run_pipeline=run_pipe,
                session_id="s1", file_paths=["/a.pdf"], template="ieee",
            )
        assert result == {"mode": "background", "task_id": None}
        bt.add_task.assert_called_once_with(
            run_pipe, "s1", ["/a.pdf"], "ieee",
        )


class TestBuildProfile:
    @pytest.fixture
    def mgr(self):
        from app.services.enhancement_manager import EnhancementManager
        m = EnhancementManager()
        m._profile = None
        return m

    def test_default_profile(self, mgr):
        with patch("app.services.enhancement_manager.settings") as mock_s:
            mock_s.ENHANCEMENTS_ENABLED = True
            mock_s.ENHANCEMENT_QUEUE_ENABLED = False
            mock_s.ENHANCEMENT_QUEUE_PROVIDER = "auto"
            mock_s.ENHANCEMENT_OCR_ENABLED = True
            mock_s.ENHANCEMENT_OCR_BACKENDS = "tesseract"
            mock_s.ENHANCEMENT_KEYWORD_ENABLED = True
            mock_s.ENHANCEMENT_KEYWORD_BACKENDS = "basic"
            with patch("app.services.enhancement_manager._module_available", return_value=True):
                p = mgr._build_profile()
            assert p.enabled is True
            assert p.ocr_enabled is True
            assert p.keyword_enabled is True

    def test_ocr_fallback_to_builtin(self, mgr):
        with patch("app.services.enhancement_manager.settings") as mock_s:
            mock_s.ENHANCEMENTS_ENABLED = True
            mock_s.ENHANCEMENT_QUEUE_ENABLED = False
            mock_s.ENHANCEMENT_QUEUE_PROVIDER = "local"
            mock_s.ENHANCEMENT_OCR_ENABLED = True
            mock_s.ENHANCEMENT_OCR_BACKENDS = "tesseract,paddle,surya"
            mock_s.ENHANCEMENT_KEYWORD_ENABLED = False
            mock_s.ENHANCEMENT_KEYWORD_BACKENDS = "basic"
            with patch("app.services.enhancement_manager._module_available", return_value=False):
                p = mgr._build_profile()
            assert p.ocr_backends == ["builtin"]

    def test_keyword_with_keyllm(self, mgr):
        with patch("app.services.enhancement_manager.settings") as mock_s:
            mock_s.ENHANCEMENTS_ENABLED = True
            mock_s.ENHANCEMENT_QUEUE_ENABLED = False
            mock_s.ENHANCEMENT_QUEUE_PROVIDER = "local"
            mock_s.ENHANCEMENT_OCR_ENABLED = False
            mock_s.ENHANCEMENT_OCR_BACKENDS = ""
            mock_s.ENHANCEMENT_KEYWORD_ENABLED = True
            mock_s.ENHANCEMENT_KEYWORD_BACKENDS = "keyllm,keybert,yake,basic"
            mock_s.NVIDIA_API_KEY = "nv_key"
            with patch("app.services.enhancement_manager._module_available", return_value=True):
                p = mgr._build_profile()
            assert "keyllm" in p.keyword_backends
            assert "basic" in p.keyword_backends
