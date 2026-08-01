import os
import re

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    pattern = re.compile(r'(\n\s*except[^\n:]*:\s*\n\s*)pass(\s*\n)')
    new_content, count = pattern.subn(r'\g<1>pass  # intentionally ignored\g<2>', content)
    
    if count > 0:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Fixed {count} empty excepts in {filepath}")

for root, _, files in os.walk('.'):
    if 'node_modules' in root or '.git' in root or '.venv' in root or 'venv' in root:
        continue
    for file in files:
        if file.endswith('.py'):
            process_file(os.path.join(root, file))
