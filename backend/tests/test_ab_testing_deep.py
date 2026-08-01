from __future__ import annotations
import pytest
from unittest.mock import patch, MagicMock


class TestABTestingFramework:
    @pytest.fixture
    def ab(self):
        from app.services.ab_testing import ABTestingFramework
        return ABTestingFramework()

    def test_init(self, ab):
        assert ab.test_results == []

    def test_compare_results_both_none(self, ab):
        result = ab._compare_results(None, None)
        assert result["both_succeeded"] is False
        assert result["latency_winner"] is None

    def test_compare_results_one_none(self, ab):
        result = ab._compare_results({"success": True, "latency": 1.0}, None)
        assert result["both_succeeded"] is False
        assert result["latency_winner"] is None

    def test_compare_results_both_succeed_nvidia_wins(self, ab):
        nv = {"success": True, "latency": 0.5}
        ds = {"success": True, "latency": 1.2}
        result = ab._compare_results(nv, ds)
        assert result["both_succeeded"] is True
        assert result["latency_winner"] == "NVIDIA"
        assert result["latency_difference"] == 0.7

    def test_compare_results_both_succeed_deepseek_wins(self, ab):
        nv = {"success": True, "latency": 2.0}
        ds = {"success": True, "latency": 0.8}
        result = ab._compare_results(nv, ds)
        assert result["both_succeeded"] is True
        assert result["latency_winner"] == "DeepSeek"

    def test_compare_results_nvidia_fails(self, ab):
        nv = {"success": False, "latency": 1.0}
        ds = {"success": True, "latency": 0.5}
        result = ab._compare_results(nv, ds)
        assert result["both_succeeded"] is False
        assert result["latency_winner"] is None

    def test_run_nvidia_test_success(self, ab):
        mock_nv = MagicMock()
        mock_nv.chat.return_value = "analysis result"
        blocks = [{"text": "Block A content here for testing"}] * 5
        result = ab._run_nvidia_test(mock_nv, blocks, "ieee")
        assert result["success"] is True
        assert result["model"] == "NVIDIA Llama 3.3 70B"
        assert "latency" in result
        mock_nv.chat.assert_called_once()

    def test_run_nvidia_test_failure(self, ab):
        mock_nv = MagicMock()
        mock_nv.chat.side_effect = Exception("NV failed")
        result = ab._run_nvidia_test(mock_nv, [{"text": "test"}], "ieee")
        assert result["success"] is False
        assert "NV failed" in result["error"]

    def test_run_deepseek_test_success(self, ab):
        mock_ds = MagicMock()
        mock_ds.invoke.return_value = MagicMock(content="classification result")
        blocks = [{"text": "Block content for analysis"}] * 3
        result = ab._run_deepseek_test(mock_ds, blocks, "acm")
        assert result["success"] is True
        assert result["model"] == "DeepSeek"

    def test_run_deepseek_test_failure(self, ab):
        mock_ds = MagicMock()
        mock_ds.invoke.side_effect = Exception("DS failed")
        result = ab._run_deepseek_test(mock_ds, [{"text": "test"}], "acm")
        assert result["success"] is False
        assert "DS failed" in result["error"]

    def test_get_test_summary_no_tests(self, ab):
        result = ab.get_test_summary()
        assert result["message"] == "No tests run yet"

    def test_get_test_summary_with_results(self, ab):
        ab.test_results = [
            {"comparison": {"latency_winner": "NVIDIA"}},
            {"comparison": {"latency_winner": "NVIDIA"}},
            {"comparison": {"latency_winner": "DeepSeek"}},
        ]
        result = ab.get_test_summary()
        assert result["total_tests"] == 3
        assert result["nvidia_wins"] == 2
        assert result["deepseek_wins"] == 1
        assert result["nvidia_win_rate"] == 2.0 / 3.0

    def test_get_test_summary_exception(self, ab):
        mock_result = MagicMock()
        mock_result.get.side_effect = Exception("fail")
        ab.test_results = [mock_result]
        result = ab.get_test_summary()
        assert "error" in result

    def test_get_ab_testing(self):
        from app.services.ab_testing import get_ab_testing, _ab_testing
        _ab_testing = None
        with patch("app.services.ab_testing.get_or_create") as mock_gc:
            mock_gc.return_value = "ab_instance"
            result = get_ab_testing()
        assert result == "ab_instance"

    def test_run_ab_test_both_providers(self, ab):
        mock_nv = MagicMock()
        mock_ds = MagicMock()
        mock_nv.chat.return_value = "nv analysis"
        mock_ds.invoke.return_value = MagicMock(content="ds analysis")
        blocks = [{"text": "Block zero text for classification"}] * 7
        with patch.object(ab, "_run_nvidia_test", return_value={"response": "nv", "latency": 0.3, "success": True}):
            with patch.object(ab, "_run_deepseek_test", return_value={"response": "ds", "latency": 0.5, "success": True}):
                with patch.object(ab, "_compare_results", return_value={"both_succeeded": True, "latency_winner": "NVIDIA"}):
                    result = ab.run_ab_test(mock_nv, mock_ds, blocks, "ieee")
        assert result["nvidia"] is not None
        assert result["deepseek"] is not None
        assert result["comparison"]["latency_winner"] == "NVIDIA"

    def test_run_ab_test_nvidia_only(self, ab):
        mock_nv = MagicMock()
        blocks = [{"text": "test"}]
        with patch.object(ab, "_run_nvidia_test", return_value={"success": True}):
            with patch.object(ab, "_compare_results", return_value={}):
                result = ab.run_ab_test(mock_nv, None, blocks, "ieee")
        assert result["nvidia"] is not None
        assert result["deepseek"] is None

    def test_run_ab_test_deepseek_only(self, ab):
        mock_ds = MagicMock()
        blocks = [{"text": "test"}]
        with patch.object(ab, "_run_deepseek_test", return_value={"success": True}):
            with patch.object(ab, "_compare_results", return_value={}):
                result = ab.run_ab_test(None, mock_ds, blocks, "ieee")
        assert result["nvidia"] is None
        assert result["deepseek"] is not None

    def test_run_ab_test_future_failure(self, ab):
        mock_nv = MagicMock()
        mock_ds = MagicMock()
        blocks = [{"text": "test"}]
        with patch.object(ab, "_run_nvidia_test", side_effect=Exception("future error")):
            with patch.object(ab, "_run_deepseek_test", return_value={"success": True}):
                with patch.object(ab, "_compare_results", return_value={}):
                    result = ab.run_ab_test(mock_nv, mock_ds, blocks, "ieee")
        assert result["nvidia"]["success"] is False
        assert "future error" in result["nvidia"]["error"]

    def test_run_ab_test_persist_success(self, ab):
        mock_nv = MagicMock()
        mock_ds = MagicMock()
        mock_sb = MagicMock()
        blocks = [{"text": "test"}]
        captured_target = []
        import threading as _tmod
        orig_start = _tmod.Thread.start
        def capture_and_start(self_):
            captured_target.append(self_._target)
            return orig_start(self_)
        with patch.object(ab, "_run_nvidia_test", return_value={"latency": 0.3, "success": True}):
            with patch.object(ab, "_run_deepseek_test", return_value={"latency": 0.5, "success": True}):
                with patch.object(ab, "_compare_results", return_value={
                    "both_succeeded": True, "latency_winner": "NVIDIA"
                }):
                    with patch("app.db.supabase_client.get_supabase_client", return_value=mock_sb):
                        with patch.object(_tmod.Thread, "start", capture_and_start):
                            ab.run_ab_test(mock_nv, mock_ds, blocks, "ieee")
        for fn in captured_target:
            if fn and "persist" in getattr(fn, "__name__", ""):
                fn()
        mock_sb.table.assert_called_with("ab_test_results")

    def test_run_ab_test_persist_failure_logged(self, ab):
        import threading as _tmod
        mock_nv = MagicMock()
        mock_ds = MagicMock()
        mock_sb = MagicMock()
        mock_sb.table.side_effect = Exception("persist failed")
        blocks = [{"text": "test"}]
        captured_target = []
        orig_start = _tmod.Thread.start
        def capture_and_start(self_):
            captured_target.append(self_._target)
            return orig_start(self_)
        with patch.object(ab, "_run_nvidia_test", return_value={"latency": 0.3, "success": True}):
            with patch.object(ab, "_run_deepseek_test", return_value={"latency": 0.5, "success": True}):
                with patch.object(ab, "_compare_results", return_value={
                    "both_succeeded": True, "latency_winner": "NVIDIA"
                }):
                    with patch("app.db.supabase_client.get_supabase_client", return_value=mock_sb):
                        with patch.object(_tmod.Thread, "start", capture_and_start):
                            with patch("app.services.ab_testing.logger") as mock_log:
                                ab.run_ab_test(mock_nv, mock_ds, blocks, "ieee")
        for fn in captured_target:
            if fn and "persist" in getattr(fn, "__name__", ""):
                fn()
        assert any(
            "Failed to persist" in str(c) and "persist failed" in str(c)
            for c in mock_log.warning.call_args_list
        ), "Expected warning about persist failure"

    def test_run_ab_test_persist_sb_none_returns(self, ab):
        import threading as _tmod
        mock_nv = MagicMock()
        mock_ds = MagicMock()
        blocks = [{"text": "test"}]
        persist_fn = []
        orig_start = _tmod.Thread.start
        def capture_and_start(self_):
            fn = self_._target
            if fn and "persist" in getattr(fn, "__name__", ""):
                persist_fn.append(fn)
            return orig_start(self_)
        with patch.object(ab, "_run_nvidia_test", return_value={"latency": 0.3, "success": True}):
            with patch.object(ab, "_run_deepseek_test", return_value={"latency": 0.5, "success": True}):
                with patch.object(ab, "_compare_results", return_value={
                    "both_succeeded": True, "latency_winner": "NVIDIA"
                }):
                    with patch("app.db.supabase_client.get_supabase_client", return_value=None):
                        with patch.object(_tmod.Thread, "start", capture_and_start):
                            ab.run_ab_test(mock_nv, mock_ds, blocks, "ieee")
                            for fn in persist_fn:
                                fn()

    def test_run_ab_test_outer_exception(self, ab):
        with patch.object(ab, "_compare_results", side_effect=Exception("outer error")):
            result = ab.run_ab_test(None, None, [], "ieee")
        assert "error" in result
