# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Nougat parser with remote-first execution.

Behavior:
1) If NOUGAT_URL/NOUGAT_URLS are configured, try remote Nougat endpoints first.
2) If remote fails and local dependencies are available, fall back to local Nougat.
3) If neither path is available, return an empty document with an error stage.
"""

from __future__ import annotations

import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from requests import RequestException

from app.config.settings import settings
from app.models import (
    Block,
    BlockType,
    DocumentMetadata,
    PipelineDocument as Document,
    TextStyle,
)
from app.pipeline.parsing.base_parser import BaseParser
from app.utils.id_generator import generate_block_id

logger = logging.getLogger(__name__)

# Optional local dependencies for Nougat model execution.
NOUGAT_AVAILABLE = False
_load_error: Optional[str] = None
try:
    import pypdf  # noqa: F401
    import torch
    from PIL import Image
    from transformers import NougatProcessor, VisionEncoderDecoderModel

    NOUGAT_AVAILABLE = True
except ImportError as exc:  # pragma: no cover - environment dependent
    _load_error = str(exc)
    logger.info(
        "Nougat local dependencies unavailable (%s). "
        "Remote Nougat can still be used when configured.",
        exc,
    )


PRIMARY_MODEL = "facebook/nougat-base"
FALLBACK_MODEL = "facebook/nougat-small"
MIN_RAM_GB = 4


def _check_available_ram_gb() -> float:
    """Return available system RAM in GB, or 0.0 on failure."""
    try:
        import psutil

        return psutil.virtual_memory().available / (1024 ** 3)
    except Exception:
        return 0.0


def _pdf_to_images(file_path: str) -> List["Image.Image"]:
    """
    Convert PDF pages to PIL images.
    Tries PyMuPDF first, then pdf2image.
    """
    images: List["Image.Image"] = []

    try:
        import fitz

        pdf_doc = fitz.open(file_path)
        for page in pdf_doc:
            pix = page.get_pixmap(dpi=200)
            images.append(Image.frombytes("RGB", [pix.width, pix.height], pix.samples))
        pdf_doc.close()
        return images
    except ImportError:
        pass

    try:
        from pdf2image import convert_from_path

        return convert_from_path(file_path, dpi=200)
    except ImportError:
        pass

    raise RuntimeError(
        "Cannot convert PDF to images. Install PyMuPDF or pdf2image for local Nougat."
    )


def _classify_nougat_line(line: str) -> BlockType:
    stripped = line.strip()
    if not stripped:
        return BlockType.UNKNOWN

    if stripped.startswith("### "):
        return BlockType.HEADING_3
    if stripped.startswith("## "):
        return BlockType.HEADING_2
    if stripped.startswith("# "):
        return BlockType.HEADING_1

    if stripped.lower().startswith("abstract"):
        return BlockType.ABSTRACT

    if stripped.lower() in ("references", "bibliography"):
        return BlockType.HEADING_1

    if stripped.startswith("- ") or stripped.startswith("* ") or re.match(r"^\d+\.\s", stripped):
        return BlockType.LIST_ITEM

    if "|" in stripped and stripped.count("|") >= 2:
        return BlockType.UNKNOWN

    return BlockType.BODY


class NougatParser(BaseParser):
    """Academic PDF parser backed by Nougat (remote-first, local-fallback)."""

    TRANSIENT_HTTP_STATUSES = {408, 425, 429, 500, 502, 503, 504, 520, 522, 524}
    LAST_GOOD_ENDPOINT_TTL_SECONDS = 300.0

    def __init__(self):
        configured_urls = list(getattr(settings, "get_nougat_urls", lambda: [])())
        if not configured_urls:
            fallback_url = getattr(settings, "NOUGAT_URL", None)
            if fallback_url:
                configured_urls = [str(fallback_url).rstrip("/")]

        self.remote_base_urls = [url.rstrip("/") for url in configured_urls if str(url).strip()]
        self.remote_parse_paths = ["/parse", "/api/parse"]
        self.remote_timeout = max(
            10,
            int(getattr(settings, "PIPELINE_DOCLING_TIMEOUT_SECONDS", 25)),
        )
        self.remote_max_retries = max(1, int(getattr(settings, "GROBID_MAX_RETRIES", 3)))
        self._last_good_remote_url = self.remote_base_urls[0] if self.remote_base_urls else None
        self._last_good_remote_at = time.monotonic()

        self.model = None
        self.processor = None
        self.device = None
        self.active_model_name = ""
        self.block_counter = 0
        self._model_loaded = False

        # Local Nougat is optional if remote is configured.
        if not NOUGAT_AVAILABLE and not self.remote_base_urls:
            raise ImportError(
                f"Nougat dependencies unavailable: {_load_error}. "
                "Either install local Nougat deps or configure NOUGAT_URLS."
            )

    def supports_format(self, file_extension: str) -> bool:
        return file_extension.lower() == ".pdf"

    def _ordered_remote_urls(self) -> List[str]:
        ordered = list(self.remote_base_urls)
        if (
            self._last_good_remote_url
            and self._last_good_remote_url in ordered
            and (time.monotonic() - self._last_good_remote_at) <= self.LAST_GOOD_ENDPOINT_TTL_SECONDS
        ):
            ordered.remove(self._last_good_remote_url)
            ordered.insert(0, self._last_good_remote_url)
        return ordered

    def _mark_last_good_remote_url(self, base_url: str, *, reason: str) -> None:
        previous = self._last_good_remote_url
        self._last_good_remote_url = base_url
        self._last_good_remote_at = time.monotonic()
        if previous and previous != base_url:
            logger.warning(
                "Nougat failover switch: %s -> %s (reason=%s)",
                previous,
                base_url,
                reason,
            )

    def _retry_backoff_seconds(self, attempt: int) -> float:
        return min(float(2 ** max(0, attempt - 1)), 8.0)

    def _new_document(self, file_path: str, document_id: str) -> Document:
        now = datetime.now(timezone.utc)
        document = Document(
            document_id=str(document_id),
            original_filename=Path(file_path).name,
            source_path=file_path,
            created_at=now,
            updated_at=now,
        )
        document.metadata = DocumentMetadata()
        return document

    def _extract_remote_text(self, payload: Any) -> str:
        if isinstance(payload, dict):
            for key in ("markdown", "text", "content", "result"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value
        if isinstance(payload, str):
            return payload
        return ""

    def _parse_via_remote(self, file_path: str, document_id: str) -> Optional[Document]:
        if not self.remote_base_urls:
            return None

        ordered_urls = self._ordered_remote_urls()
        for endpoint_index, base_url in enumerate(ordered_urls, start=1):
            for path in self.remote_parse_paths:
                endpoint = f"{base_url.rstrip('/')}{path}"
                for attempt in range(1, self.remote_max_retries + 1):
                    try:
                        with open(file_path, "rb") as fh:
                            files = {"file": (Path(file_path).name, fh, "application/pdf")}
                            response = requests.post(
                                endpoint,
                                files=files,
                                timeout=(5.0, float(self.remote_timeout)),
                            )

                        if response.status_code != 200:
                            logger.warning(
                                "Nougat remote call failed: endpoint=%s status=%s attempt=%s/%s",
                                endpoint,
                                response.status_code,
                                attempt,
                                self.remote_max_retries,
                            )
                            if (
                                response.status_code in self.TRANSIENT_HTTP_STATUSES
                                and attempt < self.remote_max_retries
                            ):
                                time.sleep(self._retry_backoff_seconds(attempt))
                                continue
                            break

                        remote_payload: Any
                        try:
                            remote_payload = response.json()
                        except ValueError:
                            remote_payload = response.text

                        extracted_text = self._extract_remote_text(remote_payload).strip()
                        if not extracted_text:
                            logger.warning(
                                "Nougat remote returned empty payload: endpoint=%s attempt=%s/%s",
                                endpoint,
                                attempt,
                                self.remote_max_retries,
                            )
                            if attempt < self.remote_max_retries:
                                time.sleep(self._retry_backoff_seconds(attempt))
                                continue
                            break

                        blocks = self._parse_nougat_output(extracted_text)
                        document = self._new_document(file_path, document_id)
                        document.blocks = blocks
                        document.figures = []
                        document.add_processing_stage(
                            stage_name="parsing",
                            status="success",
                            message=(
                                f"Parsed PDF with remote Nougat endpoint {endpoint}: "
                                f"{len(blocks)} blocks"
                            ),
                        )
                        document.metadata.ai_hints = document.metadata.ai_hints or {}
                        document.metadata.ai_hints["parser"] = "nougat_remote"
                        document.metadata.ai_hints["nougat_endpoint"] = endpoint
                        self._mark_last_good_remote_url(base_url, reason="parse")
                        return document
                    except RequestException as exc:
                        logger.warning(
                            "Nougat remote request error: endpoint=%s attempt=%s/%s error=%s",
                            endpoint,
                            attempt,
                            self.remote_max_retries,
                            exc,
                        )
                        if attempt < self.remote_max_retries:
                            time.sleep(self._retry_backoff_seconds(attempt))
                            continue
                        break
                    except Exception as exc:
                        logger.warning(
                            "Nougat remote parsing exception: endpoint=%s attempt=%s/%s error=%s",
                            endpoint,
                            attempt,
                            self.remote_max_retries,
                            exc,
                        )
                        if attempt < self.remote_max_retries:
                            time.sleep(min(float(attempt), 2.0))
                            continue
                        break

            if endpoint_index < len(ordered_urls):
                logger.warning(
                    "Nougat failover: moving to next endpoint (from=%s to=%s)",
                    base_url,
                    ordered_urls[endpoint_index],
                )
        return None

    def _ensure_model_loaded(self) -> None:
        if self._model_loaded:
            return

        if not NOUGAT_AVAILABLE:
            raise RuntimeError(
                "Local Nougat dependencies unavailable and remote parsing failed."
            )

        from app.services.model_store import model_store

        if model_store.is_loaded("nougat_model") and model_store.is_loaded("nougat_processor"):
            self.model = model_store.get_model("nougat_model")
            self.processor = model_store.get_model("nougat_processor")
            self.device = next(self.model.parameters()).device
            self.active_model_name = "cached"
            self._model_loaded = True
            logger.info("NougatParser: reusing cached local model from ModelStore.")
            return

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        available_ram = _check_available_ram_gb()
        preferred = PRIMARY_MODEL if available_ram >= MIN_RAM_GB else FALLBACK_MODEL

        for model_name in [preferred, FALLBACK_MODEL]:
            try:
                logger.info("NougatParser: loading local model '%s'...", model_name)
                self.processor = NougatProcessor.from_pretrained(model_name)  # nosec
                self.model = VisionEncoderDecoderModel.from_pretrained(model_name)  # nosec
                self.model.to(self.device)
                self.model.eval()
                self.active_model_name = model_name

                model_store.set_model("nougat_model", self.model)
                model_store.set_model("nougat_processor", self.processor)
                self._model_loaded = True
                logger.info("NougatParser: local model '%s' loaded on %s.", model_name, self.device)
                return
            except Exception as exc:  # pragma: no cover - runtime dependent
                logger.warning("NougatParser: failed to load local model '%s': %s", model_name, exc)
                if model_name == FALLBACK_MODEL:
                    raise RuntimeError(f"NougatParser: unable to load local Nougat model: {exc}") from exc

    def _process_page(self, image: "Image.Image") -> str:
        pixel_values = self.processor(image, return_tensors="pt").pixel_values
        pixel_values = pixel_values.to(self.device)

        with torch.no_grad():
            outputs = self.model.generate(
                pixel_values,
                min_length=1,
                max_new_tokens=4096,
                bad_words_ids=[[self.processor.tokenizer.unk_token_id]],
            )

        page_text = self.processor.batch_decode(outputs, skip_special_tokens=True)[0]
        page_text = self.processor.post_process_generation(page_text, fix_markdown=True)
        return page_text

    def _parse_local(self, file_path: str, document_id: str) -> Document:
        self._ensure_model_loaded()
        self.block_counter = 0

        document = self._new_document(file_path, document_id)

        logger.info("NougatParser: converting PDF to images for local inference...")
        page_images = _pdf_to_images(file_path)
        logger.info("NougatParser: processing %d pages via local Nougat...", len(page_images))

        all_text_parts: List[str] = []
        for page_num, image in enumerate(page_images):
            try:
                page_text = self._process_page(image)
                if page_text:
                    all_text_parts.append(page_text)
            except Exception as exc:
                logger.warning("NougatParser: local page %d failed: %s", page_num + 1, exc)

        full_text = "\n\n".join(all_text_parts)
        blocks = self._parse_nougat_output(full_text)
        document.blocks = blocks
        document.figures = []
        document.add_processing_stage(
            stage_name="parsing",
            status="success",
            message=(
                f"Parsed PDF with local Nougat ({self.active_model_name}): "
                f"{len(blocks)} blocks from {len(page_images)} pages"
            ),
        )
        document.metadata.ai_hints = document.metadata.ai_hints or {}
        document.metadata.ai_hints["parser"] = "nougat_local"
        document.metadata.ai_hints["nougat_model"] = self.active_model_name
        return document

    def parse(self, file_path: str, document_id: str) -> Document:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        remote_document = self._parse_via_remote(file_path, document_id)
        if remote_document is not None:
            return remote_document

        if NOUGAT_AVAILABLE:
            return self._parse_local(file_path, document_id)

        document = self._new_document(file_path, document_id)
        document.blocks = []
        document.figures = []
        document.add_processing_stage(
            stage_name="parsing",
            status="error",
            message=(
                "Nougat parsing unavailable: remote endpoints failed and local dependencies are missing."
            ),
        )
        document.metadata.ai_hints = document.metadata.ai_hints or {}
        document.metadata.ai_hints["parser"] = "nougat_unavailable"
        return document

    def _parse_nougat_output(self, text: str) -> List[Block]:
        blocks: List[Block] = []
        if not text:
            return blocks

        raw_blocks = re.split(r"\n{2,}", text)
        for raw in raw_blocks:
            raw = raw.strip()
            if not raw:
                continue

            block_type = _classify_nougat_line(raw)
            clean_text = raw
            heading_level = 0
            if raw.startswith("### "):
                clean_text = raw[4:]
                heading_level = 3
            elif raw.startswith("## "):
                clean_text = raw[3:]
                heading_level = 2
            elif raw.startswith("# "):
                clean_text = raw[2:]
                heading_level = 1

            block_id = generate_block_id(self.block_counter)
            self.block_counter += 1
            style = TextStyle(bold=(heading_level > 0))
            block = Block(
                block_id=block_id,
                text=clean_text,
                index=self.block_counter * 100,
                block_type=block_type,
                style=style,
            )

            if heading_level > 0:
                block.metadata["heading_level"] = heading_level
                block.metadata["potential_heading"] = True
            if "\\[" in raw or "$$" in raw or "\\begin{" in raw:
                block.metadata["has_equation"] = True
            if "|" in raw and raw.count("|") >= 2:
                block.metadata["is_table"] = True

            block.metadata["parser"] = "nougat"
            blocks.append(block)

        return blocks

