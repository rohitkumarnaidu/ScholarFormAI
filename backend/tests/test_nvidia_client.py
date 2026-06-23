# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Tests for NvidiaClient — focus on no-API-key degraded mode.
"""
from __future__ import annotations

import os
import pytest
from unittest.mock import patch, MagicMock

from app.services.nvidia_client import NvidiaClient, get_nvidia_client


class TestNvidiaClientNoKey:
    """Behaviour when NVIDIA_API_KEY is absent."""

    def test_chat_returns_empty_string_without_key(self):
        """chat() must return '' and not raise when no API key is set."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NVIDIA_API_KEY", None)
            client = NvidiaClient()
        result = client.chat([{"role": "user", "content": "ping"}])
        assert result == "", f"Expected empty string, got {result!r}"

    def test_analyze_document_structure_without_key(self):
        """analyze_document_structure() returns dict with 'analysis' key (empty)."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NVIDIA_API_KEY", None)
            client = NvidiaClient()
        result = client.analyze_document_structure("some text")
        assert isinstance(result, dict)
        assert "analysis" in result

    def test_validate_compliance_without_key_returns_dict(self):
        """validate_template_compliance() returns a dict even without a key."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NVIDIA_API_KEY", None)
            client = NvidiaClient()
        result = client.validate_template_compliance("document text", "ieee")
        assert isinstance(result, dict)
        assert "compliant" in result

    def test_compliance_parser_detects_noncompliant_response(self):
        """LLM response containing 'does not comply' → compliant=False."""
        with patch.dict(os.environ, {"NVIDIA_API_KEY": "fake-key"}, clear=False):
            client = NvidiaClient()
        # Patch chat() to return a non-compliance response directly
        client.chat = MagicMock(return_value="The document does not comply with IEEE standards.")
        result = client.validate_template_compliance("doc text", "ieee")
        assert result["compliant"] is False

    def test_compliance_parser_detects_compliant_response(self):
        """LLM response containing 'complies' → compliant=True."""
        with patch.dict(os.environ, {"NVIDIA_API_KEY": "fake-key"}, clear=False):
            client = NvidiaClient()
        client.chat = MagicMock(return_value="The document complies with IEEE formatting requirements.")
        result = client.validate_template_compliance("doc text", "ieee")
        assert result["compliant"] is True

    def test_singleton_returns_instance(self):
        """get_nvidia_client() returns an NvidiaClient (or None on hard failure)."""
        import app.services.nvidia_client as mod
        mod._nvidia_client = None  # reset singleton
        client = get_nvidia_client()
        assert client is None or isinstance(client, NvidiaClient)
