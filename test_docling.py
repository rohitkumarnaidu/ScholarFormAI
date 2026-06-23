"""Quick Docling local test"""
import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from docling.document_converter import DocumentConverter
from importlib.metadata import version

print(f'Docling version: {version("docling")}')
converter = DocumentConverter()
print('Docling DocumentConverter ready')

with tempfile.NamedTemporaryFile(suffix='.txt', delete=False, mode='w') as f:
    f.write('This is a test document for Docling PDF conversion.')
    txt_path = f.name

try:
    result = converter.convert(txt_path)
    print('DOCLING LOCAL: WORKING')
    print(f'Pages: {len(result.pages)}')
finally:
    os.unlink(txt_path)
print('Done')
