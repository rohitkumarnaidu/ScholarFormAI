# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import atheris
import sys

def fuzz(data):
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return
    if not text.strip():
        return
    from app.pipeline.formatting.formatter import clean_title
    clean_title(text)

def TestOneInput(data):
    fuzz(data)

if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
