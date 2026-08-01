from unittest.mock import MagicMock


class TestSemanticBlockSchema:
    def test_creates_valid_instance(self):
        from app.pipeline.intelligence.reasoning_engine import SemanticBlockSchema
        s = SemanticBlockSchema(block_id="b1", semantic_type="BODY", confidence=0.9)
        assert s.block_id == "b1"


class TestInstructionSetSchema:
    def test_creates_valid_instance(self):
        from app.pipeline.intelligence.reasoning_engine import InstructionSetSchema
        s = InstructionSetSchema(blocks=[], fallback=False)
        assert s.fallback is False


class TestCircuitFallback:
    def test_delegates_to_rule_based(self):
        from app.pipeline.intelligence.reasoning_engine import _instruction_set_circuit_fallback
        engine = MagicMock()
        engine._rule_based_fallback.return_value = {"blocks": []}
        result = _instruction_set_circuit_fallback(engine, [], "")
        assert result == {"blocks": []}
