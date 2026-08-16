from unittest.mock import MagicMock, patch

import pytest


class TestRunABTest:
    @pytest.fixture
    def framework(self):
        from app.services.ab_testing import ABTestingFramework

        return ABTestingFramework()

    def test_compare_results_both_successful(self, framework):
        nvidia_res = {"success": True, "latency": 0.5}
        deepseek_res = {"success": True, "latency": 1.0}
        cmp = framework._compare_results(nvidia_res, deepseek_res)
        assert cmp["both_succeeded"] is True
        assert cmp["latency_winner"] == "NVIDIA"

    def test_compare_results_deepseek_wins(self, framework):
        nvidia_res = {"success": True, "latency": 2.0}
        deepseek_res = {"success": True, "latency": 0.3}
        cmp = framework._compare_results(nvidia_res, deepseek_res)
        assert cmp["latency_winner"] == "DeepSeek"

    def test_compare_results_none_fallback(self, framework):
        cmp = framework._compare_results(None, {"success": True, "latency": 0.5})
        assert cmp["both_succeeded"] is False
        assert cmp["latency_winner"] is None

    def test_run_nvidia_success(self, framework):
        client = MagicMock()
        client.chat.return_value = '{"classification": "introduction"}'
        result = framework._run_nvidia_test(client, [{"text": "Hello"}], "rules")
        assert result["success"] is True
        assert result["model"] == "NVIDIA Llama 3.3 70B"

    def test_run_nvidia_failure(self, framework):
        client = MagicMock()
        client.chat.side_effect = RuntimeError("API error")
        result = framework._run_nvidia_test(client, [{"text": "Hello"}], "rules")
        assert result["success"] is False
        assert "error" in result

    def test_run_deepseek_success(self, framework):
        llm = MagicMock()
        llm.invoke.return_value = MagicMock(content='{"classification": "methods"}')
        result = framework._run_deepseek_test(llm, [{"text": "Hello"}], "rules")
        assert result["success"] is True

    def test_run_deepseek_failure(self, framework):
        llm = MagicMock()
        llm.invoke.side_effect = RuntimeError("LLM error")
        result = framework._run_deepseek_test(llm, [{"text": "Hello"}], "rules")
        assert result["success"] is False

    def test_get_test_summary_no_tests(self, framework):
        summary = framework.get_test_summary()
        assert summary == {"message": "No tests run yet"}

    def test_get_test_summary_with_results(self, framework):
        framework.test_results = [
            {"comparison": {"latency_winner": "NVIDIA"}},
            {"comparison": {"latency_winner": "DeepSeek"}},
        ]
        summary = framework.get_test_summary()
        assert summary["nvidia_wins"] == 1
        assert summary["deepseek_wins"] == 1

    def test_compare_results_both_none(self, framework):
        cmp = framework._compare_results(None, None)
        assert cmp["both_succeeded"] is False
        assert cmp["latency_winner"] is None

    def test_compare_results_only_one_success(self, framework):
        nvidia_res = {"success": True, "latency": 0.5}
        deepseek_res = {"success": False, "latency": 2.0, "error": "crashed"}
        cmp = framework._compare_results(nvidia_res, deepseek_res)
        assert cmp["both_succeeded"] is False
        assert cmp["latency_winner"] is None

    def test_run_ab_test_both_models(self, framework):
        nvidia = MagicMock()
        nvidia.chat.return_value = '{"cls": "intro"}'
        deepseek = MagicMock()
        deepseek.invoke.return_value = MagicMock(content='{"cls": "intro"}')
        result = framework.run_ab_test(nvidia, deepseek, [{"text": "Hello"}], "rules")
        assert result["nvidia"] is not None
        assert result["deepseek"] is not None
        assert "comparison" in result

    def test_run_ab_test_nvidia_only(self, framework):
        nvidia = MagicMock()
        nvidia.chat.return_value = "ok"
        result = framework.run_ab_test(nvidia, None, [{"text": "Hello"}], "rules")
        assert result["nvidia"] is not None
        assert result["deepseek"] is None

    def test_run_ab_test_deepseek_only(self, framework):
        deepseek = MagicMock()
        deepseek.invoke.return_value = MagicMock(content="ok")
        result = framework.run_ab_test(None, deepseek, [{"text": "Hello"}], "rules")
        assert result["nvidia"] is None
        assert result["deepseek"] is not None

    def test_run_ab_test_persist_failure_logged(self, framework):
        nvidia = MagicMock()
        nvidia.chat.return_value = "ok"
        deepseek = MagicMock()
        deepseek.invoke.return_value = MagicMock(content="ok")
        with patch("app.db.supabase_client.get_supabase_client", return_value=MagicMock()):
            result = framework.run_ab_test(nvidia, deepseek, [{"text": "Hello"}], "rules")
        assert result["nvidia"]["success"] is True

    def test_get_test_summary_exception_returns_error(self, framework):
        framework.test_results = [None]
        with patch("app.services.ab_testing.logger"):
            result = framework.get_test_summary()
        assert "error" in result


class TestGetABTesting:
    def test_returns_singleton(self):
        from app.services.ab_testing import get_ab_testing

        a1 = get_ab_testing()
        a2 = get_ab_testing()
        assert a1 is a2
