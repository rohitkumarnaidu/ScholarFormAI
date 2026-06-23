# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import os
from typing import List

import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from transformers import AutoModelForSequenceClassification, AutoTokenizer

MODEL_NAME = os.getenv("SCIBERT_MODEL", "allenai/scibert_scivocab_uncased")
MAX_LENGTH = int(os.getenv("SCIBERT_MAX_LENGTH", "512"))

LABELS = [
    "HEADING",
    "ABSTRACT",
    "BODY",
    "REFERENCES",
    "FIGURE_CAPTION",
    "TABLE_CAPTION",
    "ACKNOWLEDGEMENTS",
    "EQUATION",
    "METHODOLOGY",
    "CONCLUSION",
    "AUTHOR_INFO",
    "TITLE",
]

app = FastAPI(title="Scholarform SciBERT Service", version="1.0.0")

device = "cuda" if torch.cuda.is_available() else "cpu"
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME,
    ignore_mismatched_sizes=True,
).to(device)
model.eval()


class PredictRequest(BaseModel):
    texts: List[str] = Field(default_factory=list)


@app.get("/")
def root():
    return {"status": "ok", "service": "scibert", "model": MODEL_NAME, "device": device}


@app.get("/health")
def health():
    return {"status": "ok", "service": "scibert", "model": MODEL_NAME}


@app.post("/predict")
def predict(payload: PredictRequest):
    texts = [t or "" for t in payload.texts]
    if not texts:
        raise HTTPException(status_code=422, detail="`texts` must contain at least one string")

    try:
        inputs = tokenizer(
            texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=MAX_LENGTH,
        )
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model(**inputs)
            probs = torch.softmax(outputs.logits, dim=1)
            confidences, label_idxs = torch.max(probs, dim=1)

        predictions = []
        for confidence, idx in zip(confidences, label_idxs):
            label_index = idx.item()
            label = LABELS[label_index] if label_index < len(LABELS) else "BODY"
            predictions.append({"type": label, "confidence": float(confidence.item())})

        return {
            "status": "ok",
            "service": "scibert",
            "model": MODEL_NAME,
            "predictions": predictions,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"SciBERT inference failed: {exc}") from exc
