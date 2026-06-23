# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import atheris
import sys
import json

def fuzz(data):
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return
    if not isinstance(obj, dict):
        return
    _ = {str(k): str(v) for k, v in obj.items()}

def TestOneInput(data):
    fuzz(data)

if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
