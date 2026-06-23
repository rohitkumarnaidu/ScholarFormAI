# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import asyncio
from pathlib import Path
from time import monotonic
from typing import Dict, List

import httpx

from app.config.settings import settings


TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"
CSL_SEARCH_URL = "https://api.citationstyles.org/styles"
ZOTERO_STYLE_URL = "https://www.zotero.org/styles/{slug}"

_search_cache: dict[str, tuple[float, List[Dict[str, str]]]] = {}
_style_cache: dict[str, tuple[float, Dict[str, str]]] = {}
_search_cache_lock: asyncio.Lock | None = None
_style_cache_lock: asyncio.Lock | None = None


def _search_cache_ttl_seconds() -> float:
    raw_ttl = getattr(settings, "CSL_SEARCH_CACHE_TTL_SECONDS", 300)
    try:
        ttl = float(raw_ttl)
    except (TypeError, ValueError):
        ttl = 300.0
    return max(0.0, ttl)


def _style_cache_ttl_seconds() -> float:
    raw_ttl = getattr(settings, "CSL_FETCH_CACHE_TTL_SECONDS", 1800)
    try:
        ttl = float(raw_ttl)
    except (TypeError, ValueError):
        ttl = 1800.0
    return max(0.0, ttl)


def _get_search_cache_lock() -> asyncio.Lock:
    global _search_cache_lock
    if _search_cache_lock is None:
        _search_cache_lock = asyncio.Lock()
    return _search_cache_lock


def _get_style_cache_lock() -> asyncio.Lock:
    global _style_cache_lock
    if _style_cache_lock is None:
        _style_cache_lock = asyncio.Lock()
    return _style_cache_lock


def _clone_style_rows(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    return [dict(row) for row in rows]


def _clone_style_payload(payload: Dict[str, str]) -> Dict[str, str]:
    return dict(payload)


def reset_csl_cache_for_tests() -> None:
    """Test helper to clear in-memory CSL caches."""
    global _search_cache_lock, _style_cache_lock
    _search_cache.clear()
    _style_cache.clear()
    _search_cache_lock = None
    _style_cache_lock = None


def _local_styles() -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for style_file in sorted(TEMPLATES_DIR.glob("*/styles.csl")):
        slug = style_file.parent.name.lower()
        rows.append({"slug": slug, "title": slug.upper(), "source": "local"})
    return rows


async def search_styles(query: str, limit: int = 20) -> List[Dict[str, str]]:
    query = (query or "").strip().lower()
    cache_key = f"{query}|{int(limit)}"
    ttl_seconds = _search_cache_ttl_seconds()
    now = monotonic()

    if ttl_seconds > 0:
        cached = _search_cache.get(cache_key)
        if cached and now < cached[0]:
            return _clone_style_rows(cached[1])

    async with _get_search_cache_lock():
        now = monotonic()
        if ttl_seconds > 0:
            cached = _search_cache.get(cache_key)
            if cached and now < cached[0]:
                return _clone_style_rows(cached[1])

        local = [row for row in _local_styles() if query in row["slug"] or query in row["title"].lower()]

        remote: List[Dict[str, str]] = []
        if query:
            try:
                async with httpx.AsyncClient(timeout=8) as client:
                    resp = await client.get(CSL_SEARCH_URL, params={"query": query, "limit": limit})
                    resp.raise_for_status()
                    payload = resp.json()
                if isinstance(payload, list):
                    for item in payload:
                        if not isinstance(item, dict):
                            continue
                        slug = str(item.get("name") or item.get("slug") or "").strip().lower()
                        if not slug:
                            continue
                        remote.append(
                            {
                                "slug": slug,
                                "title": str(item.get("title") or slug),
                                "source": "remote",
                            }
                        )
            except Exception:
                # Network access can be unavailable in local/dev environments; local fallback keeps API usable.
                remote = []

        combined: Dict[str, Dict[str, str]] = {}
        for row in local + remote:
            combined[row["slug"]] = row
        results = list(combined.values())[:limit]

        if ttl_seconds > 0:
            _search_cache[cache_key] = (now + ttl_seconds, _clone_style_rows(results))
        else:
            _search_cache.pop(cache_key, None)

        return _clone_style_rows(results)


async def fetch_style(slug: str) -> Dict[str, str]:
    style_slug = (slug or "").strip().lower()
    if not style_slug:
        raise ValueError("slug is required")

    ttl_seconds = _style_cache_ttl_seconds()
    now = monotonic()
    if ttl_seconds > 0:
        cached = _style_cache.get(style_slug)
        if cached and now < cached[0]:
            return _clone_style_payload(cached[1])

    async with _get_style_cache_lock():
        now = monotonic()
        if ttl_seconds > 0:
            cached = _style_cache.get(style_slug)
            if cached and now < cached[0]:
                return _clone_style_payload(cached[1])

        local_path = TEMPLATES_DIR / style_slug / "styles.csl"
        if local_path.exists():
            payload = {
                "slug": style_slug,
                "source": "local",
                "content": local_path.read_text(encoding="utf-8"),
            }
            if ttl_seconds > 0:
                _style_cache[style_slug] = (now + ttl_seconds, _clone_style_payload(payload))
            else:
                _style_cache.pop(style_slug, None)
            return _clone_style_payload(payload)

        url = ZOTERO_STYLE_URL.format(slug=style_slug)
        async with httpx.AsyncClient(timeout=12) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        payload = {"slug": style_slug, "source": "remote", "content": resp.text}
        if ttl_seconds > 0:
            _style_cache[style_slug] = (now + ttl_seconds, _clone_style_payload(payload))
        else:
            _style_cache.pop(style_slug, None)
        return _clone_style_payload(payload)
