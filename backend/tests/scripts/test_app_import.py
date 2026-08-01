# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI


import sys
import traceback

try:
    print("Attempting to import app.main...")
    print("SUCCESS: App imported!")
except Exception:
    traceback.print_exc()
    sys.exit(1)
