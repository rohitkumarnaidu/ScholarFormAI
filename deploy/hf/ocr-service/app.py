# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import io
from typing import Any, Dict, List

import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from PIL import Image

app = FastAPI(title="Scholarform OCR Service", version="1.0.0")

_engine = None
_engine_error = None

try:
    from rapidocr_onnxruntime import RapidOCR

    _engine = RapidOCR()
except Exception as exc:  # pragma: no cover - startup visibility
    _engine_error = str(exc)


@app.get("/")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "service": "ocr",
        "ready": _engine is not None,
        "error": _engine_error,
    }


@app.post("/ocr")
async def ocr(file: UploadFile = File(...)) -> Dict[str, Any]:
    if _engine is None:
        raise HTTPException(status_code=503, detail=f"OCR unavailable: {_engine_error}")

    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        image = Image.open(io.BytesIO(payload)).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unsupported image payload: {exc}") from exc

    result, _ = _engine(np.array(image))
    lines: List[str] = []
    if result:
        for item in result:
            try:
                lines.append(item[1])
            except Exception:
                continue

    text = "\n".join(lines)
    return {
        "status": "ok",
        "service": "ocr",
        "text": text,
        "lines": lines,
        "line_count": len(lines),
    }

