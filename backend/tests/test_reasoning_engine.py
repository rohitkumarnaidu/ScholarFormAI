# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Test Suite for DeepSeek Reasoning Engine
Tests LLM integration, fallback mechanisms, and error handling.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from app.pipeline.intelligence.reasoning_engine import ReasoningEngine

class TestReasoningEngine:
    """Test suite for DeepSeek reasoning engine."""
    
    @pytest.fixture
    def sample_blocks(self):
        """Sample semantic blocks for testing."""
        return [
            {"block_id": "b1", "text": "Introduction", "index": 0},
            {"block_id": "b2", "text": "This paper presents a novel approach.", "index": 1},
            {"block_id": "b3", "text": "Methodology", "index": 2}
        ]
    
    @pytest.fixture
    def sample_rules(self):
        """Sample publisher rules."""
        return "Academic paper formatting guidelines with proper heading hierarchy."
    
    @pytest.mark.llm
    def test_ollama_health_check_success(self):
        """Test Ollama server health check when server is available."""
        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            with patch('app.pipeline.intelligence.reasoning_engine.ChatOllama'):
                engine = ReasoningEngine()
                assert engine.ollama_available == True
                assert engine.llm is not None
    
    @pytest.mark.llm
    def test_ollama_health_check_failure(self):
        """Test Ollama server health check when server is unavailable."""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = Exception("Connection refused")
            engine = ReasoningEngine()
            assert engine.ollama_available == False
            assert engine.llm is None
    
    @pytest.mark.llm
    def test_fallback_mechanism(self, sample_blocks, sample_rules):
        """Test rule-based fallback when Ollama unavailable."""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = Exception("Connection refused")
            engine = ReasoningEngine()
            
            result = engine.generate_instruction_set(sample_blocks, sample_rules)
            
            assert result["fallback"] == True
            assert "blocks" in result
            assert len(result["blocks"]) == len(sample_blocks)
            assert all("semantic_type" in block for block in result["blocks"])
            assert all("confidence" in block for block in result["blocks"])
    
    @pytest.mark.llm
    def test_json_validation_success(self):
        """Test JSON schema validation with valid data."""
        engine = ReasoningEngine()
        valid_data = {
            "blocks": [
                {
                    "block_id": "b1",
                    "semantic_type": "HEADING_1",
                    "confidence": 0.95
                }
            ]
        }
        assert engine._validate_json_schema(valid_data) == True
    
    @pytest.mark.llm
    def test_json_validation_failure(self):
        """Test JSON schema validation with invalid data."""
        engine = ReasoningEngine()
        
        # Missing blocks key
        assert engine._validate_json_schema({"error": "test"}) == False
        
        # Missing required fields
        invalid_data = {
            "blocks": [
                {"block_id": "b1"}  # Missing semantic_type and confidence
            ]
        }
        assert engine._validate_json_schema(invalid_data) == False
    
    @pytest.mark.llm
    def test_successful_reasoning(self, sample_blocks, sample_rules):
        """Test successful DeepSeek reasoning with valid response."""
        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            
            with patch.object(ReasoningEngine, '__init__', lambda x, **kwargs: None):
                engine = ReasoningEngine()
                engine.ollama_available = True
                engine.model = "deepseek-r1:8b"
                
                # Mock LLM response
                mock_llm = MagicMock()
                mock_response = MagicMock()
                mock_response.content = json.dumps({
                    "blocks": [
                        {
                            "block_id": "b1",
                            "semantic_type": "HEADING_1",
                            "canonical_section_name": "Introduction",
                            "confidence": 0.95
                        }
                    ]
                })
                mock_llm.invoke.return_value = mock_response
                engine.llm = mock_llm
                
                result = engine.generate_instruction_set(sample_blocks, sample_rules)
                
                assert result["fallback"] == False
                assert "latency" in result
                assert "model" in result
                assert result["model"] == "deepseek-r1:8b"
    
    @pytest.mark.llm
    def test_retry_logic(self, sample_blocks, sample_rules):
        """Test retry logic on transient failures."""
        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            
            with patch.object(ReasoningEngine, '__init__', lambda x, **kwargs: None):
                engine = ReasoningEngine()
                engine.ollama_available = True
                engine.model = "deepseek-r1:8b"
                
                # Mock LLM to fail twice, then succeed
                mock_llm = MagicMock()
                mock_llm.invoke.side_effect = [
                    Exception("Timeout"),
                    Exception("Timeout"),
                    MagicMock(content=json.dumps({
                        "blocks": [{
                            "block_id": "b1",
                            "semantic_type": "HEADING_1",
                            "confidence": 0.9
                        }]
                    }))
                ]
                engine.llm = mock_llm
                
                with patch('time.sleep'):  # Skip actual sleep
                    result = engine.generate_instruction_set(sample_blocks, sample_rules, max_retries=2)
                
                assert mock_llm.invoke.call_count == 3
                assert result["fallback"] == False
    
    @pytest.mark.llm
    def test_max_retries_exceeded(self, sample_blocks, sample_rules):
        """Test fallback after max retries exceeded."""
        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            
            with patch.object(ReasoningEngine, '__init__', lambda x, **kwargs: None):
                engine = ReasoningEngine()
                engine.ollama_available = True
                
                # Mock LLM to always fail
                mock_llm = MagicMock()
                mock_llm.invoke.side_effect = Exception("Persistent error")
                engine.llm = mock_llm
                
                with patch('time.sleep'):
                    result = engine.generate_instruction_set(sample_blocks, sample_rules, max_retries=2)
                
                # Should fall back to rule-based
                assert result["fallback"] == True
                assert "blocks" in result
    
    @pytest.mark.llm
    def test_timeout_configuration(self):
        """Test timeout parameter is properly set."""
        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            
            with patch('app.pipeline.intelligence.reasoning_engine.ChatOllama') as mock_ollama:
                engine = ReasoningEngine(timeout=45)
                
                # Verify ChatOllama was called with timeout
                mock_ollama.assert_called_once()
                call_kwargs = mock_ollama.call_args[1]
                assert call_kwargs['timeout'] == 45
    
    @pytest.mark.llm
    def test_rule_based_classification_logic(self, sample_blocks):
        """Test rule-based classification heuristics."""
        engine = ReasoningEngine()
        
        test_blocks = [
            {"block_id": "b1", "text": "Introduction:", "index": 0},
            {"block_id": "b2", "text": "Abstract: This paper...", "index": 1},
            {"block_id": "b3", "text": "References", "index": 2},
            {"block_id": "b4", "text": "This is a long body paragraph with lots of text.", "index": 3}
        ]
        
        result = engine._rule_based_fallback(test_blocks)
        
        assert result["blocks"][0]["semantic_type"] == "HEADING_1"  # Short with colon
        assert result["blocks"][1]["semantic_type"] == "ABSTRACT_BODY"  # Contains "abstract"
        assert result["blocks"][2]["semantic_type"] == "REFERENCE_ENTRY"  # Contains "reference"
        assert result["blocks"][3]["semantic_type"] == "BODY_TEXT"  # Default
        
        # All should have lower confidence
        assert all(block["confidence"] == 0.5 for block in result["blocks"])


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "llm"])
