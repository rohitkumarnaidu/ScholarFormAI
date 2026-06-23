# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Minimal Chroma backend tests through RagEngine.

These tests validate the app behavior for both:
1) Chroma unavailable -> native fallback
2) Chroma available -> Chroma backend path
"""

from unittest.mock import MagicMock, patch

from app.pipeline.intelligence.rag_engine import RagEngine


def test_rag_engine_falls_back_to_native_when_chroma_unavailable(tmp_path):
    with (
        patch("app.pipeline.intelligence.rag_engine.chromadb", None),
        patch("app.pipeline.intelligence.rag_engine._load_chromadb", return_value=None),
    ):
        engine = RagEngine(persist_directory=str(tmp_path))

    assert engine.backend == "native"
    assert engine.chroma_enabled is False


def test_rag_engine_uses_chroma_backend_when_client_initializes(tmp_path):
    chromadb_mock = MagicMock()
    client_mock = MagicMock()
    collection_mock = MagicMock()

    chromadb_mock.PersistentClient.return_value = client_mock
    client_mock.get_or_create_collection.return_value = collection_mock

    with patch("app.pipeline.intelligence.rag_engine.chromadb", chromadb_mock):
        engine = RagEngine(persist_directory=str(tmp_path))

    assert engine.backend == "chromadb"
    assert engine.chroma_enabled is True
    chromadb_mock.PersistentClient.assert_called_once()
    client_mock.get_or_create_collection.assert_called_once()
