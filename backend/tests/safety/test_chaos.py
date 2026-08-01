# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import unittest
from unittest.mock import MagicMock, patch
from app.pipeline.intelligence.reasoning_engine import ReasoningEngine

class TestSafetyChaos(unittest.TestCase):
    
    def setUp(self):
        self.engine = ReasoningEngine()
        
    def test_circuit_breaker_activates(self):
        """Verify circuit breaker opens after threshold failures."""
        print("\n🧪 STATUS: Testing Circuit Breaker Activation...")
        
        # When nvidia_client and ChatOllama are used, we need to mock their invoke/chat methods
        # to trigger a failure that will be caught by the circuit breaker.
        # Alternatively, mocking requests.post might not cover everything if it uses other libs.
        # Actually, let's mock generate_with_deepseek & generate_with_nvidia to fail
        with patch.object(self.engine, '_generate_with_nvidia', side_effect=Exception("NVIDIA API Error")):
            with patch.object(self.engine, '_generate_with_deepseek', side_effect=Exception("DeepSeek API Error")):
                with patch.object(self.engine, '_rule_based_fallback', side_effect=Exception("Rules Error")):
                    # 1. Fail 3 times
                    for i in range(3):
                        res = self.engine.generate_instruction_set([], "")
                        # The circuit breaker + guard will return the fallback dict
                        self.assertTrue(res.get("fallback"), f"Attempt {i}: Should indicate fallback")
                    
                # 2. Fourth call should trip circuit breaker safely 
                try:
                    res = self.engine.generate_instruction_set([], "")
                    self.assertTrue(res.get("fallback"), "Circuit breaker tripped should also return fallback")
                except Exception as e:
                    self.fail(f"Circuit breaker did not fail safely: {e}")

    def test_validator_suppresses_bad_json(self):
        """Verify validator guard catches malformed JSON from 'hallucinating' AI."""
        print("\n🧪 STATUS: Testing Validator Guard...")
        
        # Mock successful request but BAD response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "I am not JSON I am a pirate"} 
        
        with patch('requests.post', return_value=mock_response):
            # Should not crash
            result = self.engine._call_ollama("test")
            # _call_ollama is wrapped in @retry_guard, which re-raises eventually?
            # actually _call_ollama logic itself catches exceptions and returns None
            self.assertIsNone(result)

    def test_orchestrator_safe_execution(self):
        """Verify safe_execution context manager catches unforeseen crashes."""
        from app.pipeline.safety import safe_execution
        
        print("\n🧪 STATUS: Testing Orchestrator Safety Net...")
        crash_survived = False
        try:
            with safe_execution("Chaos Block"):
                raise ValueError("Random unexpected crash!")
            crash_survived = True
        except Exception:
            crash_survived = False
            
        self.assertTrue(crash_survived, "Safe execution block failed to suppress exception")

if __name__ == '__main__':
    unittest.main()
