# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI


try:
    print("Trying to import langchain...")
    import langchain
    print(f"LangChain version: {langchain.__version__}")
    
    print("Trying to import AgentExecutor...")
    from langchain.agents import AgentExecutor
    print("SUCCESS: AgentExecutor imported!")
except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
