# ScholarFormAI Python CLI Starter Kit

This starter kit provides a foundation for building your own internal CLI tools that wrap the ScholarFormAI API.

## Prerequisites

- Python 3.10+
- `pip install click requests pydantic rich`

## Usage

```bash
# Format a local docx file to IEEE format
python run.py format --input ./draft.docx --template IEEE --output ./final.pdf

# Analyze a document for hallucinated references
python run.py analyze --input ./draft.pdf
```

## Structure

- `cli/commands.py` - Click command definitions
- `cli/api.py` - ScholarFormAI API wrapper
- `cli/utils.py` - Helper functions for file I/O and Rich terminal formatting
