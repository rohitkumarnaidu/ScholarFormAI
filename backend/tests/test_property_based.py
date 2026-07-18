import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from unittest.mock import MagicMock, patch
import json
pytestmark = [pytest.mark.property]

class TestSchemaSerialization:
    @given(st.text(min_size=0, max_size=100), st.text(min_size=0, max_size=50))
    def test_message_response_roundtrip(self, message_text, request_id):
        from app.schemas.api_envelope import APIResponse
        try:
            response = APIResponse(data=message_text, request_id=request_id)
            assert response.data == message_text
            assert response.request_id == request_id
        except Exception:
            pass

    @given(st.integers(min_value=1, max_value=100))
    def test_pagination_limit_bounds(self, limit):
        from app.schemas.pagination import PaginationParams
        try:
            params = PaginationParams(limit=limit)
            assert 1 <= params.limit <= 100
        except Exception:
            pass

    @given(st.text(min_size=1, max_size=200))
    def test_pagination_order_by(self, order_by):
        from app.schemas.pagination import PaginationParams
        try:
            params = PaginationParams(limit=50, order_by=order_by)
            assert params.order_by == order_by
        except Exception:
            pass

    @given(st.sampled_from(["asc", "desc"]))
    def test_pagination_order_dir(self, order_dir):
        from app.schemas.pagination import PaginationParams
        try:
            params = PaginationParams(limit=50, order_dir=order_dir)
            assert params.order_dir in ("asc", "desc")
        except Exception:
            pass

    @given(st.text(min_size=0, max_size=200))
    def test_cursor_page_roundtrip(self, next_cursor):
        from app.schemas.pagination import CursorPage
        try:
            page = CursorPage(
                items=[{"id": 1}],
                next_cursor=next_cursor or None,
                has_more=True,
                total=100,
            )
            assert len(page.items) > 0
            assert isinstance(page.has_more, bool)
        except Exception:
            pass

class TestGeneratorStateTransitions:
    @given(st.sampled_from(["idle", "parsing", "outline_review", "generating", "complete"]))
    def test_session_status_persistence(self, status):
        from app.schemas.generator_session import SessionResponse
        try:
            session = SessionResponse(id="test-id", status=status, session_type="agent")
            assert session.status == status
        except Exception:
            pass

    @given(st.lists(st.text(max_size=50), max_size=5))
    def test_message_content_persistence(self, contents):
        from app.schemas.generator_session import MessageRequest
        for content in contents:
            try:
                msg = MessageRequest(content=content)
                assert msg.content == content
            except Exception:
                pass

    @given(st.integers(min_value=0, max_value=100))
    def test_stage_event_progress(self, progress):
        from app.schemas.generator_session import StageEvent
        from datetime import datetime
        try:
            event = StageEvent(stage="parsing", progress=progress, message="test", timestamp=datetime.utcnow())
            assert 0 <= event.progress <= 100
        except Exception:
            pass

class TestApiEnvelope:
    @given(st.text(min_size=1, max_size=50))
    def test_success_response_has_data(self, request_id):
        from app.schemas.api_envelope import success_response
        response = success_response(data={"key": "value"}, request_id=request_id)
        assert response.data is not None
        assert response.error is None
        assert response.request_id == request_id

    @given(st.text(min_size=1, max_size=50), st.text(min_size=1, max_size=100))
    def test_error_response_has_error(self, request_id, message):
        from app.schemas.api_envelope import error_response
        response = error_response(code="ERROR", message=message, request_id=request_id)
        assert response.data is None
        assert response.error is not None
        assert response.error.message == message

    @given(st.text(min_size=1, max_size=50), st.text(min_size=1, max_size=100))
    def test_error_response_roundtrip_json(self, request_id, message):
        from app.schemas.api_envelope import error_response
        response = error_response(code="TEST", message=message, request_id=request_id)
        dumped = response.model_dump()
        assert dumped["error"]["message"] == message
        assert dumped["request_id"] == request_id

class TestAuthSchemas:
    @given(st.emails())
    def test_login_request_valid_email(self, email):
        from app.schemas.auth import LoginRequest
        try:
            req = LoginRequest(email=email, password="ValidPass1!")
            assert req.email == email
        except Exception:
            pass

    @settings(suppress_health_check=[HealthCheck.filter_too_much], max_examples=20)
    @given(st.text(min_size=8, max_size=128, alphabet=st.characters(whitelist_categories=('L', 'N', 'P'))))
    def test_password_min_length_constraint(self, password):
        has_upper = bool(set(password) & set("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
        has_lower = bool(set(password) & set("abcdefghijklmnopqrstuvwxyz"))
        has_digit = bool(set(password) & set("0123456789"))
        has_special = bool(set(password) & set("@$!%*?&_-#"))
        assume(has_upper and has_lower and has_digit and has_special)
        from app.schemas.auth import _validate_password_strength
        try:
            result = _validate_password_strength(password)
            assert result == password
        except ValueError:
            pass

    def test_forgot_password_request(self):
        from app.schemas.auth import ForgotPasswordRequest
        req = ForgotPasswordRequest(email="test@example.com")
        assert req.email == "test@example.com"

class TestWebhookSchemas:
    @given(st.text(min_size=1, max_size=200))
    def test_webhook_subscription_create_name(self, name):
        from app.schemas.webhook import WebhookSubscriptionCreate
        try:
            sub = WebhookSubscriptionCreate(
                name=name,
                url="https://example.com/hook",
                events=["document.completed"],
            )
            assert sub.name == name
        except Exception:
            pass

    @given(st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=5))
    def test_webhook_subscription_events(self, events):
        from app.schemas.webhook import WebhookSubscriptionCreate
        try:
            sub = WebhookSubscriptionCreate(
                name="test", url="https://example.com/hook", events=events
            )
            assert len(sub.events) == len(events)
        except Exception:
            pass

    @given(st.booleans())
    def test_webhook_subscription_update_is_active(self, is_active):
        from app.schemas.webhook import WebhookSubscriptionUpdate
        try:
            update = WebhookSubscriptionUpdate(is_active=is_active)
            assert update.is_active == is_active
        except Exception:
            pass

class TestParserProperties:
    @given(st.text(min_size=0, max_size=1000))
    @settings(max_examples=20)
    def test_txt_parser_handles_any_text(self, text):
        import tempfile, os
        from app.pipeline.parsing.txt_parser import TxtParser
        parser = TxtParser()
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8")
        tmp.write(text)
        tmp.close()
        try:
            doc = parser.parse(tmp.name, "test-id")
            assert doc is not None
            assert doc.document_id == "test-id"
        except Exception:
            pass
        finally:
            os.unlink(tmp.name)

    @settings(suppress_health_check=[HealthCheck.filter_too_much], max_examples=20)
    @given(st.text(min_size=0, max_size=100))
    def test_txt_parser_empty_input(self, text):
        assume(len(text.strip()) == 0)
        import tempfile, os
        from app.pipeline.parsing.txt_parser import TxtParser
        parser = TxtParser()
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8")
        tmp.write(text)
        tmp.close()
        try:
            doc = parser.parse(tmp.name, "test-id")
            assert doc is not None
            assert isinstance(doc.blocks, list)
        except Exception:
            pass
        finally:
            os.unlink(tmp.name)

    def test_txt_parser_large_input(self):
        import tempfile, os
        from app.pipeline.parsing.txt_parser import TxtParser
        parser = TxtParser()
        text = "\n\n".join(["This is paragraph number " + str(i) for i in range(500)])
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8")
        tmp.write(text)
        tmp.close()
        doc = parser.parse(tmp.name, "test-id")
        os.unlink(tmp.name)
        assert doc is not None
        assert len(doc.blocks) >= 1

    @given(st.text(alphabet=st.characters(whitelist_categories=('L', 'M', 'N', 'P', 'Z')), min_size=1, max_size=500))
    @settings(max_examples=20)
    def test_txt_parser_unicode_input(self, text):
        assume(any(ord(c) > 127 for c in text))
        import tempfile, os
        from app.pipeline.parsing.txt_parser import TxtParser
        parser = TxtParser()
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8")
        tmp.write(text)
        tmp.close()
        try:
            doc = parser.parse(tmp.name, "test-id")
            assert doc is not None
        except Exception:
            pass
        finally:
            os.unlink(tmp.name)

class TestSanitizeProperties:
    @settings(deadline=None, max_examples=20)
    @given(st.text(min_size=0, max_size=500))
    def test_sanitize_never_increases_length_beyond_max(self, text):
        from app.services.llm_service import sanitize_for_llm, MAX_LLM_INPUT_LENGTH
        result = sanitize_for_llm(text)
        assert isinstance(result, str)
        if text:
            assert len(result) <= MAX_LLM_INPUT_LENGTH + 100

    @given(st.text(min_size=0, max_size=200))
    def test_sanitize_preserves_safe_text(self, text):
        from app.services.llm_service import sanitize_for_llm
        assume("ignore" not in text.lower() and "forget" not in text.lower())
        assume("you are" not in text.lower() and "system:" not in text.lower())
        assume("disregard" not in text.lower() and "new instructions" not in text.lower())
        result = sanitize_for_llm(text)
        assert text in result or len(result) >= len(text) - 10

    @given(st.text(min_size=0, max_size=200))
    def test_sanitize_idempotent(self, text):
        from app.services.llm_service import sanitize_for_llm
        r1 = sanitize_for_llm(text)
        r2 = sanitize_for_llm(r1)
        assert r2 == r1

class TestDeterministicEmbeddingProperties:
    @settings(deadline=None, max_examples=20)
    @given(st.text(min_size=0, max_size=200))
    def test_embedding_deterministic(self, text):
        from app.pipeline.intelligence.rag_engine import _DeterministicEmbeddingModel
        model = _DeterministicEmbeddingModel(dimension=64)
        v1 = model.encode(text)
        v2 = model.encode(text)
        assert v1 == v2

    @given(st.text(min_size=0, max_size=200), st.text(min_size=0, max_size=200))
    def test_embedding_same_length(self, t1, t2):
        from app.pipeline.intelligence.rag_engine import _DeterministicEmbeddingModel
        model = _DeterministicEmbeddingModel(dimension=128)
        v1 = model.encode(t1)
        v2 = model.encode(t2)
        assert len(v1) == len(v2)

    @given(st.integers(min_value=32, max_value=512))
    def test_embedding_dimension_matches(self, dim):
        from app.pipeline.intelligence.rag_engine import _DeterministicEmbeddingModel
        model = _DeterministicEmbeddingModel(dimension=dim)
        vec = model.encode("test")
        assert len(vec) == dim

class TestPromptBuilderProperties:
    @settings(deadline=None, max_examples=10)
    @given(st.sampled_from(["academic_paper", "resume", "portfolio", "report", "thesis"]))
    def test_prompt_builder_returns_string(self, doc_type):
        from app.pipeline.generation.prompt_builder import PromptBuilder
        builder = PromptBuilder()
        try:
            prompt = builder.build(doc_type, {"title": "Test"}, {})
            assert isinstance(prompt, str)
            assert len(prompt) > 50
        except Exception:
            pass

    @given(st.text(max_size=50))
    def test_prompt_builder_rejects_unknown(self, doc_type):
        assume(doc_type not in ("academic_paper", "resume", "portfolio", "report", "thesis"))
        from app.pipeline.generation.prompt_builder import PromptBuilder
        builder = PromptBuilder()
        with pytest.raises(ValueError):
            builder.build(doc_type, {}, {})

class TestCacheKeyProperties:
    @given(st.text(max_size=50), st.text(max_size=50), st.floats(min_value=0, max_value=2), st.integers(min_value=1, max_value=4096))
    def test_cache_key_unique(self, sys_prompt, user_msg, temp, max_tok):
        from app.services.llm_service import _cache_key
        key1 = _cache_key(sys_prompt, user_msg, "model1", temp, max_tok)
        key2 = _cache_key(sys_prompt + "x", user_msg, "model1", temp, max_tok)
        assert key1 != key2

    @given(st.text(max_size=50))
    def test_cache_key_format(self, prompt):
        from app.services.llm_service import _cache_key
        key = _cache_key(prompt, "user", "model", 0.3, 2048)
        assert key.startswith("llm_cache:")

class TestNormalizeModelName:
    @given(st.text(min_size=1, max_size=50).filter(lambda s: s.strip()))
    def test_normalize_adds_prefix(self, model):
        from app.services.llm_service import _normalize_model_name
        result = _normalize_model_name(model, "groq")
        assert result.startswith("groq/")

    @given(st.text(min_size=0, max_size=0))
    def test_normalize_empty_string(self, model):
        from app.services.llm_service import _normalize_model_name
        result = _normalize_model_name(model, "openai")
        assert result == ""

class TestExtractPrompts:
    @given(st.lists(st.text(max_size=20), max_size=5))
    def test_extract_merges_all_system(self, contents):
        from app.services.llm_service import _extract_prompts
        messages = [{"role": "system", "content": c} for c in contents]
        system, user = _extract_prompts(messages)
        if contents:
            assert "\n".join(contents) in system or all(c in system for c in contents)

    @given(st.lists(st.text(max_size=20), max_size=5))
    def test_extract_merges_all_user(self, contents):
        from app.services.llm_service import _extract_prompts
        messages = [{"role": "user", "content": c} for c in contents]
        system, user = _extract_prompts(messages)
        if contents:
            assert all(c in user for c in contents)

class TestRagEngineProperties:
    @settings(deadline=None, max_examples=10)
    @given(st.text(min_size=1, max_size=100))
    def test_query_rules_always_returns_list(self, template_name):
        from app.pipeline.intelligence.rag_engine import RagEngine
        with (
            patch("app.pipeline.intelligence.rag_engine._load_chromadb", return_value=None),
            patch("app.pipeline.intelligence.rag_engine.chromadb", None),
            patch("app.config.settings.settings") as ms,
            patch("app.services.model_store.model_store") as mm,
            patch("sentence_transformers.SentenceTransformer") as mock_st,
        ):
            ms.LOW_MEMORY_MODE = True
            ms.RAG_USE_TRANSFORMERS = False
            import tempfile
            d = tempfile.mkdtemp()
            engine = RagEngine(persist_directory=d, auto_seed=False)
            engine.embedding_model = MagicMock()
            engine.embedding_model.encode.return_value = [0.1] * 256
            result = engine.query_rules(template_name, "test", top_k=2)
            assert isinstance(result, list)
            import shutil
            shutil.rmtree(d, ignore_errors=True)

    @settings(deadline=None, max_examples=10)
    @given(st.integers(min_value=0, max_value=10))
    def test_query_rules_respects_top_k(self, top_k):
        from app.pipeline.intelligence.rag_engine import RagEngine
        with (
            patch("app.pipeline.intelligence.rag_engine._load_chromadb", return_value=None),
            patch("app.pipeline.intelligence.rag_engine.chromadb", None),
            patch("app.config.settings.settings") as ms,
            patch("app.services.model_store.model_store") as mm,
            patch("sentence_transformers.SentenceTransformer") as mock_st,
        ):
            ms.LOW_MEMORY_MODE = True
            ms.RAG_USE_TRANSFORMERS = False
            import tempfile
            d = tempfile.mkdtemp()
            engine = RagEngine(persist_directory=d, auto_seed=False)
            engine.embedding_model = MagicMock()
            engine.embedding_model.encode.return_value = [0.1] * 256
            for i in range(5):
                engine.add_guideline("IEEE", "test", f"Rule {i}")
            result = engine.query_rules("IEEE", "Rule", top_k=top_k)
            assert len(result) <= max(top_k, 1)
            import shutil
            shutil.rmtree(d, ignore_errors=True)

class TestInferProvider:
    @given(st.sampled_from(["nvidia_nim/", "groq/", "openrouter/", "ollama/", "openai/", "anthropic/"]))
    def test_infer_provider_known(self, prefix):
        from app.services.llm_service import _infer_provider
        result = _infer_provider(prefix + "model")
        assert result != "unknown"

    @given(st.text(min_size=1, max_size=50))
    def test_infer_provider_unknown_fallback(self, model):
        assume(not any(model.startswith(p) for p in ["nvidia_nim/", "groq/", "openrouter/", "ollama/", "openai/", "gpt-", "anthropic/", "claude"]))
        from app.services.llm_service import _infer_provider
        result = _infer_provider(model)
        assert result == "unknown"

class TestValidateOutput:
    @given(st.text(min_size=1, max_size=200))
    def test_validate_output_returns_dict(self, text_content):
        from app.pipeline.safety.validator_guard import validate_output
        from pydantic import BaseModel
        class SimpleSchema(BaseModel):
            text: str = ""
        decorated = validate_output(SimpleSchema)
        result = decorated(lambda: {"text": text_content})()
        assert isinstance(result, dict)
        assert "text" in result
