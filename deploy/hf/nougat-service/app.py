# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import os
from io import BytesIO
from typing import List

import fitz
import torch
from fastapi import FastAPI, File, HTTPException, UploadFile
from PIL import Image
from transformers import NougatProcessor, VisionEncoderDecoderModel

MODEL_NAME = os.getenv("NOUGAT_MODEL", "facebook/nougat-small")
MAX_PAGES = int(os.getenv("NOUGAT_MAX_PAGES", "30"))
MAX_TOKENS = int(os.getenv("NOUGAT_MAX_TOKENS", "4096"))

app = FastAPI(title="Scholarform Nougat Service", version="1.0.0")

device = "cuda" if torch.cuda.is_available() else "cpu"
processor = NougatProcessor.from_pretrained(MODEL_NAME)
model = VisionEncoderDecoderModel.from_pretrained(MODEL_NAME).to(device)
model.eval()


def _pdf_to_images(pdf_bytes: bytes) -> List[Image.Image]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages: List[Image.Image] = []
    page_count = min(doc.page_count, MAX_PAGES)
    for i in range(page_count):
        pix = doc[i].get_pixmap(dpi=200)
        pages.append(Image.frombytes("RGB", [pix.width, pix.height], pix.samples))
    doc.close()
    return pages


def _run_nougat(image: Image.Image) -> str:
    pixel_values = processor(image, return_tensors="pt").pixel_values.to(device)
    with torch.no_grad():
        outputs = model.generate(
            pixel_values,
            min_length=1,
            max_new_tokens=MAX_TOKENS,
            bad_words_ids=[[processor.tokenizer.unk_token_id]],
        )
    text = processor.batch_decode(outputs, skip_special_tokens=True)[0]
    return processor.post_process_generation(text, fix_markdown=True)


@app.get("/")
def root():
    return {"status": "ok", "service": "nougat", "model": MODEL_NAME, "device": device}


@app.get("/health")
def health():
    return {"status": "ok", "service": "nougat", "model": MODEL_NAME}


@app.post("/parse")
async def parse_pdf(file: UploadFile = File(...)):
    filename = (file.filename or "").lower()
    if not filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        pages = _pdf_to_images(pdf_bytes)
        if not pages:
            raise HTTPException(status_code=400, detail="No pages extracted from PDF")

        parts: List[str] = []
        for page in pages:
            page_text = _run_nougat(page).strip()
            if page_text:
                parts.append(page_text)

        markdown = "\n\n".join(parts).strip()
        return {
            "status": "ok",
            "service": "nougat",
            "model": MODEL_NAME,
            "page_count": len(pages),
            "markdown": markdown,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Nougat parse failed: {exc}") from exc
