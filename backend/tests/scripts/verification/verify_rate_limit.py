# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import sys
import uuid
from unittest.mock import MagicMock

# MOCK Dependencies to avoid heavy installs (Docling, etc.)
sys.modules["docling"] = MagicMock()
sys.modules["app.pipeline.services.docling_client"] = MagicMock()

# Mock Orchestrator to avoid instantiation issues
mock_orchestrator = MagicMock()
sys.modules["app.pipeline.orchestrator"] = mock_orchestrator

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def verify_rate_limit():
    print("Verifying Rate Limit (10 uploads/min)...")
    token = f"Bearer test_token_{uuid.uuid4()}"
    headers = {"Authorization": token}
    files = {'file': ('test.docx', b'test content', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
    
    # Send 10 requests
    for i in range(10):
        try:
            resp = client.post("/api/v1/documents/upload", files=files, headers=headers)
            print(f"Request {i+1}: Status {resp.status_code}")
            if resp.status_code == 429:
                print("❌ FAILED: Got 429 too early.")
                return False
        except Exception as e:
            print(f"❌ Error on request {i+1}: {e}")
            return False

    # Send 11th request
    resp = client.post("/api/v1/documents/upload", files=files, headers=headers)
    print(f"Request 11: Status {resp.status_code}")
    
    if resp.status_code == 429:
        print("✅ SUCCESS: Rate limit triggered on 11th request.")
        return True
    else:
        print(f"❌ FAILED: Expected 429, got {resp.status_code}")
        print(f"Response: {resp.text}")
        return False

if __name__ == "__main__":
    if verify_rate_limit():
        sys.exit(0)
    else:
        sys.exit(1)
