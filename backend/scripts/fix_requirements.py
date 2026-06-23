# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI


import os

try:
    # Try reading as UTF-16 first (default for PowerShell redirect)
    with open('requirements.txt', 'r', encoding='utf-16') as f:
        lines = f.readlines()
except UnicodeError:
    # Fallback to UTF-8 if it wasn't UTF-16
    with open('requirements.txt', 'r', encoding='utf-8') as f:
        lines = f.readlines()

new_lines = []
langchain_added = False

for line in lines:
    line = line.strip()
    if not line:
        continue
    # Filter out all langchain related packages to replace them with strict new versions
    if line.lower().startswith('langchain') or line.lower().startswith('langgraph'):
        continue
    new_lines.append(line)

# Add the correct LangChain 0.3.x stack
new_lines.extend([
    "langchain==0.3.18",
    "langchain-community==0.3.18",
    "langchain-core==0.3.37",
    "langchain-ollama==0.2.3",
    "langchain-openai==0.3.6",
    "langchain-text-splitters==0.3.6",
    "langgraph==0.2.73" 
])

with open('requirements.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(new_lines))

print("Successfully cleaned requirements.txt")
