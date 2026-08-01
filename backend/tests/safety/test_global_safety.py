# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI


import asyncio
import logging
import sys
from unittest.mock import MagicMock, patch

import pytest

from app.pipeline.safety import safe_execution, safe_function

# Mock langchain to avoid installation requirement for safety tests
sys.modules["langchain"] = MagicMock()
sys.modules["langchain.agents"] = MagicMock()
sys.modules["langchain.chat_models"] = MagicMock()
sys.modules["langchain.prompts"] = MagicMock()
sys.modules["langchain.tools"] = MagicMock() 
sys.modules["langchain.llms"] = MagicMock()
sys.modules["langchain.llms.base"] = MagicMock()
sys.modules["langchain_openai"] = MagicMock()
sys.modules["langchain.callbacks"] = MagicMock()
sys.modules["langchain.callbacks.base"] = MagicMock()
sys.modules["langchain.schema"] = MagicMock()
sys.modules["langchain.callbacks.base"] = MagicMock()

from app.pipeline.agents.deep_learning import TransformerPatternDetector
from app.pipeline.agents.document_agent import DocumentAgent
from app.pipeline.agents.ml_patterns import MLPatternDetector
from app.pipeline.intelligence.rag_engine import RagEngine
from app.pipeline.intelligence.semantic_parser import SemanticParser
from app.pipeline.parsing.parser_factory import ParserFactory
from app.pipeline.services.docling_client import DoclingClient

# Configure logging to capture output
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestGlobalSafety:
    """
    Test suite to verify that safety wrappers are correctly applied 
    and prevent crashes across all critical components.
    """

    def test_safe_execution_context_manager(self):
        """Test the basic safe_execution context manager."""
        with safe_execution("Test Operation"):
            raise ValueError("Simulated Crash")
        # If we reach here, the exception was caught by safe_execution.
        # Verify no unhandled exception propagated.

    def test_safe_function_decorator(self):
        """Test the safe_function decorator."""
        @safe_function(fallback_value="SAFE", error_message="Test Func")
        def risky_function():
            raise ValueError("Simulated Crash")
        
        result = risky_function()
        assert result == "SAFE"

    def test_semantic_parser_safety(self):
        """Test SemanticParser handles model crashes gracefully."""
        # Helper to get a SemanticParser instance, potentially with mocked dependencies
        def get_semantic_parser():
            with patch('app.pipeline.intelligence.semantic_parser.SemanticParser._load_model'):
                return SemanticParser()

        parser = get_semantic_parser()
        # Mock _repair_fragmented_headings to fail, effectively crashing analyze_blocks
        with patch.object(parser, '_repair_fragmented_headings', side_effect=Exception("Crash")):
            result = parser.analyze_blocks([])
        # Verify it falls back to empty list as per decorator
        assert result == []

    def test_rag_engine_safety(self):
        """Test RagEngine handles retrieval failures gracefully."""
        engine = RagEngine()
        # Patch query_guidelines instead of retrieve
        # RagEngine.query_rules is the safe wrapper (via try-except block), let's test that.
        with patch.object(engine, 'query_guidelines', side_effect=Exception("Crash")):
            result = engine.query_rules("IEEE", "methods")
        assert result == []

    def test_document_agent_safety(self):
        """Test DocumentAgent handles processing errors gracefully."""
        # Mock LLM creation to avoid OPENAI_API_KEY error during init
        with patch('app.pipeline.agents.llm_factory.CustomLLMFactory.create_llm') as mock_llm:
            mock_llm.return_value = MagicMock()
            agent = DocumentAgent(enable_memory=False)
            
            # Mocking run to fail
            # We patch _execute_with_retry to simulate internal failure
            with patch.object(agent, '_execute_with_retry', side_effect=Exception("Agent crashed safely")):
                # document_agent.run IS decorated with safe_async_function
                # We must await it
                result = asyncio.run(agent.run(None, "test_job"))
            
            assert result["success"] is False
            assert "Agent crashed safely" in result["error"] or "Agent crashed safely" in result.get("message", "")

    def test_docling_client_safety(self):
        """Test DoclingClient handles library errors gracefully."""
        # Patch DOCLING_AVAILABLE to False to trigger immediate fallback
        with patch('app.pipeline.services.docling_client.DOCLING_AVAILABLE', False):
            client = DoclingClient()
            result = client.analyze_layout("test.pdf")
        assert isinstance(result, dict)
        assert result.get("elements", []) == []

    def test_deep_learning_safety(self):
        """Verify TransformerPatternDetector doesn't crash."""
        # Initialize with dummy to avoid real model loading
        with patch('app.pipeline.agents.deep_learning.AutoTokenizer'), \
             patch('app.pipeline.agents.deep_learning.AutoModel'):
            detector = TransformerPatternDetector()
            
            # Force crash in encode_document
            with patch.object(detector, 'tokenizer', side_effect=Exception("Crash")):
                result = detector.encode_document("text")
                assert result.shape == (768,) # Fallback is zeros

    def test_ml_patterns_safety(self):
        """Verify MLPatternDetector doesn't crash."""
        detector = MLPatternDetector()
        
        # Force crash in fit
        with patch.object(detector, 'scaler', side_effect=Exception("Crash")):
             # scaler.fit_transform called in fit
             detector.scaler.fit_transform.side_effect = Exception("Crash")
             result = detector.fit([{}])
             assert result is False

    def test_parser_factory_safety(self):
        """Verify ParserFactory doesn't crash."""
        factory = ParserFactory()
        
        # Inject a malicious parser that crashes when checked
        mock_parser = MagicMock()
        mock_parser.supports_format.side_effect = Exception("Crash")
        factory.parsers = [mock_parser]
        
        # Should catch crash and return None
        result = factory.get_parser("dummy.pdf")
        assert result is None


class TestPhase3Safety:
    """Test suite for Phase 3 Hardening: Formatter, Validator, Detector, Routers."""

    def test_safe_async_function(self):
        """Verify safe_async_function decorator works."""
        import asyncio

        from app.pipeline.safety.safe_execution import safe_async_function
        
        @safe_async_function(fallback_value="ASYNC_SAFE", error_message="Async Fail")
        async def risky_async():
            raise ValueError("Async Crash")
            
        result = asyncio.run(risky_async())
        assert result == "ASYNC_SAFE"

    def test_formatter_safety(self):
        """Verify Formatter.process and format don't crash."""
        from app.models import PipelineDocument
        from app.pipeline.formatting.formatter import Formatter
        
        # Mock dependencies to avoid filesystem/template issues during test
        with patch('app.pipeline.formatting.formatter.ContractLoader'), \
             patch('app.pipeline.formatting.formatter.StyleMapper'), \
             patch('app.pipeline.formatting.formatter.NumberingEngine'), \
             patch('app.pipeline.formatting.formatter.ReferenceFormatter'), \
             patch('app.pipeline.formatting.formatter.TemplateRenderer'), \
             patch('app.pipeline.formatting.formatter.TableRenderer'):
            
            formatter = Formatter()
            doc = PipelineDocument(document_id="test", filename="test.docx")
            
            # Test that calling the REAL wrapped method catches exception if internal logic fails.
            # We trigger a crash in numbering_engine, which is called early in format()
            formatter.numbering_engine.apply_numbering.side_effect = Exception("Engine Crash")
            
            result = formatter.process(doc)
            assert result is doc
            # Depending on how the mocks are set up, generated_doc might be None or the fallback
            # safe_execution returns None on error, so generated_doc = None
            assert doc.generated_doc is None

    def test_validator_safety(self):
        """Verify Validator.validate doesn't crash."""
        from app.models import PipelineDocument
        from app.pipeline.validation import DocumentValidator, ValidationResult
        
        with patch('app.pipeline.validation.validator_v3.ContractLoader'), \
             patch('app.pipeline.validation.validator_v3.SectionOrderValidator'), \
             patch('app.pipeline.validation.validator_v3.CrossRefClient'):
             
            validator = DocumentValidator()
            doc = PipelineDocument(document_id="test", filename="test.docx")
            
            # Force crash in internal _check_sections
            # Note: _check_sections is called by validate -> check_sections
            # We must be careful if we are patching the INSTANCE method or CLASS method.
            # Here we are patching the INSTANCE method on the LIVE object if we use patch.object(validator...)
            
            with patch.object(validator, '_check_sections', side_effect=Exception("Check Crash")):
                result = validator.validate(doc)
                assert isinstance(result, ValidationResult)
                assert result.is_valid is False
                assert "Validation process crashed unexpectedly" in result.errors

    def test_structure_detector_safety(self):
        """Verify StructureDetector.process doesn't crash."""
        from app.models import PipelineDocument
        from app.pipeline.structure_detection.detector import StructureDetector
        
        with patch('app.pipeline.structure_detection.detector.ContractLoader'), \
             patch('app.pipeline.structure_detection.detector.datetime'):
            
            detector = StructureDetector()
            doc = PipelineDocument(document_id="test", filename="test.docx")
            doc.metadata.ai_hints = {} 
            
            # Force crash in _detect_heading_candidates (standard path)
            with patch.object(detector, '_detect_heading_candidates', side_effect=Exception("Rule Crash")):
                # process is wrapped with safe_execution context manager
                result = detector.process(doc)
                assert result is doc

if __name__ == "__main__":
    pytest.main([__file__])
