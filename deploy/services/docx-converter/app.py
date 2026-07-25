# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import Response

app = FastAPI(title="Scholarform DOCX Converter", version="1.0.0")


@app.get("/health")
def health_check() -> Dict[str, Any]:
    return {"status": "ok", "service": "docx-converter"}


@app.get("/")
def root() -> Dict[str, Any]:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    return {
        "status": "ok",
        "service": "docx-converter",
        "ready": bool(soffice),
        "engine": soffice,
    }


@app.post("/convert")
async def convert(file: UploadFile = File(...), to: str = Query(default="docx")):
    target_ext = to.strip().lower().lstrip(".")
    if target_ext not in {"docx", "pdf", "txt"}:
        raise HTTPException(status_code=400, detail="Unsupported target format")

    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise HTTPException(status_code=503, detail="LibreOffice is unavailable")

    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Empty file")

    original_name = Path(file.filename or "document").name
    input_suffix = Path(original_name).suffix or ".txt"

    with TemporaryDirectory() as tmp_dir:
        src = Path(tmp_dir) / f"input{input_suffix}"
        src.write_bytes(payload)

        cmd = [
            soffice,
            "--headless",
            "--convert-to",
            target_ext,
            "--outdir",
            tmp_dir,
            str(src),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if proc.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Conversion failed: {(proc.stderr or proc.stdout).strip()}",
            )

        candidates = list(Path(tmp_dir).glob(f"*.{target_ext}"))
        if not candidates:
            raise HTTPException(status_code=500, detail="No output file produced")

        output_path = candidates[0]
        out_name = f"{Path(original_name).stem}.{target_ext}"
        output_bytes = output_path.read_bytes()
        headers = {"Content-Disposition": f'attachment; filename="{out_name}"'}
        return Response(content=output_bytes, media_type="application/octet-stream", headers=headers)
