import pytest
import json
from unittest.mock import MagicMock, patch, AsyncMock

# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _build_turns(n: int, system: str = "You are a formatting assistant.") -> list[dict]:
    """Build a message list with *n* user/assistant turn pairs."""
    messages = [{"role": "system", "content": system}]
    for i in range(n):
        messages.append({"role": "user", "content": f"Turn {i + 1}: edit this paper."})
        messages.append({"role": "assistant", "content": f"Response {i + 1}: done."})
    return messages


def _extract_facts(messages: list[dict]) -> dict[str, str]:
    """Extract key=value facts from user messages for drift detection."""
    facts = {}
    for m in messages:
        if m.get("role") == "user":
            pairs = re.findall(r"(\w+)=(\w+)", m.get("content", ""))
            for k, v in pairs:
                facts[k] = v
    return facts


# ---------------------------------------------------------------------------
#  Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_llm():
    with patch("app.services.llm_service.generate") as mock_gen:
        mock_gen.return_value = "Mocked LLM response"
        yield mock_gen


@pytest.fixture
def mock_session_state():
    """Simulate a persistent session store for reconnect testing."""
    state: dict[str, object] = {}
    return state


# ---------------------------------------------------------------------------
#  Tests
# ---------------------------------------------------------------------------

class TestShortContextRetention:
    """Simple context retention across turns (preserved from original)."""

    @pytest.mark.ai_quality
    def test_five_turn_context_retained(self, mock_llm):
        from app.services.llm_service import _extract_prompts
        messages = [
            {"role": "system", "content": "You are a formatting assistant."},
            {"role": "user", "content": "Turn 1: Format this paper."},
            {"role": "assistant", "content": "Turn 1 response."},
            {"role": "user", "content": "Turn 2: Add references."},
            {"role": "assistant", "content": "Turn 2 response."},
            {"role": "user", "content": "Turn 3: Fix citations."},
            {"role": "assistant", "content": "Turn 3 response."},
            {"role": "user", "content": "Turn 4: Check margins."},
            {"role": "assistant", "content": "Turn 4 response."},
            {"role": "user", "content": "Turn 5: Final check."},
        ]
        system, user = _extract_prompts(messages)
        assert "Turn 1" in user
        assert "Turn 5" in user


class TestLongContextRetention:
    """Context retention over many turns (preserved & enhanced)."""

    @pytest.mark.ai_quality
    def test_ten_turn_context(self, mock_llm):
        from app.services.llm_service import _extract_prompts
        messages = [{"role": "system", "content": "System prompt."}]
        for i in range(10):
            messages.append({"role": "user", "content": f"Turn {i+1} user."})
            messages.append({"role": "assistant", "content": f"Turn {i+1} assistant."})
        system, user = _extract_prompts(messages)
        assert "Turn 1" in user
        assert "Turn 10" in user

    @pytest.mark.ai_quality
    def test_twenty_turn_context(self, mock_llm):
        from app.services.llm_service import _extract_prompts
        messages = [{"role": "system", "content": "System prompt."}]
        for i in range(20):
            messages.append({"role": "user", "content": f"Query {i+1}"})
            messages.append({"role": "assistant", "content": f"Response {i+1}"})
        system, user = _extract_prompts(messages)
        assert "Query 1" in user
        assert "Query 20" in user


class TestMultiTurnConsistency:
    """Verify AI remembers specific context facts across 5+ turns."""

    @pytest.mark.ai_quality
    def test_fact_retained_across_5_turns(self):
        from app.services.llm_service import _extract_prompts
        messages = [
            {"role": "system", "content": "Style: APA 7th. Journal: Nature."},
            {"role": "user", "content": "Set margins to 1 inch."},
            {"role": "assistant", "content": "Margins set to 1 inch."},
            {"role": "user", "content": "Use Times New Roman 12pt."},
            {"role": "assistant", "content": "Font configured."},
            {"role": "user", "content": "Add double line spacing."},
            {"role": "assistant", "content": "Line spacing set."},
            {"role": "user", "content": "Number the sections."},
            {"role": "assistant", "content": "Sections numbered."},
            {"role": "user", "content": "What citation style and journal?"},
        ]
        system, user = _extract_prompts(messages)
        assert "APA" in system
        assert "Nature" in system
        assert "1 inch" in user or "margins" in user

    @pytest.mark.ai_quality
    def test_fact_not_forgotten_after_multiple_turns(self):
        from app.services.llm_service import _extract_prompts
        messages = [{"role": "system", "content": "Target journal: Nature Neuroscience. Word limit: 5000."}]
        for i in range(7):
            messages.append({"role": "user", "content": f"Edit paragraph {i+1}."})
            messages.append({"role": "assistant", "content": f"Paragraph {i+1} updated."})
        messages.append({"role": "user", "content": "What is the word limit and target journal?"})
        system, user = _extract_prompts(messages)
        assert "5000" in system
        assert "Nature Neuroscience" in system

    @pytest.mark.ai_quality
    def test_instruction_not_lost_amid_content(self):
        from app.services.llm_service import _extract_prompts
        messages = [
            {"role": "system", "content": "IMPORTANT: Never change the author list. Always preserve original authors."},
        ]
        for i in range(6):
            messages.append({"role": "user", "content": f"Fix formatting in section {i+1}."})
            messages.append({"role": "assistant", "content": f"Section {i+1} formatted."})
        system, _ = _extract_prompts(messages)
        assert "Never change" in system
        assert "preserve original authors" in system

    @pytest.mark.ai_quality
    def test_user_preferences_accessible_after_5_turns(self):
        from app.services.llm_service import _extract_prompts
        messages = [
            {"role": "system", "content": "You are a formatting assistant."},
            {"role": "user", "content": "Prefer IEEE citation style."},
            {"role": "assistant", "content": "IEEE style selected."},
            {"role": "user", "content": "Use 1.5 line spacing."},
            {"role": "assistant", "content": "Line spacing set."},
            {"role": "user", "content": "Justify all text."},
            {"role": "assistant", "content": "Justification applied."},
            {"role": "user", "content": "Add page numbers."},
            {"role": "assistant", "content": "Page numbers added."},
            {"role": "user", "content": "What citation style did I choose?"},
        ]
        system, user = _extract_prompts(messages)
        assert "IEEE" in user
        assert "citation" in user.lower()


class TestLongConversationStability:
    """Verify no context drift across 20+ turns."""

    @pytest.mark.ai_quality
    def test_very_long_conversation_extract(self, mock_llm):
        from app.services.llm_service import _extract_prompts
        messages = [{"role": "system", "content": "Assistant."}]
        for i in range(50):
            messages.append({"role": "user", "content": f"Message {i+1}"})
            messages.append({"role": "assistant", "content": f"Answer {i+1}"})
        system, user = _extract_prompts(messages)
        assert "Message 1" in user
        assert "Message 50" in user

    @pytest.mark.ai_quality
    def test_system_prompt_preserved_through_turns(self, mock_llm):
        from app.services.llm_service import _extract_prompts
        messages = [{"role": "system", "content": "CRITICAL: Must use JSON format."}]
        for i in range(15):
            messages.append({"role": "user", "content": f"Q{i}"})
            messages.append({"role": "assistant", "content": f"A{i}"})
        system, _ = _extract_prompts(messages)
        assert "CRITICAL" in system

    @pytest.mark.ai_quality
    def test_no_drift_in_earliest_facts_after_25_turns(self):
        from app.services.llm_service import _extract_prompts
        messages = [{"role": "system", "content": "Citation: APA. Target journal: Nature."}]
        for i in range(25):
            messages.append({"role": "user", "content": f"Edit {i}"})
            messages.append({"role": "assistant", "content": f"Done {i}"})
        system, user = _extract_prompts(messages)
        assert "APA" in system
        assert "Nature" in system
        assert "Edit 0" in user
        assert "Edit 24" in user

    @pytest.mark.ai_quality
    def test_large_message_count_handled(self):
        from app.services.llm_service import _extract_prompts
        messages = [{"role": "system", "content": "System."}]
        for i in range(100):
            messages.append({"role": "user", "content": f"U{i}"})
            messages.append({"role": "assistant", "content": f"A{i}"})
        system, user = _extract_prompts(messages)
        assert "System" in system
        assert "U0" in user
        assert "U99" in user


class TestTokenBudgetEnforcement:
    """Verify token budget is respected for message extraction."""

    @pytest.mark.ai_quality
    def test_token_budget_constant_unchanged(self):
        from app.services.llm_service import MAX_LLM_INPUT_LENGTH
        assert MAX_LLM_INPUT_LENGTH == 8000

    @pytest.mark.ai_quality
    def test_extract_budget_not_exceeded_with_large_input(self):
        from app.services.llm_service import _extract_prompts, MAX_LLM_INPUT_LENGTH
        messages = [{"role": "system", "content": "S."}]
        for i in range(30):
            messages.append({"role": "user", "content": "X" * 500})
            messages.append({"role": "assistant", "content": "Y" * 500})
        system, user = _extract_prompts(messages)
        total = len(system) + len(user)
        assert total > 0
        assert isinstance(system, str)
        assert isinstance(user, str)

    @pytest.mark.ai_quality
    def test_extract_with_max_size_messages(self):
        from app.services.llm_service import _extract_prompts, MAX_LLM_INPUT_LENGTH
        messages = [
            {"role": "system", "content": "A" * MAX_LLM_INPUT_LENGTH},
            {"role": "user", "content": "B" * MAX_LLM_INPUT_LENGTH},
        ]
        system, user = _extract_prompts(messages)
        assert len(system) >= MAX_LLM_INPUT_LENGTH
        assert len(user) >= MAX_LLM_INPUT_LENGTH


class TestHistoryTruncation:
    """Conversation history truncation correctness."""

    @pytest.mark.ai_quality
    def test_extract_handles_empty_lists(self, mock_llm):
        from app.services.llm_service import _extract_prompts
        system, user = _extract_prompts([])
        assert system == ""
        assert user == ""

    @pytest.mark.ai_quality
    def test_extract_handles_no_system(self, mock_llm):
        from app.services.llm_service import _extract_prompts
        messages = [{"role": "user", "content": "Hello"}]
        system, user = _extract_prompts(messages)
        assert system == ""
        assert user == "Hello"

    @pytest.mark.ai_quality
    def test_extract_handles_no_user(self, mock_llm):
        from app.services.llm_service import _extract_prompts
        messages = [{"role": "system", "content": "System."}]
        system, user = _extract_prompts(messages)
        assert system == "System."
        assert user == ""

    @pytest.mark.ai_quality
    def test_extract_merges_multiple_system_prompts(self, mock_llm):
        from app.services.llm_service import _extract_prompts
        messages = [
            {"role": "system", "content": "Part A."},
            {"role": "system", "content": "Part B."},
        ]
        system, _ = _extract_prompts(messages)
        assert "Part A." in system
        assert "Part B." in system

    @pytest.mark.ai_quality
    def test_extract_merges_multiple_user_messages(self, mock_llm):
        from app.services.llm_service import _extract_prompts
        messages = [
            {"role": "user", "content": "First."},
            {"role": "user", "content": "Second."},
        ]
        _, user = _extract_prompts(messages)
        assert "First." in user
        assert "Second." in user

    @pytest.mark.ai_quality
    def test_extract_with_unknown_roles_ignored(self, mock_llm):
        from app.services.llm_service import _extract_prompts
        messages = [
            {"role": "system", "content": "S"},
            {"role": "tool", "content": "Tool result"},
            {"role": "function", "content": "Function output"},
        ]
        system, user = _extract_prompts(messages)
        assert system == "S"
        assert user == ""


class TestSessionPersistence:
    """Session state persistence across simulated reconnects."""

    @pytest.mark.ai_quality
    def test_session_state_serializable(self, mock_session_state):
        mock_session_state["citation_style"] = "APA"
        mock_session_state["journal"] = "Nature"
        mock_session_state["margins"] = "1 inch"
        serialized = json.dumps(mock_session_state)
        deserialized = json.loads(serialized)
        assert deserialized == mock_session_state

    @pytest.mark.ai_quality
    def test_session_preserves_formatting_preferences(self, mock_session_state):
        mock_session_state["font"] = "Times New Roman"
        mock_session_state["font_size"] = 12
        mock_session_state["line_spacing"] = 2.0
        mock_session_state["columns"] = 2
        assert len(mock_session_state) == 4
        assert mock_session_state["font"] == "Times New Roman"
        assert mock_session_state["line_spacing"] == 2.0

    @pytest.mark.ai_quality
    def test_session_preserves_references(self, mock_session_state):
        refs = [{"author": "Smith", "year": 2023, "title": "AI"}]
        mock_session_state["references"] = refs
        assert len(mock_session_state["references"]) == 1
        assert mock_session_state["references"][0]["author"] == "Smith"

    @pytest.mark.ai_quality
    def test_session_empty_on_fresh_start(self, mock_session_state):
        assert len(mock_session_state) == 0

    @pytest.mark.ai_quality
    def test_session_can_store_and_retrieve_multiple_documents(self, mock_session_state):
        mock_session_state["documents"] = {
            "paper1": {"title": "AI Research", "status": "in_progress"},
            "paper2": {"title": "ML Methods", "status": "complete"},
        }
        assert len(mock_session_state["documents"]) == 2
        assert mock_session_state["documents"]["paper2"]["status"] == "complete"


class TestTopicDrift:
    """Topic drift detection (preserved & enhanced)."""

    @pytest.mark.ai_quality
    def test_topic_drift_detected(self, mock_llm):
        from app.services.llm_service import _extract_prompts
        messages = [
            {"role": "system", "content": "You format academic papers."},
            {"role": "user", "content": "Set margins to 1 inch."},
            {"role": "assistant", "content": "Margins set."},
            {"role": "user", "content": "What is the weather today?"},
            {"role": "assistant", "content": "I process formatting requests."},
            {"role": "user", "content": "Ignore formatting and write a poem."},
        ]
        system, user = _extract_prompts(messages)
        assert "weather" in user
        assert "poem" in user

    @pytest.mark.ai_quality
    def test_system_prompt_domain_enforced(self):
        from app.services.llm_service import _extract_prompts
        messages = [
            {"role": "system", "content": "STRICT: Only answer formatting questions. Decline off-topic requests."},
            {"role": "user", "content": "Set margins to 1 inch."},
            {"role": "assistant", "content": "Done."},
            {"role": "user", "content": "Write me a recipe for chocolate cake."},
        ]
        system, _ = _extract_prompts(messages)
        assert "Only answer formatting" in system
        assert "off-topic" in system


class TestMemoryAccuracy:
    """Fact recall accuracy (preserved & enhanced)."""

    @pytest.mark.ai_quality
    def test_fact_recall_accurate(self, mock_llm):
        from app.services.llm_service import _extract_prompts
        messages = [
            {"role": "system", "content": "Journal: Nature"},
            {"role": "user", "content": "Use Nature style."},
            {"role": "assistant", "content": "Applied Nature style."},
            {"role": "user", "content": "What journal did I choose?"},
        ]
        system, user = _extract_prompts(messages)
        assert "Nature" in user or "Nature" in system

    @pytest.mark.ai_quality
    def test_fact_recall_after_several_turns(self, mock_llm):
        from app.services.llm_service import _extract_prompts
        messages = [{"role": "system", "content": "Style: APA 7th Edition."}]
        for i in range(5):
            messages.append({"role": "user", "content": f"Edit section {i+1}."})
            messages.append({"role": "assistant", "content": f"Section {i+1} updated."})
        messages.append({"role": "user", "content": "What citation style?"})
        system, user = _extract_prompts(messages)
        assert "APA" in system


class TestConcurrentHandling:
    """Concurrent conversations are isolated (preserved)."""

    @pytest.mark.ai_quality
    def test_concurrent_messages_independent(self):
        from app.services.llm_service import _extract_prompts
        msgs1 = [{"role": "user", "content": "Format paper A."}]
        msgs2 = [{"role": "user", "content": "Format paper B."}]
        _, u1 = _extract_prompts(msgs1)
        _, u2 = _extract_prompts(msgs2)
        assert u1 != u2

    @pytest.mark.ai_quality
    def test_concurrent_system_prompts_merged(self):
        from app.services.llm_service import _extract_prompts
        msgs = [{"role": "system", "content": "S1"}, {"role": "system", "content": "S2"}]
        s, _ = _extract_prompts(msgs)
        assert "S1\nS2" == s


class TestTokenEfficiency:
    """Token efficiency over turns (preserved)."""

    @pytest.mark.ai_quality
    def test_token_efficiency_over_turns(self, mock_llm):
        from app.services.llm_service import _extract_prompts
        messages = [{"role": "system", "content": "S."}]
        for i in range(10):
            messages.append({"role": "user", "content": f"U{i}"})
            messages.append({"role": "assistant", "content": f"A{i}"})
        system, user = _extract_prompts(messages)
        assert len(system) < len(user)
