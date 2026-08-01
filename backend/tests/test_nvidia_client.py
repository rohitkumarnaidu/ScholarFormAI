from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestNvidiaClient:
    def test_init_no_key(self):
        with patch("app.services.nvidia_client.os.getenv", return_value=None):
            with patch("app.services.nvidia_client.settings.NVIDIA_API_KEY", ""):
                from app.services.nvidia_client import NvidiaClient
                client = NvidiaClient()
                assert client.api_key == ""

    def test_init_with_key(self):
        with patch("app.services.nvidia_client.os.getenv", return_value="sk-test"):
            with patch("app.services.nvidia_client.LITELLM_AVAILABLE", False):
                with patch("app.services.nvidia_client._OPENAI_AVAILABLE", False):
                    from app.services.nvidia_client import NvidiaClient
                    client = NvidiaClient()
                    assert client.api_key == "sk-test"

    def test_chat_no_key_returns_empty(self):
        from app.services.nvidia_client import NvidiaClient
        client = NvidiaClient.__new__(NvidiaClient)
        client.api_key = ""
        client.llama_70b = "meta/llama-3.3-70b-instruct"
        client.llama_vision = "meta/llama-3.2-11b-vision-instruct"
        result = client.chat([{"role": "user", "content": "hi"}])
        assert result == ""

    def test_chat_direct_client_success(self):
        from app.services.nvidia_client import NvidiaClient
        client = NvidiaClient.__new__(NvidiaClient)
        client.api_key = "sk-test"
        client.llama_70b = "meta/llama-3.3-70b-instruct"
        client.llama_vision = "meta/llama-3.2-11b-vision-instruct"
        client.client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Hello response"
        client.client.chat.completions.create.return_value = MagicMock(choices=[mock_choice], usage=None)
        with patch("app.services.nvidia_client._USE_LLM_SERVICE", False):
            result = client.chat([{"role": "user", "content": "hi"}])
            assert result == "Hello response"

    def test_chat_direct_client_empty_choices(self):
        from app.services.nvidia_client import NvidiaClient
        client = NvidiaClient.__new__(NvidiaClient)
        client.api_key = "sk-test"
        client.llama_70b = "meta/llama-3.3-70b-instruct"
        client.llama_vision = "meta/llama-3.2-11b-vision-instruct"
        client.client = MagicMock()
        client.client.chat.completions.create.return_value = MagicMock(choices=[], usage=None)
        with patch("app.services.nvidia_client._USE_LLM_SERVICE", False):
            result = client.chat([{"role": "user", "content": "hi"}])
            assert result == ""

    def test_analyze_document_structure(self):
        from app.services.nvidia_client import NvidiaClient
        client = NvidiaClient.__new__(NvidiaClient)
        client.api_key = "sk-test"
        client.llama_70b = "meta/llama-3.3-70b-instruct"
        client.llama_vision = "meta/llama-3.2-11b-vision-instruct"
        client.chat = MagicMock(return_value="Abstract: ... Introduction: ... Methods: ...")
        result = client.analyze_document_structure("test doc")
        assert "analysis" in result
        assert result["confidence"] > 0

    def test_analyze_document_structure_empty_response(self):
        from app.services.nvidia_client import NvidiaClient
        client = NvidiaClient.__new__(NvidiaClient)
        client.api_key = "sk-test"
        client.llama_70b = "meta/llama-3.3-70b-instruct"
        client.llama_vision = "meta/llama-3.2-11b-vision-instruct"
        client.chat = MagicMock(return_value="")
        result = client.analyze_document_structure("test doc")
        assert result["confidence"] == 0.0

    def test_validate_template_compliance(self):
        from app.services.nvidia_client import NvidiaClient
        client = NvidiaClient.__new__(NvidiaClient)
        client.api_key = "sk-test"
        client.llama_70b = "meta/llama-3.3-70b-instruct"
        client.llama_vision = "meta/llama-3.2-11b-vision-instruct"
        client.chat = MagicMock(return_value="True - the document complies")
        result = client.validate_template_compliance("doc text", "ieee")
        assert result["compliant"] is True

    def test_validate_template_compliance_not_compliant(self):
        from app.services.nvidia_client import NvidiaClient
        client = NvidiaClient.__new__(NvidiaClient)
        client.api_key = "sk-test"
        client.llama_70b = "meta/llama-3.3-70b-instruct"
        client.llama_vision = "meta/llama-3.2-11b-vision-instruct"
        client.chat = MagicMock(return_value="The document does not comply with IEEE format")
        result = client.validate_template_compliance("doc text", "ieee")
        assert result["compliant"] is False

    def test_get_nvidia_client(self):
        from app.services.nvidia_client import get_nvidia_client
        with patch("app.services.nvidia_client.NvidiaClient") as mock_cls:
            mock_cls.return_value = MagicMock()
            client = get_nvidia_client()
            assert client is not None

    def test_chat_litellm_path(self):
        with patch("app.services.nvidia_client._USE_LLM_SERVICE", True):
            with patch("app.services.nvidia_client.LITELLM_AVAILABLE", True):
                with patch("app.services.nvidia_client._llm_generate", return_value="litellm ok"):
                    from app.services.nvidia_client import NvidiaClient
                    client = NvidiaClient.__new__(NvidiaClient)
                    client.api_key = "key"
                    client.llama_70b = "meta/llama-3.3-70b-instruct"
                    client.llama_vision = "meta/llama-3.2-11b-vision-instruct"
                    result = client.chat([{"role": "user", "content": "hi"}])
                    assert result == "litellm ok"

    def test_chat_litellm_fallback_to_direct(self):
        with patch("app.services.nvidia_client._USE_LLM_SERVICE", True):
            with patch("app.services.nvidia_client.LITELLM_AVAILABLE", True):
                with patch("app.services.nvidia_client._llm_generate", side_effect=Exception("fail")):
                    from app.services.nvidia_client import NvidiaClient
                    client = NvidiaClient.__new__(NvidiaClient)
                    client.api_key = "key"
                    client.llama_70b = "meta/llama-3.3-70b-instruct"
                    client.llama_vision = "meta/llama-3.2-11b-vision-instruct"
                    client.client = MagicMock()
                    mock_choice = MagicMock()
                    mock_choice.message.content = "fallback ok"
                    client.client.chat.completions.create.return_value = MagicMock(choices=[mock_choice], usage=None)
                    result = client.chat([{"role": "user", "content": "hi"}])
                    assert result == "fallback ok"

    def test_chat_no_client_available(self):
        from app.services.nvidia_client import NvidiaClient
        client = NvidiaClient.__new__(NvidiaClient)
        client.api_key = "key"
        client.llama_70b = "meta/llama-3.3-70b-instruct"
        client.llama_vision = "meta/llama-3.2-11b-vision-instruct"
        client.client = None
        with patch("app.services.nvidia_client._USE_LLM_SERVICE", False):
            result = client.chat([{"role": "user", "content": "hi"}])
            assert result == ""

    def test_chat_direct_client_raises(self):
        from app.services.nvidia_client import NvidiaClient
        client = NvidiaClient.__new__(NvidiaClient)
        client.api_key = "key"
        client.llama_70b = "meta/llama-3.3-70b-instruct"
        client.llama_vision = "meta/llama-3.2-11b-vision-instruct"
        client.client = MagicMock()
        client.client.chat.completions.create.side_effect = Exception("api fail")
        with patch("app.services.nvidia_client._USE_LLM_SERVICE", False), pytest.raises(Exception):
            client.chat([{"role": "user", "content": "hi"}])

    def test_validate_compliance_ambiguous(self):
        from app.services.nvidia_client import NvidiaClient
        client = NvidiaClient.__new__(NvidiaClient)
        client.api_key = "sk-test"
        client.llama_70b = "meta/llama-3.3-70b-instruct"
        client.llama_vision = "meta/llama-3.2-11b-vision-instruct"
        client.chat = MagicMock(return_value="I'm not sure about compliance.")
        result = client.validate_template_compliance("doc text", "ieee")
        assert result["compliant"] is False

    def test_chat_clamps_temperature(self):
        from app.services.nvidia_client import NvidiaClient
        client = NvidiaClient.__new__(NvidiaClient)
        client.api_key = "key"
        client.llama_70b = "meta/llama-3.3-70b-instruct"
        client.llama_vision = "meta/llama-3.2-11b-vision-instruct"
        client.client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "ok"
        client.client.chat.completions.create.return_value = MagicMock(choices=[mock_choice], usage=None)
        with patch("app.services.nvidia_client._USE_LLM_SERVICE", False):
            client.chat([{"role": "user", "content": "hi"}], temperature=1.5)
            call_kwargs = client.client.chat.completions.create.call_args[1]
            assert call_kwargs["temperature"] == 1.0

    def test_chat_with_usage_logging(self):
        from app.services.nvidia_client import NvidiaClient
        client = NvidiaClient.__new__(NvidiaClient)
        client.api_key = "key"
        client.llama_70b = "meta/llama-3.3-70b-instruct"
        client.llama_vision = "meta/llama-3.2-11b-vision-instruct"
        client.client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "response"
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 50
        mock_usage.completion_tokens = 100
        mock_usage.total_tokens = 150
        client.client.chat.completions.create.return_value = MagicMock(choices=[mock_choice], usage=mock_usage)
        with patch("app.services.nvidia_client._USE_LLM_SERVICE", False):
            result = client.chat([{"role": "user", "content": "hi"}])
        assert result == "response"

    def test_chat_vision_model(self):
        from app.services.nvidia_client import NvidiaClient
        client = NvidiaClient.__new__(NvidiaClient)
        client.api_key = "key"
        client.llama_70b = "meta/llama-3.3-70b-instruct"
        client.llama_vision = "meta/llama-3.2-11b-vision-instruct"
        client.client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "vision analysis"
        client.client.chat.completions.create.return_value = MagicMock(choices=[mock_choice], usage=None)
        with patch("app.services.nvidia_client._USE_LLM_SERVICE", False):
            result = client.chat([{"role": "user", "content": "desc"}], model="llama-vision")
        assert result == "vision analysis"

    def test_analyze_figure_success(self):
        from app.services.nvidia_client import NvidiaClient
        client = NvidiaClient.__new__(NvidiaClient)
        client.chat = MagicMock(return_value="figure shows a sigmoid curve")
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = b"small_image_bytes"
        with patch("builtins.open", return_value=mock_file):
            with patch("app.services.nvidia_client.base64.b64encode", return_value=b"fakebase64"):
                result = client.analyze_figure("/fake/path.png", caption="Test figure")
        assert result == "figure shows a sigmoid curve"

    def test_analyze_figure_empty_response_uses_caption(self):
        from app.services.nvidia_client import NvidiaClient
        client = NvidiaClient.__new__(NvidiaClient)
        client.chat = MagicMock(return_value="")
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = b"small_image_bytes"
        with patch("builtins.open", return_value=mock_file):
            with patch("app.services.nvidia_client.base64.b64encode", return_value=b"fakebase64"):
                result = client.analyze_figure("/fake/path.png", caption="Fallback caption")
        assert result == "Fallback caption"

    def test_analyze_figure_exception_returns_caption(self):
        from app.services.nvidia_client import NvidiaClient
        client = NvidiaClient.__new__(NvidiaClient)
        client.chat = MagicMock(side_effect=Exception("vision fail"))
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = b"data"
        with patch("builtins.open", return_value=mock_file):
            result = client.analyze_figure("/fake/path.png", caption="Fallback")
        assert result == "Fallback"

    def test_analyze_figure_no_caption(self):
        from app.services.nvidia_client import NvidiaClient
        client = NvidiaClient.__new__(NvidiaClient)
        client.chat = MagicMock(side_effect=Exception("vision fail"))
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = b"data"
        with patch("builtins.open", return_value=mock_file):
            result = client.analyze_figure("/fake/path.png")
        assert result == "Figure (AI analysis unavailable)"

    def test_analyze_figure_image_too_large(self):
        from app.services.nvidia_client import NvidiaClient
        client = NvidiaClient.__new__(NvidiaClient)
        client.chat = MagicMock(return_value="analysis")
        mock_img = MagicMock()
        mock_img.mode = "RGB"
        mock_bytes = b"x" * 3_000_000  # > 2MB
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = mock_bytes
        with patch("builtins.open", return_value=mock_file), patch("PIL.Image.open", return_value=mock_img):
            result = client.analyze_figure("/fake/path.jpeg", caption="Large figure")
        assert result == "analysis"

    def test_analyze_figure_rgba_to_rgb(self):
        from app.services.nvidia_client import NvidiaClient
        client = NvidiaClient.__new__(NvidiaClient)
        client.chat = MagicMock(return_value="analysis")
        mock_img = MagicMock()
        mock_img.mode = "RGBA"
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = b"x" * 3_000_000
        with patch("builtins.open", return_value=mock_file), patch("PIL.Image.open", return_value=mock_img):
            result = client.analyze_figure("/fake/path.jpeg", caption="RGBA test")
        assert result == "analysis"
        mock_img.convert.assert_called_once_with("RGB")

    def test_chat_direct_with_vision_model_removes_nvidia_prefix(self):
        from app.services.nvidia_client import NvidiaClient
        client = NvidiaClient.__new__(NvidiaClient)
        client.api_key = "key"
        client.llama_70b = "meta/llama-3.3-70b-instruct"
        client.llama_vision = "meta/llama-3.2-11b-vision-instruct"
        client.client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "done"
        client.client.chat.completions.create.return_value = MagicMock(choices=[mock_choice], usage=None)
        with patch("app.services.nvidia_client._USE_LLM_SERVICE", False):
            client.chat([{"role": "user", "content": "hi"}], model="llama-vision")
            call_args = client.client.chat.completions.create.call_args[1]
            assert call_args["model"] == "meta/llama-3.2-11b-vision-instruct"
