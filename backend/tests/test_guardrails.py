# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import sys
import json
from app.pipeline.safety.llm_validator import guard_llm_output
from app.pipeline.intelligence.reasoning_engine import InstructionSetSchema

# Dummy LLM functional output that returns a JSON string instead of an object
@guard_llm_output(schema=InstructionSetSchema, error_return_value={"blocks": [], "fallback": True})
def dummy_llm_call():
    # Simulate a raw LLM text response
    raw_json = '''
    {
      "blocks": [
        {
          "block_id": "b1",
          "semantic_type": "HEADING_1",
          "confidence": 0.98
        }
      ]
    }
    '''
    return raw_json

if __name__ == "__main__":
    result = dummy_llm_call()
    print("GUARDRAILS OUTPUT:")
    print(json.dumps(result, indent=2))
    
    if "blocks" in result and len(result["blocks"]) > 0:
        print("\n✅ Guardrails Validation Passed!")
        sys.exit(0)
    else:
        print("\n❌ Guardrails Validation Failed!")
        sys.exit(1)
