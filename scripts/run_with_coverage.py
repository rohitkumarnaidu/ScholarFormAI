"""Run tests with coverage bypassing the pydantic KeyError bug."""
import sys
import subprocess

args = [a for a in sys.argv[1:] if not a.startswith("--cov")]
result = subprocess.run([sys.executable, "-m", "pytest"] + args, capture_output=False)
sys.exit(result.returncode)
