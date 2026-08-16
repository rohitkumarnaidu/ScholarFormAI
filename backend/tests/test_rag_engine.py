# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Test Suite for RAG Engine
Tests retrieval-augmented generation, ChromaDB integration, and fallback mechanisms.
"""

import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from app.pipeline.intelligence.rag_engine import RagEngine


class TestRagEngine:
    """Test suite for RAG engine."""

    @pytest.fixture
    def temp_persist_dir(self):
        """Create temporary persistence directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def sample_guidelines(self):
        """Sample publisher guidelines for testing."""
        return [
            {
                "publisher": "IEEE",
                "section": "abstract",
                "text": "Abstract should be 150-250 words and provide a concise summary.",
            },
            {
                "publisher": "IEEE",
                "section": "references",
                "text": "References should be numbered in order of appearance.",
            },
            {"publisher": "APA", "section": "abstract", "text": "Abstract should not exceed 250 words."},
        ]

    @pytest.mark.rag
    def test_initialization_native_backend(self, temp_persist_dir):
        """Test RAG engine initialization with native backend."""
        with patch("app.pipeline.intelligence.rag_engine.chromadb") as mock_chromadb:
            # Force ChromaDB to fail
            mock_chromadb.PersistentClient.side_effect = Exception("ChromaDB unavailable")

            engine = RagEngine(persist_directory=temp_persist_dir)

            assert engine.backend == "native"
            assert not engine.chroma_enabled
            assert engine.embedding_model is not None

    @pytest.mark.rag
    def test_initialization_chromadb_backend(self, temp_persist_dir):
        """Test RAG engine initialization with ChromaDB backend."""
        with patch("app.pipeline.intelligence.rag_engine.chromadb") as mock_chromadb:
            # Mock successful ChromaDB initialization
            mock_client = MagicMock()
            mock_collection = MagicMock()
            mock_chromadb.PersistentClient.return_value = mock_client
            mock_client.get_or_create_collection.return_value = mock_collection

            engine = RagEngine(persist_directory=temp_persist_dir)

            assert engine.backend == "chromadb"
            assert engine.chroma_enabled
            assert engine.client is not None

    @pytest.mark.rag
    def test_add_guideline_native(self, temp_persist_dir, sample_guidelines):
        """Test adding guidelines to native backend."""
        with patch("app.pipeline.intelligence.rag_engine.chromadb") as mock_chromadb:
            mock_chromadb.PersistentClient.side_effect = Exception("ChromaDB unavailable")

            engine = RagEngine(persist_directory=temp_persist_dir)

            # Add guideline
            guideline = sample_guidelines[0]
            engine.add_guideline(publisher=guideline["publisher"], section=guideline["section"], text=guideline["text"])

            # Verify it was added
            assert len(engine.knowledge_base) == 1
            assert engine.knowledge_base[0]["text"] == guideline["text"]
            assert engine.knowledge_base[0]["metadata"]["publisher"] == "IEEE"
            assert "embedding" in engine.knowledge_base[0]

    @pytest.mark.rag
    def test_add_guideline_chromadb(self, temp_persist_dir, sample_guidelines):
        """Test adding guidelines to ChromaDB backend."""
        with patch("app.pipeline.intelligence.rag_engine.chromadb") as mock_chromadb:
            mock_client = MagicMock()
            mock_collection = MagicMock()
            mock_chromadb.PersistentClient.return_value = mock_client
            mock_client.get_or_create_collection.return_value = mock_collection

            engine = RagEngine(persist_directory=temp_persist_dir)

            guideline = sample_guidelines[0]
            engine.add_guideline(publisher=guideline["publisher"], section=guideline["section"], text=guideline["text"])

            # Verify ChromaDB add was called
            mock_collection.add.assert_called_once()

            # Verify native store also updated (for fallback)
            assert len(engine.knowledge_base) == 1

    @pytest.mark.rag
    def test_query_guidelines_native(self, temp_persist_dir, sample_guidelines):
        """Test querying guidelines from native backend."""
        with patch("app.pipeline.intelligence.rag_engine.chromadb") as mock_chromadb:
            mock_chromadb.PersistentClient.side_effect = Exception("ChromaDB unavailable")

            engine = RagEngine(persist_directory=temp_persist_dir)

            # Add multiple guidelines
            for guideline in sample_guidelines[:2]:  # Only IEEE guidelines
                engine.add_guideline(
                    publisher=guideline["publisher"], section=guideline["section"], text=guideline["text"]
                )

            # Query for abstract guidelines
            results = engine.query_guidelines(publisher="IEEE", intent="abstract formatting rules", top_k=1)

            assert len(results) > 0
            assert isinstance(results[0], str)
            # Should return the abstract guideline
            assert "abstract" in results[0].lower()

    @pytest.mark.rag
    def test_query_guidelines_chromadb(self, temp_persist_dir):
        """Test querying guidelines from ChromaDB backend."""
        with patch("app.pipeline.intelligence.rag_engine.chromadb") as mock_chromadb:
            mock_client = MagicMock()
            mock_collection = MagicMock()
            mock_chromadb.PersistentClient.return_value = mock_client
            mock_client.get_or_create_collection.return_value = mock_collection

            # Mock query response
            mock_collection.query.return_value = {"documents": [["Abstract should be concise."]]}

            engine = RagEngine(persist_directory=temp_persist_dir)

            results = engine.query_guidelines(publisher="IEEE", intent="abstract formatting", top_k=1)

            assert len(results) == 1
            assert results[0] == "Abstract should be concise."
            mock_collection.query.assert_called_once()

    @pytest.mark.rag
    def test_query_rules_interface(self, temp_persist_dir, sample_guidelines):
        """Test query_rules interface required by orchestrator."""
        with patch("app.pipeline.intelligence.rag_engine.chromadb") as mock_chromadb:
            mock_chromadb.PersistentClient.side_effect = Exception("ChromaDB unavailable")

            engine = RagEngine(persist_directory=temp_persist_dir)

            # Add guidelines
            for guideline in sample_guidelines[:2]:
                engine.add_guideline(
                    publisher=guideline["publisher"], section=guideline["section"], text=guideline["text"]
                )

            # Query using orchestrator interface
            results = engine.query_rules(template_name="ieee", section_name="abstract", top_k=1)

            assert isinstance(results, list)
            assert len(results) > 0
            assert "text" in results[0]
            assert "metadata" in results[0]
            assert results[0]["metadata"]["publisher"] == "IEEE"

    @pytest.mark.rag
    def test_native_persistence(self, temp_persist_dir, sample_guidelines):
        """Test native backend persistence to disk."""
        with patch("app.pipeline.intelligence.rag_engine.chromadb") as mock_chromadb:
            mock_chromadb.PersistentClient.side_effect = Exception("ChromaDB unavailable")

            # Create engine and add guideline
            engine1 = RagEngine(persist_directory=temp_persist_dir)
            guideline = sample_guidelines[0]
            engine1.add_guideline(
                publisher=guideline["publisher"], section=guideline["section"], text=guideline["text"]
            )

            # Create new engine instance (should load from disk)
            engine2 = RagEngine(persist_directory=temp_persist_dir)

            assert len(engine2.knowledge_base) == 1
            assert engine2.knowledge_base[0]["text"] == guideline["text"]

    @pytest.mark.rag
    def test_chromadb_fallback_on_query_error(self, temp_persist_dir, sample_guidelines):
        """Test fallback to native when ChromaDB query fails."""
        with patch("app.pipeline.intelligence.rag_engine.chromadb") as mock_chromadb:
            mock_client = MagicMock()
            mock_collection = MagicMock()
            mock_chromadb.PersistentClient.return_value = mock_client
            mock_client.get_or_create_collection.return_value = mock_collection

            engine = RagEngine(persist_directory=temp_persist_dir)

            # Add guideline (goes to both ChromaDB and native)
            guideline = sample_guidelines[0]
            engine.add_guideline(publisher=guideline["publisher"], section=guideline["section"], text=guideline["text"])

            # Make ChromaDB query fail
            mock_collection.query.side_effect = Exception("ChromaDB query failed")

            # Should fall back to native
            results = engine.query_guidelines(publisher="IEEE", intent="abstract", top_k=1)

            # Should still get results from native fallback
            assert len(results) > 0

    @pytest.mark.rag
    def test_reset_functionality(self, temp_persist_dir, sample_guidelines):
        """Test reset clears all guidelines."""
        with patch("app.pipeline.intelligence.rag_engine.chromadb") as mock_chromadb:
            mock_chromadb.PersistentClient.side_effect = Exception("ChromaDB unavailable")

            engine = RagEngine(persist_directory=temp_persist_dir)

            # Add guidelines
            for guideline in sample_guidelines:
                engine.add_guideline(
                    publisher=guideline["publisher"], section=guideline["section"], text=guideline["text"]
                )

            assert len(engine.knowledge_base) == 3

            # Reset
            engine.reset()

            assert len(engine.knowledge_base) == 0
            assert not os.path.exists(engine.kb_file)

    @pytest.mark.rag
    def test_semantic_similarity_ranking(self, temp_persist_dir):
        """Test that semantic similarity ranks results correctly."""
        with patch("app.pipeline.intelligence.rag_engine.chromadb") as mock_chromadb:
            mock_chromadb.PersistentClient.side_effect = Exception("ChromaDB unavailable")

            engine = RagEngine(persist_directory=temp_persist_dir)

            # Add guidelines with different relevance
            engine.add_guideline("IEEE", "abstract", "Abstract should be 150-250 words.")
            engine.add_guideline("IEEE", "references", "References use numbered citations.")
            engine.add_guideline("IEEE", "figures", "Figures should be high resolution.")

            # Query for abstract-related content
            results = engine.query_guidelines(publisher="IEEE", intent="How long should the abstract be?", top_k=1)

            # Most relevant result should be about abstract length
            assert len(results) > 0
            assert "abstract" in results[0].lower()
            assert "150-250" in results[0] or "words" in results[0]

    @pytest.mark.rag
    def test_empty_query_handling(self, temp_persist_dir):
        """Test handling of queries when no guidelines exist."""
        with patch("app.pipeline.intelligence.rag_engine.chromadb") as mock_chromadb:
            mock_chromadb.PersistentClient.side_effect = Exception("ChromaDB unavailable")

            engine = RagEngine(persist_directory=temp_persist_dir)

            # Query empty knowledge base
            results = engine.query_guidelines(publisher="IEEE", intent="abstract formatting", top_k=1)

            assert results == []

    @pytest.mark.rag
    def test_publisher_filtering(self, temp_persist_dir, sample_guidelines):
        """Test that queries filter by publisher correctly."""
        with patch("app.pipeline.intelligence.rag_engine.chromadb") as mock_chromadb:
            mock_chromadb.PersistentClient.side_effect = Exception("ChromaDB unavailable")

            engine = RagEngine(persist_directory=temp_persist_dir)

            # Add guidelines from different publishers
            for guideline in sample_guidelines:
                engine.add_guideline(
                    publisher=guideline["publisher"], section=guideline["section"], text=guideline["text"]
                )

            # Query for IEEE only
            results = engine.query_guidelines(publisher="IEEE", intent="abstract", top_k=10)

            # Should only get IEEE guidelines
            for result in results:
                # Find the guideline in knowledge base
                matching = [g for g in engine.knowledge_base if g["text"] == result]
                assert len(matching) > 0
                assert matching[0]["metadata"]["publisher"] == "IEEE"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "rag"])
