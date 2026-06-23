# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI


import sys
import os
import asyncio
from pprint import pformat

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.services.auth_service import AuthService
from app.config.settings import settings

class Logger:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "w", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()

    def flush(self):
        self.terminal.flush()
        self.log.flush()

    def close(self):
        self.log.close()

async def verify_auth_structure():
    sys.stdout = Logger("verify_result_internal.log")
    sys.stderr = sys.stdout # Capture errors too
    
    print(f"--- 🔐 Verifying Auth Response Structure ---")
    
    email = "structural_test_user_2@example.com"
    password = "TestPassword123!"
    
    print(f"1. Attempting Signup for {email}...")
    try:
        await AuthService.signup(email, password, "Test User", "Test Inst")
        print("   ✅ Signup call completed (or user exists).")
    except Exception as e:
        print(f"   ℹ️  Signup note: {e}")

    print(f"\n2. Attempting Login...")
    try:
        response = await AuthService.login(email, password)
        print(f"   ✅ Login successful!")
        print(f"   👉 Response Type: {type(response)}")
        
        # Check if it's a Pydantic model or object
        if hasattr(response, 'session'):
            print(f"   👉 Has .session attribute: Yes")
            print(f"   👉 Session Type: {type(response.session)}")
            # Try to see if session has access_token
            if response.session and hasattr(response.session, 'access_token'):
                 print(f"   👉 Session.access_token: Present")
            else:
                 print(f"   ❌ Session.access_token: MISSING")
        else:
            print(f"   ❌ Has .session attribute: NO")
            
        print(f"\n   👉 Full Response Dump:")
        try:
            # Try varying dumping methods
            if hasattr(response, 'model_dump'):
                print(pformat(response.model_dump()))
            elif hasattr(response, 'dict'):
                print(pformat(response.dict()))
            else:
                print(pformat(vars(response)))
        except:
            print(str(response))
            
    except Exception as e:
        print(f"   ❌ Login failed: {e}")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(verify_auth_structure())
