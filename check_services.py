"""Verify all services connectivity"""
import sys, os, redis, requests, subprocess

# load .env from backend directory
from dotenv import load_dotenv
dotenv_path = os.path.join(os.path.dirname(__file__), 'backend', '.env')
load_dotenv(dotenv_path)

ok = True

# Redis
try:
    r = redis.Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
    assert r.ping(), 'Redis ping failed'
    r.set('test:hello', 'world')
    assert r.get('test:hello') == b'world'
    r.delete('test:hello')
    print('REDIS: OK (ping, set, get, delete)')
except Exception as e:
    print(f'REDIS: FAIL - {e}')
    ok = False

# Pandoc - check in default install location
import shutil
pandoc_path = shutil.which('pandoc') or os.path.expanduser('~\\AppData\\Local\\Pandoc\\pandoc.exe')
if not os.path.exists(pandoc_path):
    print('PANDOC: binary not found in PATH or default location')
    ok = False
else:
    try:
        result = subprocess.run([pandoc_path, '--version'], capture_output=True, text=True, timeout=10)
        first_line = result.stdout.split('\n')[0]
        print(f'PANDOC: {first_line}')
    except Exception as e:
        print(f'PANDOC: FAIL - {e}')
        ok = False

# GROBID
try:
    gurl = os.getenv('GROBID_URL') or os.getenv('GROBID_BASE_URL')
    r = requests.get(f'{gurl}/api/isalive', timeout=10)
    print(f'GROBID: {r.status_code} {r.text.strip()[:50]}')
except Exception as e:
    print(f'GROBID: FAIL - {e}')
    ok = False

# Supabase
try:
    surl = os.getenv('SUPABASE_URL')
    skey = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    r = requests.get(f'{surl}/rest/v1/profiles?select=count', timeout=10,
                     headers={'apikey': skey, 'Authorization': f'Bearer {skey}'})
    print(f'SUPABASE: {r.status_code} {r.text.strip()[:80]}')
except Exception as e:
    print(f'SUPABASE: FAIL - {e}')
    ok = False

# Docling local
try:
    from docling.document_converter import DocumentConverter
    from importlib.metadata import version as v
    print(f'DOCLING: local package v{v("docling")}, importable')
except Exception as e:
    print(f'DOCLING: FAIL - {e}')
    ok = False

print()
print('ALL SERVICES OK' if ok else 'SOME SERVICES FAILED')
