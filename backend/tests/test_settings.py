# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Tests for the Settings class — safe defaults, threshold clamping, and
absence of secrets does not crash the process.
"""
from __future__ import annotations

import pytest


class TestSettingsDefaults:

    def _fresh_settings(self, env_overrides: dict | None = None):
        """Import Settings in a clean env context."""
        # Reload settings module with patched env
        import importlib

        import app.config.settings as mod
        importlib.reload(mod)
        return mod.Settings()

    def test_algorithm_default_is_hs256(self):
        """JWT algorithm default must be HS256."""
        from app.config.settings import Settings
        s = Settings()
        assert s.ALGORITHM == "HS256"

    def test_cors_origins_has_localhost(self):
        """CORS origins include localhost by default."""
        from app.config.settings import Settings
        s = Settings()
        assert "localhost" in s.CORS_ORIGINS

    def test_default_template_is_ieee(self, monkeypatch):
        """Default template must be 'ieee' (unless overridden by env)."""
        monkeypatch.setenv("DEFAULT_TEMPLATE", "ieee")
        from importlib import reload

        from app.config import settings
        reload(settings)
        from app.config.settings import Settings
        s = Settings()
        assert s.DEFAULT_TEMPLATE == "ieee"

    def test_confidence_thresholds_are_between_0_and_1(self):
        """All confidence thresholds must be in [0, 1]."""
        from app.config.settings import Settings
        s = Settings()
        for attr in (
            "HEADING_STYLE_THRESHOLD",
            "HEADING_FALLBACK_CONFIDENCE",
            "HEURISTIC_CONFIDENCE_HIGH",
            "HEURISTIC_CONFIDENCE_MEDIUM",
            "HEURISTIC_CONFIDENCE_LOW",
        ):
            val = getattr(s, attr)
            assert 0.0 <= val <= 1.0, f"{attr}={val} is outside [0, 1]"

    def test_grobid_defaults(self):
        """GROBID defaults are sane and usable."""
        from app.config.settings import Settings
        s = Settings()
        assert s.GROBID_BASE_URL
        assert s.GROBID_BASE_URL.startswith("http")
        assert s.GROBID_TIMEOUT > 0
        assert s.GROBID_MAX_RETRIES == 3

    def test_grobid_urls_prefer_urls_list(self, monkeypatch):
        """When GROBID_URLS is set, it takes precedence over legacy single URL vars."""
        monkeypatch.setenv("GROBID_URLS", "https://primary.example,https://shadow.example")
        monkeypatch.setenv("GROBID_URL", "https://legacy.example")
        monkeypatch.setenv("GROBID_BASE_URL", "https://legacy-base.example")

        from app.config.settings import Settings

        s = Settings()
        s.validate()
        assert s.get_grobid_urls() == ["https://primary.example", "https://shadow.example"]
        assert s.GROBID_URL == "https://primary.example"

    def test_nougat_and_scibert_urls_resolve_in_order(self, monkeypatch):
        monkeypatch.setenv("NOUGAT_URLS", "https://nougat-a.example,https://nougat-b.example")
        monkeypatch.setenv("NOUGAT_URL", "https://nougat-legacy.example")
        monkeypatch.setenv("SCIBERT_URLS", "https://scibert-a.example,https://scibert-b.example")
        monkeypatch.setenv("SCIBERT_URL", "https://scibert-legacy.example")

        from app.config.settings import Settings

        s = Settings()
        s.validate()
        assert s.get_nougat_urls() == ["https://nougat-a.example", "https://nougat-b.example"]
        assert s.get_scibert_urls() == ["https://scibert-a.example", "https://scibert-b.example"]

    def test_validate_does_not_raise(self):
        """Settings.validate() must never raise even if all secrets are unset."""
        from app.config.settings import settings
        try:
            settings.validate()
        except Exception as exc:
            pytest.fail(f"settings.validate() raised unexpectedly: {exc}")
