# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import hashlib
import html
import json
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import yaml
import redis

from app.config.settings import settings

logger = logging.getLogger(__name__)

TEMPLATE_ROOT = Path(__file__).resolve().parent.parent / "templates"
CSS_CACHE_KEY_PREFIX = "preview:css:"
HTML_CACHE_KEY_PREFIX = "preview:html:"


@dataclass
class _CachedValue:
    expires_at: float
    value: dict


class PreviewRenderer:
    def __init__(self) -> None:
        self._redis = None
        self._redis_enabled = bool(settings.REDIS_ENABLED)
        self._redis_warning_logged = False
        self._local_cache: Dict[str, _CachedValue] = {}
        self._css_cache: Dict[str, str] = {}
        self._template_names = self._discover_templates()
        self._init_redis()

    def _init_redis(self) -> None:
        if not self._redis_enabled:
            logger.info("Preview renderer Redis disabled via REDIS_ENABLED=false.")
            self._redis = None
            return
        try:
            self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
            self._redis.ping()
        except Exception as exc:
            logger.warning("Preview renderer Redis unavailable (%s). Using in-memory cache.", exc)
            self._redis = None

    def _discover_templates(self) -> set[str]:
        if not TEMPLATE_ROOT.exists():
            return set()
        return {p.name.lower() for p in TEMPLATE_ROOT.iterdir() if p.is_dir()}

    def _normalize_template(self, template_name: str) -> str:
        normalized = (template_name or "").strip().lower().replace(" ", "_")
        if not normalized:
            normalized = settings.DEFAULT_TEMPLATE.lower().replace(" ", "_")
        return normalized

    def _render_cache_key(self, content: str, template_name: str) -> str:
        hasher = hashlib.sha256()
        hasher.update(template_name.encode("utf-8"))
        hasher.update(b":")
        hasher.update(content.encode("utf-8"))
        return f"{HTML_CACHE_KEY_PREFIX}{hasher.hexdigest()}"

    def _get_cached(self, key: str) -> Optional[dict]:
        if self._redis is not None:
            try:
                cached = self._redis.get(key)
                if cached:
                    return json.loads(cached)
            except Exception as exc:
                if not self._redis_warning_logged:
                    logger.warning("Preview cache read failed (%s). Falling back to memory.", exc)
                    self._redis_warning_logged = True
        cached_local = self._local_cache.get(key)
        if not cached_local:
            return None
        if cached_local.expires_at < time.time():
            self._local_cache.pop(key, None)
            return None
        return cached_local.value

    def _set_cached(self, key: str, value: dict, ttl: int) -> None:
        if self._redis is not None:
            try:
                self._redis.setex(key, ttl, json.dumps(value))
                return
            except Exception as exc:
                if not self._redis_warning_logged:
                    logger.warning("Preview cache write failed (%s). Falling back to memory.", exc)
                    self._redis_warning_logged = True
        self._local_cache[key] = _CachedValue(expires_at=time.time() + ttl, value=value)

    def _load_contract(self, template_dir: Path) -> dict:
        contract_path = template_dir / "contract.yaml"
        if not contract_path.exists():
            return {}
        try:
            return yaml.safe_load(contract_path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            logger.warning("Failed to load contract %s: %s", contract_path, exc)
            return {}

    def _build_fallback_css(self, template_name: str, contract: dict) -> str:
        layout = contract.get("layout") or {}
        margins = layout.get("margins") or {}
        line_spacing = float(layout.get("line_spacing") or 1.4)
        page_size = str(layout.get("page_size") or "Letter").lower()
        page_width = 8.5
        if page_size == "a4":
            page_width = 8.27
        top = margins.get("top", 1.0)
        right = margins.get("right", 1.0)
        bottom = margins.get("bottom", 1.0)
        left = margins.get("left", 1.0)
        font_family = "Times New Roman, serif"
        if template_name in {"modern_blue", "modern_gold", "modern_red", "portfolio", "resume"}:
            font_family = "Helvetica, Arial, sans-serif"
        return f"""
        :root {{
          --doc-line-height: {line_spacing};
        }}
        body {{
          margin: 0;
          padding: 24px;
          background: #f4f6fb;
          color: #111111;
        }}
        .preview-page {{
          background: #ffffff;
          width: min(100%, {page_width}in);
          margin: 0 auto;
          padding: {top}in {right}in {bottom}in {left}in;
          box-shadow: 0 10px 30px rgba(16, 24, 40, 0.08);
          border-radius: 6px;
          font-family: {font_family};
          font-size: 12pt;
          line-height: var(--doc-line-height);
        }}
        .doc-title {{
          text-align: center;
          font-size: 20pt;
          font-weight: 700;
          margin: 0 0 16pt 0;
        }}
        .doc-heading {{
          font-size: 14pt;
          font-weight: 700;
          margin: 18pt 0 8pt 0;
        }}
        .doc-subheading {{
          font-size: 12.5pt;
          font-weight: 700;
          margin: 14pt 0 6pt 0;
        }}
        .doc-paragraph {{
          margin: 0 0 10pt 0;
          text-align: justify;
        }}
        .doc-caption {{
          font-size: 10pt;
          font-style: italic;
          margin: 6pt 0 10pt 0;
        }}
        .doc-list {{
          margin: 0 0 10pt 18pt;
          padding: 0;
        }}
        .doc-list li {{
          margin: 0 0 4pt 0;
        }}
        .doc-abstract-heading {{
          text-transform: uppercase;
          letter-spacing: 0.08em;
        }}
        .doc-empty {{
          color: #667085;
          font-style: italic;
        }}
        @media (max-width: 860px) {{
          body {{
            padding: 12px;
          }}
          .preview-page {{
            padding: 0.75in 0.75in;
          }}
        }}
        """

    def _load_template_css(self, template_name: str) -> str:
        template_dir = TEMPLATE_ROOT / template_name
        css_candidates = [
            template_dir / "preview.css",
            template_dir / "styles.css",
            template_dir / "style.css",
            template_dir / "template.css",
        ]
        for path in css_candidates:
            if path.exists():
                try:
                    return path.read_text(encoding="utf-8")
                except Exception as exc:
                    logger.warning("Failed to read CSS file %s: %s", path, exc)
                    continue
        contract = self._load_contract(template_dir)
        return self._build_fallback_css(template_name, contract)

    def _get_template_css(self, template_name: str, warnings: List[str]) -> str:
        cache_key = f"{CSS_CACHE_KEY_PREFIX}{template_name}"
        if template_name in self._css_cache:
            return self._css_cache[template_name]
        if self._redis is not None:
            try:
                cached_css = self._redis.get(cache_key)
                if cached_css:
                    self._css_cache[template_name] = cached_css
                    return cached_css
            except Exception as exc:
                logger.warning("Redis cache get failed for CSS %s: %s", template_name, exc)
                pass
        if template_name not in self._template_names:
            warnings.append(f"unknown_template:{template_name}")
        css = self._load_template_css(template_name)
        self._css_cache[template_name] = css
        if self._redis is not None:
            try:
                self._redis.setex(cache_key, 3600, css)
            except Exception as exc:
                logger.warning("Redis cache set failed for CSS %s: %s", template_name, exc)
                pass
        return css

    def _split_blocks(self, content: str) -> List[dict]:
        lines = content.replace("\r\n", "\n").split("\n")
        raw_blocks: List[dict] = []
        current: List[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                if current:
                    raw_blocks.append({"raw_type": "paragraph", "text": " ".join(current)})
                    current = []
                continue
            if self._is_list_item(stripped):
                if current:
                    raw_blocks.append({"raw_type": "paragraph", "text": " ".join(current)})
                    current = []
                raw_blocks.append({"raw_type": "list_item", "text": self._strip_list_marker(stripped)})
                continue
            current.append(stripped)
        if current:
            raw_blocks.append({"raw_type": "paragraph", "text": " ".join(current)})
        return raw_blocks

    def _is_list_item(self, text: str) -> bool:
        return bool(re.match(r"^([-*]|\d+[.)])\s+", text))

    def _strip_list_marker(self, text: str) -> str:
        return re.sub(r"^([-*]|\d+[.)])\s+", "", text).strip()

    def _is_caption(self, text: str) -> bool:
        return bool(re.match(r"^(figure|fig\.|table)\s+\d+[:\s-]", text, re.IGNORECASE))

    def _is_heading(self, text: str) -> bool:
        if re.match(r"^#{1,6}\s+", text):
            return True
        if re.match(r"^\d+(?:\.\d+)*\s+\S+", text):
            return True
        letters_only = re.sub(r"[^A-Za-z]", "", text)
        return len(letters_only) >= 4 and text.isupper() and len(text) <= 80

    def _heading_level(self, text: str) -> int:
        hash_match = re.match(r"^(#{1,6})\s+", text)
        if hash_match:
            return min(4, max(2, len(hash_match.group(1))))
        numeric_match = re.match(r"^(\d+(?:\.\d+)*)\s+", text)
        if numeric_match:
            depth = numeric_match.group(1).count(".")
            return min(4, 2 + depth)
        return 2

    def _strip_heading_marker(self, text: str) -> str:
        text = re.sub(r"^#{1,6}\s+", "", text)
        text = re.sub(r"^\d+(?:\.\d+)*\s+", "", text)
        return text.strip()

    def _is_title(self, text: str, index: int) -> bool:
        if index != 0:
            return False
        if len(text) > 150:
            return False
        if text.endswith("."):
            return False
        return True

    def _classify_blocks(self, raw_blocks: List[dict]) -> List[dict]:
        classified: List[dict] = []
        abstract_next = False
        for idx, block in enumerate(raw_blocks):
            text = block.get("text", "").strip()
            if not text:
                continue
            if block.get("raw_type") == "list_item":
                classified.append({"type": "list_item", "text": text})
                continue
            if text.lower() == "abstract":
                classified.append({"type": "abstract_heading", "text": text})
                abstract_next = True
                continue
            if abstract_next:
                classified.append({"type": "abstract_body", "text": text})
                abstract_next = False
                continue
            if self._is_title(text, idx):
                classified.append({"type": "title", "text": text})
                continue
            if self._is_caption(text):
                classified.append({"type": "caption", "text": text})
                continue
            if self._is_heading(text):
                level = self._heading_level(text)
                classified.append({"type": "heading", "text": self._strip_heading_marker(text), "level": level})
                continue
            classified.append({"type": "paragraph", "text": text})
        return classified

    def _render_blocks(self, blocks: List[dict]) -> str:
        parts: List[str] = []
        in_list = False
        for block in blocks:
            block_type = block.get("type")
            text = html.escape(block.get("text", ""))
            if block_type == "list_item":
                if not in_list:
                    parts.append('<ul class="doc-list">')
                    in_list = True
                parts.append(f"<li>{text}</li>")
                continue
            if in_list:
                parts.append("</ul>")
                in_list = False
            if block_type == "title":
                parts.append(f'<h1 class="doc-title">{text}</h1>')
            elif block_type == "heading":
                level = int(block.get("level") or 2)
                if level >= 3:
                    parts.append(f'<h3 class="doc-subheading">{text}</h3>')
                else:
                    parts.append(f'<h2 class="doc-heading">{text}</h2>')
            elif block_type == "abstract_heading":
                parts.append(f'<h2 class="doc-heading doc-abstract-heading">{text}</h2>')
            elif block_type == "abstract_body":
                parts.append(f'<p class="doc-paragraph doc-abstract-body">{text}</p>')
            elif block_type == "caption":
                parts.append(f'<p class="doc-caption">{text}</p>')
            else:
                parts.append(f'<p class="doc-paragraph">{text}</p>')
        if in_list:
            parts.append("</ul>")
        return "\n".join(parts)

    def render_preview(self, content: str, template_name: str) -> dict:
        start = time.perf_counter()
        warnings: List[str] = []
        requested_template = self._normalize_template(template_name)
        normalized_template = requested_template
        if normalized_template not in self._template_names:
            fallback_template = self._normalize_template(settings.DEFAULT_TEMPLATE)
            if fallback_template in self._template_names:
                warnings.append(f"unknown_template:{normalized_template}")
                normalized_template = fallback_template
        cache_key = self._render_cache_key(content, requested_template)
        cached = self._get_cached(cache_key)
        if cached:
            latency_ms = (time.perf_counter() - start) * 1000.0
            cached_response = dict(cached)
            cached_response["latency_ms"] = latency_ms
            return cached_response
        if not content.strip():
            warnings.append("empty_content")
        raw_blocks = self._split_blocks(content)
        blocks = self._classify_blocks(raw_blocks)
        body_html = self._render_blocks(blocks)
        if not body_html:
            body_html = '<p class="doc-paragraph doc-empty">Start typing to see the preview.</p>'
        css = self._get_template_css(normalized_template, warnings)
        html_out = (
            "<!doctype html>"
            "<html>"
            "<head>"
            '<meta charset="utf-8" />'
            f"<style>{css}</style>"
            "</head>"
            "<body>"
            f'<div class="preview-page template-{normalized_template}">'
            f"{body_html}"
            "</div>"
            "</body>"
            "</html>"
        )
        result = {"html": html_out, "latency_ms": 0.0, "warnings": warnings}
        self._set_cached(cache_key, {"html": html_out, "warnings": warnings}, ttl=60)
        result["latency_ms"] = (time.perf_counter() - start) * 1000.0
        return result

    def preload_template_css(self) -> None:
        for template_name in sorted(self._template_names):
            warnings: List[str] = []
            css = self._get_template_css(template_name, warnings)
            if css and template_name not in self._css_cache:
                self._css_cache[template_name] = css


preview_renderer = PreviewRenderer()


def preload_template_css() -> None:
    preview_renderer.preload_template_css()
