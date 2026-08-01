from __future__ import annotations
from unittest.mock import patch, MagicMock


class TestNvidiaClientInitBranches:
    """Cover remaining __init__ branches without module reload."""

    def test_init_openai_init_success(self):
        with patch("app.services.nvidia_client.os.getenv", return_value="key"):
            with patch("app.services.nvidia_client.LITELLM_AVAILABLE", False):
                with patch("app.services.nvidia_client._USE_LLM_SERVICE", False):
                    with patch("app.services.nvidia_client._OPENAI_AVAILABLE", True):
                        mock_openai = MagicMock()
                        with patch("app.services.nvidia_client._OpenAI", return_value=mock_openai):
                            with patch("app.services.nvidia_client.logger") as mock_log:
                                from app.services.nvidia_client import NvidiaClient
                                client = NvidiaClient()
        assert client.client is not None
        mock_log.info.assert_any_call(
            "NvidiaClient: direct OpenAI client initialized (litellm not available)."
        )

    def test_init_openai_init_failure(self):
        with patch("app.services.nvidia_client.os.getenv", return_value="key"):
            with patch("app.services.nvidia_client.LITELLM_AVAILABLE", False):
                with patch("app.services.nvidia_client._USE_LLM_SERVICE", False):
                    with patch("app.services.nvidia_client._OPENAI_AVAILABLE", True):
                        with patch("app.services.nvidia_client._OpenAI", side_effect=Exception("fail")):
                            with patch("app.services.nvidia_client.logger") as mock_log:
                                from app.services.nvidia_client import NvidiaClient
                                client = NvidiaClient()
        assert client.client is None
        mock_log.error.assert_called_once()

    def test_init_no_openai_available(self):
        with patch("app.services.nvidia_client.os.getenv", return_value="key"):
            with patch("app.services.nvidia_client.LITELLM_AVAILABLE", False):
                with patch("app.services.nvidia_client._USE_LLM_SERVICE", False):
                    with patch("app.services.nvidia_client._OPENAI_AVAILABLE", False):
                        from app.services.nvidia_client import NvidiaClient
                        client = NvidiaClient()
        assert client.client is None

    def test_init_litellm_path_logs(self):
        with patch("app.services.nvidia_client.os.getenv", return_value="key"):
            with patch("app.services.nvidia_client.LITELLM_AVAILABLE", True):
                with patch("app.services.nvidia_client._USE_LLM_SERVICE", True):
                    with patch("app.services.nvidia_client.logger") as mock_log:
                        from app.services.nvidia_client import NvidiaClient
                        client = NvidiaClient()
        mock_log.info.assert_any_call("NvidiaClient: using LiteLLM for NVIDIA calls.")

    def test_init_settings_path(self):
        with patch("app.services.nvidia_client.os.getenv", side_effect=lambda k, d=None: None if k == "NVIDIA_API_KEY" else d):
            with patch("app.services.nvidia_client.settings.NVIDIA_API_KEY", "settings-val"):
                with patch("app.services.nvidia_client.LITELLM_AVAILABLE", False):
                    with patch("app.services.nvidia_client._OPENAI_AVAILABLE", False):
                        from app.services.nvidia_client import NvidiaClient
                        client = NvidiaClient()
        assert client.api_key == "settings-val"


class TestNvidiaClientAnalyzeFigureMediaTypes:
    """Cover media type detection branches."""

    def make_client(self):
        from app.services.nvidia_client import NvidiaClient
        client = NvidiaClient.__new__(NvidiaClient)
        client.api_key = "key"
        client.llama_70b = "meta/llama-3.3-70b-instruct"
        client.llama_vision = "meta/llama-3.2-11b-vision-instruct"
        return client

    def test_jpg(self):
        client = self.make_client()
        client.chat = MagicMock(return_value="jpg analysis")
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = b"data"
        with patch("builtins.open", return_value=mock_file), \
             patch("app.services.nvidia_client.base64.b64encode", return_value=b"f"):
            result = client.analyze_figure("/p/f.jpg", caption="test")
        assert result == "jpg analysis"

    def test_jpeg(self):
        client = self.make_client()
        client.chat = MagicMock(return_value="jpeg analysis")
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = b"data"
        with patch("builtins.open", return_value=mock_file), \
             patch("app.services.nvidia_client.base64.b64encode", return_value=b"f"):
            result = client.analyze_figure("/p/f.jpeg", caption="test")
        assert result == "jpeg analysis"

    def test_gif(self):
        client = self.make_client()
        client.chat = MagicMock(return_value="gif analysis")
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = b"data"
        with patch("builtins.open", return_value=mock_file), \
             patch("app.services.nvidia_client.base64.b64encode", return_value=b"f"):
            result = client.analyze_figure("/p/f.gif", caption="test")
        assert result == "gif analysis"

    def test_webp(self):
        client = self.make_client()
        client.chat = MagicMock(return_value="webp analysis")
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = b"data"
        with patch("builtins.open", return_value=mock_file), \
             patch("app.services.nvidia_client.base64.b64encode", return_value=b"f"):
            result = client.analyze_figure("/p/f.webp", caption="test")
        assert result == "webp analysis"

    def test_unknown_ext(self):
        client = self.make_client()
        client.chat = MagicMock(return_value="analysis")
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = b"data"
        with patch("builtins.open", return_value=mock_file), \
             patch("app.services.nvidia_client.base64.b64encode", return_value=b"f"):
            result = client.analyze_figure("/p/f.xyz", caption="test")
        assert result == "analysis"

    def test_no_caption_fallback(self):
        client = self.make_client()
        client.chat = MagicMock(side_effect=Exception("fail"))
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = b"data"
        with patch("builtins.open", return_value=mock_file):
            result = client.analyze_figure("/p/f.png")
        assert result == "Figure (AI analysis unavailable)"

    def test_large_palette_mode(self):
        client = self.make_client()
        client.chat = MagicMock(return_value="analysis")
        mock_img = MagicMock()
        mock_img.mode = "P"
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = b"x" * 3_000_000
        with patch("builtins.open", return_value=mock_file), \
             patch("PIL.Image.open", return_value=mock_img):
            result = client.analyze_figure("/p/f.jpeg", caption="large")
        assert result == "analysis"
        mock_img.convert.assert_called_once_with("RGB")


class TestNvidiaClientValidateTemplateComplianceBranches:
    def test_yes(self):
        from app.services.nvidia_client import NvidiaClient
        c = NvidiaClient.__new__(NvidiaClient)
        c.api_key = "k"; c.llama_70b = "m"; c.llama_vision = "m"
        c.chat = MagicMock(return_value="Yes, complies")
        assert c.validate_template_compliance("t", "a")["compliant"] is True

    def test_complies_lower(self):
        from app.services.nvidia_client import NvidiaClient
        c = NvidiaClient.__new__(NvidiaClient)
        c.api_key = "k"; c.llama_70b = "m"; c.llama_vision = "m"
        c.chat = MagicMock(return_value="this document complies with all")
        assert c.validate_template_compliance("t", "a")["compliant"] is True


class TestNvidiaClientGetClientDeep:
    def test_reuses_instance(self):
        from app.services.nvidia_client import get_nvidia_client, _nvidia_client
        _nvidia_client = None
        mock_instance = MagicMock()
        with patch("app.services.nvidia_client.NvidiaClient", return_value=mock_instance):
            c1 = get_nvidia_client()
        assert c1 is mock_instance
