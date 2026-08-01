from __future__ import annotations
import pytest
from unittest.mock import MagicMock, patch


class TestSuggestionServiceBuildPrompt:
    @pytest.fixture
    def svc(self):
        from app.services.suggestion_service import SuggestionService
        return SuggestionService

    def test_style_prompt(self, svc):
        messages = svc._build_suggestion_prompt("Some text", "style")
        assert len(messages) == 2
        assert "academic writing style" in messages[0]["content"]
        assert "Some text" in messages[1]["content"]

    def test_grammar_prompt(self, svc):
        messages = svc._build_suggestion_prompt("Text", "grammar")
        assert "grammar" in messages[0]["content"]

    def test_unknown_type_fallback(self, svc):
        messages = svc._build_suggestion_prompt("Text", "unknown")
        assert "academic writing assistant" in messages[0]["content"]

    def test_structure_prompt(self, svc):
        messages = svc._build_suggestion_prompt("Text", "structure")
        assert "structural improvements" in messages[0]["content"]

    def test_citation_prompt(self, svc):
        messages = svc._build_suggestion_prompt("Refs", "citation")
        assert "citation" in messages[0]["content"].lower()


class TestUtcNowIso:
    @pytest.fixture
    def svc(self):
        from app.services.suggestion_service import SuggestionService
        return SuggestionService

    def test_returns_iso(self, svc):
        result = svc._utc_now_iso()
        assert "T" in result


class TestCallLlmForSuggestion:
    @pytest.fixture
    def svc(self):
        return __import__("app.services.suggestion_service", fromlist=["SuggestionService"]).SuggestionService

    @patch("app.services.llm_service.generate_with_fallback")
    async def test_returns_text(self, mock_gen, svc):
        mock_gen.return_value = {"text": "Improved text"}
        result = await svc._call_llm_for_suggestion("Original", "style")
        assert result == "Improved text"

    @patch("app.services.llm_service.generate_with_fallback")
    async def test_empty_text_returns_none(self, mock_gen, svc):
        mock_gen.return_value = {"text": ""}
        result = await svc._call_llm_for_suggestion("Text", "style")
        assert result is None

    @patch("app.services.llm_service.generate_with_fallback")
    async def test_exception_returns_none(self, mock_gen, svc):
        mock_gen.side_effect = Exception("LLM down")
        result = await svc._call_llm_for_suggestion("Text", "style")
        assert result is None


class TestGenerateSuggestion:
    @pytest.fixture
    def svc(self):
        svc = __import__("app.services.suggestion_service", fromlist=["SuggestionService"]).SuggestionService
        svc._table_available = None
        svc._table_warning_logged = False
        return svc

    @patch("app.services.suggestion_service.get_supabase_client")
    @patch("app.services.suggestion_service.asyncio.to_thread")
    @patch.object(__import__("app.services.suggestion_service", fromlist=["SuggestionService"]).SuggestionService, "_call_llm_for_suggestion")
    async def test_generates_and_saves(self, mock_llm, mock_to_thread, mock_get_sb, svc):
        mock_llm.return_value = "Improved text"
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_result = MagicMock()
        mock_result.data = [{"id": "sug-1", "suggested_text": "Improved text"}]
        mock_to_thread.return_value = mock_result
        result = await svc.generate_suggestion(
            document_id="doc-1",
            block={"id": "b1", "type": "paragraph", "text": "Original text", "section": "intro"},
            suggestion_type="style",
            user_id="user-1",
            session_id="sess-1",
        )
        assert result is not None
        assert result["id"] == "sug-1"

    @patch("app.services.suggestion_service.get_supabase_client")
    @patch("app.services.suggestion_service.asyncio.to_thread")
    @patch.object(__import__("app.services.suggestion_service", fromlist=["SuggestionService"]).SuggestionService, "_call_llm_for_suggestion")
    async def test_llm_fails_uses_original(self, mock_llm, mock_to_thread, mock_get_sb, svc):
        mock_llm.return_value = None
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_result = MagicMock()
        mock_result.data = [{"id": "sug-1"}]
        mock_to_thread.return_value = mock_result
        result = await svc.generate_suggestion(
            document_id="doc-1",
            block={"id": "b1", "type": "paragraph", "text": "Original"},
            suggestion_type="style",
        )
        assert result is not None

    async def test_unknown_type_returns_none(self, svc):
        result = await svc.generate_suggestion(
            document_id="doc-1",
            block={"id": "b1", "text": "Text"},
            suggestion_type="unknown_type",
        )
        assert result is None

    async def test_empty_text_returns_none(self, svc):
        result = await svc.generate_suggestion(
            document_id="doc-1",
            block={"id": "b1", "text": ""},
            suggestion_type="style",
        )
        assert result is None

    async def test_whitespace_text_returns_none(self, svc):
        result = await svc.generate_suggestion(
            document_id="doc-1",
            block={"id": "b1", "text": "   "},
            suggestion_type="style",
        )
        assert result is None

    @patch("app.services.suggestion_service.get_supabase_client", return_value=None)
    @patch.object(__import__("app.services.suggestion_service", fromlist=["SuggestionService"]).SuggestionService, "_call_llm_for_suggestion")
    async def test_no_supabase_raises(self, mock_llm, mock_get_sb, svc):
        mock_llm.return_value = "Improved"
        from app.exceptions import DatabaseUnavailableError
        with pytest.raises(DatabaseUnavailableError):
            await svc.generate_suggestion(
                document_id="doc-1",
                block={"id": "b1", "text": "Text"},
                suggestion_type="style",
            )

    @patch("app.services.suggestion_service.get_supabase_client")
    @patch("app.services.suggestion_service.asyncio.to_thread")
    @patch.object(__import__("app.services.suggestion_service", fromlist=["SuggestionService"]).SuggestionService, "_call_llm_for_suggestion")
    async def test_missing_table_sets_flag(self, mock_llm, mock_to_thread, mock_get_sb, svc):
        mock_llm.return_value = "Improved"
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_to_thread.side_effect = Exception("Could not find the table 'suggestions'")
        result = await svc.generate_suggestion(
            document_id="doc-1",
            block={"id": "b1", "text": "Text"},
            suggestion_type="clarity",
        )
        assert result is None
        assert svc._table_available is False


class TestGetSuggestions:
    @pytest.fixture
    def svc(self):
        return __import__("app.services.suggestion_service", fromlist=["SuggestionService"]).SuggestionService

    @patch("app.services.suggestion_service.get_supabase_client")
    @patch("app.services.suggestion_service.asyncio.to_thread")
    async def test_returns_suggestions(self, mock_to_thread, mock_get_sb, svc):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_result = MagicMock()
        mock_result.data = [{"id": "s1", "suggestion_type": "style"}]
        mock_to_thread.return_value = mock_result
        result = await svc.get_suggestions("doc-1")
        assert len(result) == 1

    @patch("app.services.suggestion_service.get_supabase_client", return_value=None)
    async def test_no_supabase_raises(self, mock_get_sb, svc):
        from app.exceptions import DatabaseUnavailableError
        with pytest.raises(DatabaseUnavailableError):
            await svc.get_suggestions("doc-1")

    @patch("app.services.suggestion_service.get_supabase_client")
    @patch("app.services.suggestion_service.asyncio.to_thread")
    async def test_missing_table_returns_empty(self, mock_to_thread, mock_get_sb, svc):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_to_thread.side_effect = Exception("Could not find the table 'suggestions'")
        result = await svc.get_suggestions("doc-1")
        assert result == []

    @patch("app.services.suggestion_service.get_supabase_client")
    @patch("app.services.suggestion_service.asyncio.to_thread")
    async def test_with_status_filter(self, mock_to_thread, mock_get_sb, svc):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_result = MagicMock()
        mock_result.data = [{"id": "s1", "status": "pending"}]
        mock_to_thread.return_value = mock_result
        result = await svc.get_suggestions("doc-1", status="pending")
        assert len(result) == 1


class TestUpdateSuggestionStatus:
    @pytest.fixture
    def svc(self):
        return __import__("app.services.suggestion_service", fromlist=["SuggestionService"]).SuggestionService

    @patch("app.services.suggestion_service.get_supabase_client")
    @patch("app.services.suggestion_service.asyncio.to_thread")
    async def test_updates_successfully(self, mock_to_thread, mock_get_sb, svc):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_result = MagicMock()
        mock_result.data = [{"id": "s1", "status": "accepted"}]
        mock_to_thread.return_value = mock_result
        result = await svc._update_suggestion_status("s1", "accepted")
        assert result["status"] == "accepted"

    async def test_invalid_status_returns_none(self, svc):
        result = await svc._update_suggestion_status("s1", "invalid_status")
        assert result is None

    @patch("app.services.suggestion_service.get_supabase_client", return_value=None)
    async def test_no_supabase_raises(self, mock_get_sb, svc):
        from app.exceptions import DatabaseUnavailableError
        with pytest.raises(DatabaseUnavailableError):
            await svc._update_suggestion_status("s1", "accepted")

    @patch("app.services.suggestion_service.get_supabase_client")
    @patch("app.services.suggestion_service.asyncio.to_thread")
    async def test_exception_raises(self, mock_to_thread, mock_get_sb, svc):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_to_thread.side_effect = Exception("Update failed")
        from app.exceptions import DatabaseUnavailableError
        with pytest.raises(DatabaseUnavailableError):
            await svc._update_suggestion_status("s1", "accepted")

    @patch("app.services.suggestion_service.get_supabase_client")
    @patch("app.services.suggestion_service.asyncio.to_thread")
    async def test_accepted_sets_accepted_at(self, mock_to_thread, mock_get_sb, svc):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_result = MagicMock()
        mock_result.data = [{"id": "s1", "status": "accepted"}]
        mock_to_thread.return_value = mock_result
        result = await svc._update_suggestion_status("s1", "accepted")
        assert result is not None


class TestAcceptRejectDismiss:
    @pytest.fixture
    def svc(self):
        return __import__("app.services.suggestion_service", fromlist=["SuggestionService"]).SuggestionService

    @patch.object(__import__("app.services.suggestion_service", fromlist=["SuggestionService"]).SuggestionService, "_update_suggestion_status")
    async def test_accept(self, mock_update, svc):
        mock_update.return_value = {"id": "s1", "status": "accepted"}
        result = await svc.accept_suggestion("s1")
        mock_update.assert_called_with("s1", "accepted")
        assert result["status"] == "accepted"

    @patch.object(__import__("app.services.suggestion_service", fromlist=["SuggestionService"]).SuggestionService, "_update_suggestion_status")
    async def test_reject(self, mock_update, svc):
        mock_update.return_value = {"id": "s1", "status": "rejected"}
        await svc.reject_suggestion("s1")
        mock_update.assert_called_with("s1", "rejected")

    @patch.object(__import__("app.services.suggestion_service", fromlist=["SuggestionService"]).SuggestionService, "_update_suggestion_status")
    async def test_dismiss(self, mock_update, svc):
        mock_update.return_value = {"id": "s1", "status": "dismissed"}
        await svc.dismiss_suggestion("s1")
        mock_update.assert_called_with("s1", "dismissed")


class TestGetSuggestionHistory:
    @pytest.fixture
    def svc(self):
        return __import__("app.services.suggestion_service", fromlist=["SuggestionService"]).SuggestionService

    @patch("app.services.suggestion_service.get_supabase_client")
    @patch("app.services.suggestion_service.asyncio.to_thread")
    async def test_returns_history(self, mock_to_thread, mock_get_sb, svc):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_result = MagicMock()
        mock_result.data = [{"id": "s1"}]
        mock_to_thread.return_value = mock_result
        result = await svc.get_suggestion_history("user-1")
        assert len(result) == 1

    @patch("app.services.suggestion_service.get_supabase_client", return_value=None)
    async def test_no_supabase_raises(self, mock_get_sb, svc):
        from app.exceptions import DatabaseUnavailableError
        with pytest.raises(DatabaseUnavailableError):
            await svc.get_suggestion_history("user-1")

    @patch("app.services.suggestion_service.get_supabase_client")
    @patch("app.services.suggestion_service.asyncio.to_thread")
    async def test_missing_table_returns_empty(self, mock_to_thread, mock_get_sb, svc):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_to_thread.side_effect = Exception("Could not find the table 'suggestions'")
        result = await svc.get_suggestion_history("user-1")
        assert result == []


class TestApplySuggestion:
    @pytest.fixture
    def svc(self):
        return __import__("app.services.suggestion_service", fromlist=["SuggestionService"]).SuggestionService

    @patch("app.services.suggestion_service.get_supabase_client")
    @patch("app.services.suggestion_service.asyncio.to_thread")
    async def test_apply_not_pending(self, mock_to_thread, mock_get_sb, svc):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_result = MagicMock()
        mock_result.data = {"id": "s1", "status": "accepted", "suggested_text": "improved"}
        mock_to_thread.return_value = mock_result
        result = await svc.apply_suggestion("s1", "doc-1")
        assert result["status"] == "accepted"

    @patch("app.services.suggestion_service.get_supabase_client")
    @patch("app.services.suggestion_service.asyncio.to_thread")
    async def test_apply_suggestion_not_found(self, mock_to_thread, mock_get_sb, svc):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_result = MagicMock()
        mock_result.data = None
        mock_to_thread.return_value = mock_result
        result = await svc.apply_suggestion("nonexistent", "doc-1")
        assert result is None

    @patch("app.services.suggestion_service.get_supabase_client", return_value=None)
    async def test_no_supabase_raises(self, mock_get_sb, svc):
        from app.exceptions import DatabaseUnavailableError
        with pytest.raises(DatabaseUnavailableError):
            await svc.apply_suggestion("s1", "doc-1")


class TestGenerateSuggestionEdgeCases:
    @pytest.fixture
    def svc(self):
        svc = __import__("app.services.suggestion_service", fromlist=["SuggestionService"]).SuggestionService
        svc._table_available = None
        svc._table_warning_logged = False
        return svc

    @patch("app.services.suggestion_service.get_supabase_client")
    @patch("app.services.suggestion_service.asyncio.to_thread")
    @patch.object(__import__("app.services.suggestion_service", fromlist=["SuggestionService"]).SuggestionService, "_call_llm_for_suggestion")
    async def test_insert_other_error_raises(self, mock_llm, mock_to_thread, mock_get_sb, svc):
        mock_llm.return_value = "Improved"
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_to_thread.side_effect = Exception("DB constraint violation")
        from app.exceptions import DatabaseUnavailableError
        with pytest.raises(DatabaseUnavailableError):
            await svc.generate_suggestion(
                document_id="doc-1",
                block={"id": "b1", "text": "Text"},
                suggestion_type="style",
            )

    @patch("app.services.suggestion_service.get_supabase_client")
    @patch("app.services.suggestion_service.asyncio.to_thread")
    @patch.object(__import__("app.services.suggestion_service", fromlist=["SuggestionService"]).SuggestionService, "_call_llm_for_suggestion")
    async def test_insert_return_no_data(self, mock_llm, mock_to_thread, mock_get_sb, svc):
        mock_llm.return_value = "Improved"
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_result = MagicMock()
        mock_result.data = None
        mock_to_thread.return_value = mock_result
        result = await svc.generate_suggestion(
            document_id="doc-1",
            block={"id": "b1", "text": "Text"},
            suggestion_type="structure",
        )
        assert result is None
        assert svc._table_available is True

    @patch("app.services.suggestion_service.get_supabase_client")
    @patch("app.services.suggestion_service.asyncio.to_thread")
    @patch.object(__import__("app.services.suggestion_service", fromlist=["SuggestionService"]).SuggestionService, "_call_llm_for_suggestion")
    async def test_missing_table_warn_once(self, mock_llm, mock_to_thread, mock_get_sb, svc):
        svc._table_warning_logged = True
        mock_llm.return_value = "Improved"
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_to_thread.side_effect = Exception("Could not find the table 'suggestions'")
        result = await svc.generate_suggestion(
            document_id="doc-1",
            block={"id": "b1", "text": "Text"},
            suggestion_type="clarity",
        )
        assert result is None


class TestGetSuggestionsEdgeCases:
    @pytest.fixture
    def svc(self):
        return __import__("app.services.suggestion_service", fromlist=["SuggestionService"]).SuggestionService

    @patch("app.services.suggestion_service.get_supabase_client")
    @patch("app.services.suggestion_service.asyncio.to_thread")
    async def test_other_error_raises(self, mock_to_thread, mock_get_sb, svc):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_to_thread.side_effect = Exception("Server error")
        from app.exceptions import DatabaseUnavailableError
        with pytest.raises(DatabaseUnavailableError):
            await svc.get_suggestions("doc-1")


class TestGetSuggestionHistoryEdgeCases:
    @pytest.fixture
    def svc(self):
        return __import__("app.services.suggestion_service", fromlist=["SuggestionService"]).SuggestionService

    @patch("app.services.suggestion_service.get_supabase_client")
    @patch("app.services.suggestion_service.asyncio.to_thread")
    async def test_other_error_raises(self, mock_to_thread, mock_get_sb, svc):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_to_thread.side_effect = Exception("Server error")
        from app.exceptions import DatabaseUnavailableError
        with pytest.raises(DatabaseUnavailableError):
            await svc.get_suggestion_history("user-1")


class TestUpdateSuggestionStatusEdgeCases:
    @pytest.fixture
    def svc(self):
        return __import__("app.services.suggestion_service", fromlist=["SuggestionService"]).SuggestionService

    @patch("app.services.suggestion_service.get_supabase_client")
    @patch("app.services.suggestion_service.asyncio.to_thread")
    async def test_data_empty_returns_none(self, mock_to_thread, mock_get_sb, svc):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_result = MagicMock()
        mock_result.data = None
        mock_to_thread.return_value = mock_result
        result = await svc._update_suggestion_status("s1", "rejected")
        assert result is None


class TestApplySuggestionDeep:
    @pytest.fixture
    def svc(self):
        return __import__("app.services.suggestion_service", fromlist=["SuggestionService"]).SuggestionService

    @patch("app.services.suggestion_service.get_supabase_client")
    @patch("app.services.suggestion_service.asyncio.to_thread")
    async def test_fetch_error_raises(self, mock_to_thread, mock_get_sb, svc):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_to_thread.side_effect = Exception("Fetch failed")
        from app.exceptions import DatabaseUnavailableError
        with pytest.raises(DatabaseUnavailableError):
            await svc.apply_suggestion("s1", "doc-1")

    @patch("app.services.suggestion_service.get_supabase_client")
    @patch("app.services.suggestion_service.asyncio.to_thread")
    async def test_pending_with_doc_update(self, mock_to_thread, mock_get_sb, svc):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb

        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            mock_result = MagicMock()
            if call_count[0] == 1:
                mock_result.data = {
                    "id": "s1",
                    "status": "pending",
                    "suggested_text": "Improved text",
                    "context": {"block_id": "b1"},
                }
            elif call_count[0] == 2:
                mock_result.data = [{"id": "s1", "status": "accepted"}]
            elif call_count[0] == 3:
                mock_result.data = {"structured_data": {"blocks": [{"id": "b1", "text": "Original"}]}}
            elif call_count[0] == 4:
                mock_result.data = [{"id": "s1", "status": "accepted"}]
            return mock_result

        mock_to_thread.side_effect = side_effect
        result = await svc.apply_suggestion("s1", "doc-1")
        assert result is not None

    @patch("app.services.suggestion_service.get_supabase_client")
    @patch("app.services.suggestion_service.asyncio.to_thread")
    async def test_pending_no_block_id(self, mock_to_thread, mock_get_sb, svc):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb

        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            mock_result = MagicMock()
            if call_count[0] == 1:
                mock_result.data = {
                    "id": "s1",
                    "status": "pending",
                    "suggested_text": "Improved text",
                    "context": {},
                }
            elif call_count[0] == 2:
                mock_result.data = [{"id": "s1", "status": "accepted"}]
            elif call_count[0] == 3:
                mock_result.data = {"structured_data": {"blocks": [{"id": "b1", "text": "Original"}]}}
            elif call_count[0] == 4:
                mock_result.data = [{"id": "s1", "status": "accepted"}]
            return mock_result

        mock_to_thread.side_effect = side_effect
        result = await svc.apply_suggestion("s1", "doc-1")
        assert result is not None

    @patch("app.services.suggestion_service.get_supabase_client")
    @patch("app.services.suggestion_service.asyncio.to_thread")
    async def test_doc_result_update_failure_logged(self, mock_to_thread, mock_get_sb, svc):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb

        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            mock_result = MagicMock()
            if call_count[0] == 1:
                mock_result.data = {
                    "id": "s1",
                    "status": "pending",
                    "suggested_text": "Improved text",
                    "context": {"block_id": "b1"},
                }
            elif call_count[0] == 2:
                mock_result.data = [{"id": "s1", "status": "accepted"}]
            elif call_count[0] == 3:
                mock_result.data = {"structured_data": {"blocks": [{"id": "b1", "text": "Original"}]}}
            elif call_count[0] == 4:
                raise Exception("Update failed")
            elif call_count[0] == 5:
                mock_result.data = [{"id": "s1", "status": "accepted"}]
            return mock_result

        mock_to_thread.side_effect = side_effect
        result = await svc.apply_suggestion("s1", "doc-1")
        assert result is not None

    @patch("app.services.suggestion_service.get_supabase_client")
    @patch("app.services.suggestion_service.asyncio.to_thread")
    async def test_doc_result_fetch_failure_continues(self, mock_to_thread, mock_get_sb, svc):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb

        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            mock_result = MagicMock()
            if call_count[0] == 1:
                mock_result.data = {
                    "id": "s1",
                    "status": "pending",
                    "suggested_text": "Improved text",
                    "context": {"block_id": "b1"},
                }
            elif call_count[0] == 2:
                mock_result.data = [{"id": "s1", "status": "accepted"}]
            elif call_count[0] == 3:
                raise Exception("Doc fetch failed")
            elif call_count[0] == 4:
                mock_result.data = [{"id": "s1", "status": "accepted"}]
            return mock_result

        mock_to_thread.side_effect = side_effect
        result = await svc.apply_suggestion("s1", "doc-1")
        assert result is not None


class TestSuggestionServiceModule:
    def test_suggestion_service_instance(self):
        from app.services.suggestion_service import suggestion_service
        assert suggestion_service is not None

    def test_suggestion_types(self):
        from app.services.suggestion_service import SUGGESTION_TYPES
        assert "style" in SUGGESTION_TYPES
        assert "grammar" in SUGGESTION_TYPES

    def test_suggestion_statuses(self):
        from app.services.suggestion_service import SUGGESTION_STATUSES
        assert "pending" in SUGGESTION_STATUSES
        assert "accepted" in SUGGESTION_STATUSES


_INLINE_TO_THREAD = lambda fn, *a, **kw: fn(*a, **kw)


class TestSuggestionServiceInnerClosures:
    @pytest.mark.asyncio
    async def test_run_insert_success(self):
        from app.services.suggestion_service import SuggestionService
        svc = SuggestionService
        svc._table_available = None
        svc._table_warning_logged = False
        mock_sb = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{"id": "s1", "suggested_text": "Improved"}]
        mock_sb.table.return_value.insert.return_value.execute.return_value = mock_result
        with patch("app.services.suggestion_service.get_supabase_client", return_value=mock_sb):
            with patch("app.services.suggestion_service.asyncio.to_thread", side_effect=_INLINE_TO_THREAD):
                with patch.object(SuggestionService, "_call_llm_for_suggestion", return_value="Improved"):
                    result = await svc.generate_suggestion(
                        document_id="doc-1",
                        block={"id": "b1", "type": "paragraph", "text": "Original text"},
                        suggestion_type="style",
                    )
        assert result is not None
        assert svc._table_available is True

    @pytest.mark.asyncio
    async def test_get_suggestions_run_query_success(self):
        from app.services.suggestion_service import SuggestionService
        mock_sb = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{"id": "s1"}]
        mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_result
        with patch("app.services.suggestion_service.get_supabase_client", return_value=mock_sb):
            with patch("app.services.suggestion_service.asyncio.to_thread", side_effect=_INLINE_TO_THREAD):
                result = await SuggestionService.get_suggestions("doc-1")
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_suggestions_run_query_with_status(self):
        from app.services.suggestion_service import SuggestionService
        mock_sb = MagicMock()
        mock_eq = MagicMock()
        mock_eq.execute.return_value = MagicMock(data=[{"id": "s1", "status": "pending"}])
        mock_eq.eq.return_value = mock_eq
        mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value = mock_eq
        with patch("app.services.suggestion_service.get_supabase_client", return_value=mock_sb):
            with patch("app.services.suggestion_service.asyncio.to_thread", side_effect=_INLINE_TO_THREAD):
                result = await SuggestionService.get_suggestions("doc-1", status="pending")
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_update_suggestion_status_run_update(self):
        from app.services.suggestion_service import SuggestionService
        mock_sb = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{"id": "s1", "status": "rejected"}]
        mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_result
        with patch("app.services.suggestion_service.get_supabase_client", return_value=mock_sb):
            with patch("app.services.suggestion_service.asyncio.to_thread", side_effect=_INLINE_TO_THREAD):
                result = await SuggestionService._update_suggestion_status("s1", "rejected")
        assert result["status"] == "rejected"

    @pytest.mark.asyncio
    async def test_get_suggestion_history_run_query(self):
        from app.services.suggestion_service import SuggestionService
        mock_sb = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{"id": "s1"}]
        mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_result
        with patch("app.services.suggestion_service.get_supabase_client", return_value=mock_sb):
            with patch("app.services.suggestion_service.asyncio.to_thread", side_effect=_INLINE_TO_THREAD):
                result = await SuggestionService.get_suggestion_history("user-1")
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_apply_suggestion_run_fetch(self):
        from app.services.suggestion_service import SuggestionService
        mock_sb = MagicMock()
        mock_result = MagicMock()
        mock_result.data = {"id": "s1", "status": "accepted", "suggested_text": "improved"}
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_result
        with patch("app.services.suggestion_service.get_supabase_client", return_value=mock_sb):
            with patch("app.services.suggestion_service.asyncio.to_thread", side_effect=_INLINE_TO_THREAD):
                result = await SuggestionService.apply_suggestion("s1", "doc-1")
        assert result is not None
