# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict

from fastapi import FastAPI, File, HTTPException, UploadFile

app = FastAPI(title="Scholarform Docling Service", version="1.0.0")

_converter = None
_converter_error = None

try:
    from docling.document_converter import DocumentConverter

    _converter = DocumentConverter()
except Exception as exc:  # pragma: no cover - startup probe visibility
    _converter_error = str(exc)


@app.get("/")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "service": "docling",
        "ready": _converter is not None,
        "error": _converter_error,
    }


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)) -> Dict[str, Any]:
    if _converter is None:
        raise HTTPException(status_code=503, detail=f"Docling unavailable: {_converter_error}")

    suffix = Path(file.filename or "document.pdf").suffix or ".pdf"
    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Empty file")

    with NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(payload)
        tmp_path = tmp.name

    try:
        result = _converter.convert(tmp_path)
        doc = result.document

        if hasattr(doc, "export_to_markdown"):
            text = doc.export_to_markdown()
        else:
            text = "\n".join(
                item.text for item in getattr(doc, "texts", []) if getattr(item, "text", None)
            )

        return {
            "status": "ok",
            "service": "docling",
            "text": text,
            "text_length": len(text),
        }
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

