# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Local OCR service using RapidOCR (ONNX Runtime).
Replaces the HF Space OCR service — runs directly in the backend process.
"""

import logging

logger = logging.getLogger(__name__)


class LocalOCRService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._engine = None
        return cls._instance

    def _get_engine(self):
        if self._engine is None:
            from rapidocr_onnxruntime import RapidOCR

            self._engine = RapidOCR()
        return self._engine

    async def ocr_image(self, image_bytes: bytes) -> list[dict]:
        """Run OCR on image bytes, return list of {text, confidence, bbox}"""
        engine = self._get_engine()
        import io

        import numpy as np
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes))
        img_array = np.array(img)
        result, elapse = engine(img_array)

        if result is None:
            return []

        items = []
        for box, text, confidence in result:
            items.append(
                {"text": text, "confidence": float(confidence), "bbox": box.tolist() if hasattr(box, "tolist") else box}
            )
        return items

    def is_available(self) -> bool:
        if self._engine is not None:
            return True
        try:
            import importlib.util

            return importlib.util.find_spec("rapidocr_onnxruntime") is not None
        except Exception:
            return False


local_ocr_service = LocalOCRService()
