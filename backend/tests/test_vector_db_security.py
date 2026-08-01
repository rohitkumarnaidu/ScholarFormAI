from __future__ import annotations

from unittest.mock import patch

import pytest

pytestmark = [pytest.mark.rag]


class TestRAGDataLeakage:
    @patch("app.pipeline.intelligence.rag_engine.chromadb", None)
    @patch("app.pipeline.intelligence.rag_engine._load_chromadb", return_value=None)
    def test_rag_cannot_query_unrelated_document_data(self, mock_load, tmp_path):
        from app.pipeline.intelligence.rag_engine import RagEngine
        persist = tmp_path / "rag_test"
        persist.mkdir()
        engine = RagEngine(persist_directory=str(persist), auto_seed=False)
        engine.add_guideline("IEEE", "formatting", "Use 12pt Times New Roman")
        engine.add_guideline("ACM", "formatting", "Use 10pt Computer Modern")
        results = engine.query_guidelines("IEEE", "font size", top_k=5)
        for r in results:
            assert "10pt Computer Modern" not in r
        results_acm = engine.query_guidelines("ACM", "font size", top_k=5)
        for r in results_acm:
            assert "12pt Times New Roman" not in r


class TestVectorDatabasePoisoning:
    @patch("app.pipeline.intelligence.rag_engine.chromadb", None)
    @patch("app.pipeline.intelligence.rag_engine._load_chromadb", return_value=None)
    def test_malicious_document_injection_resisted(self, mock_load, tmp_path):
        from app.pipeline.intelligence.rag_engine import RagEngine
        persist = tmp_path / "rag_poison"
        persist.mkdir()
        engine = RagEngine(persist_directory=str(persist), auto_seed=False)
        engine.add_guideline("IEEE", "formatting", "Use 12pt Times New Roman")
        malicious = "<script>malicious</script>" * 1000
        engine.add_guideline("IEEE", "formatting", malicious)
        results = engine.query_guidelines("IEEE", "font size", top_k=10)
        assert len(results) > 0
        legit_found = any("Times New Roman" in r for r in results)
        assert legit_found


class TestQueryInjection:
    @patch("app.pipeline.intelligence.rag_engine.chromadb", None)
    @patch("app.pipeline.intelligence.rag_engine._load_chromadb", return_value=None)
    def test_embedding_manipulation_does_not_crash(self, mock_load, tmp_path):
        from app.pipeline.intelligence.rag_engine import RagEngine
        persist = tmp_path / "rag_inject"
        persist.mkdir()
        engine = RagEngine(persist_directory=str(persist), auto_seed=False)
        engine.add_guideline("IEEE", "formatting", "Use 12pt Times New Roman")
        injection_queries = [
            "\x00\x01\x02\x03" * 100,
            "\uffff" * 1000,
            "SELECT * FROM users; DROP TABLE guidelines;",
            "../../../etc/passwd",
            "\\x00\\x01\\x02",
        ]
        for q in injection_queries:
            results = engine.query_guidelines("IEEE", q, top_k=3)
            assert isinstance(results, list)

    @patch("app.pipeline.intelligence.rag_engine.chromadb", None)
    @patch("app.pipeline.intelligence.rag_engine._load_chromadb", return_value=None)
    def test_zero_length_query_returns_empty(self, mock_load, tmp_path):
        from app.pipeline.intelligence.rag_engine import RagEngine
        persist = tmp_path / "rag_empty"
        persist.mkdir()
        engine = RagEngine(persist_directory=str(persist), auto_seed=False)
        engine.add_guideline("IEEE", "formatting", "Use 12pt Times New Roman")
        results = engine.query_guidelines("IEEE", "", top_k=3)
        assert results == []


class TestCrossUserDataLeakage:
    @patch("app.pipeline.intelligence.rag_engine.chromadb", None)
    @patch("app.pipeline.intelligence.rag_engine._load_chromadb", return_value=None)
    def test_cross_user_isolation(self, mock_load, tmp_path):
        import tempfile

        from app.pipeline.intelligence.rag_engine import RagEngine
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            engine1 = RagEngine(persist_directory=d1, auto_seed=False)
            engine2 = RagEngine(persist_directory=d2, auto_seed=False)
            engine1.add_guideline("IEEE", "formatting", "Secret User 1 Data")
            engine2.add_guideline("IEEE", "formatting", "Secret User 2 Data")
            r1 = engine1.query_guidelines("IEEE", "Secret User", top_k=5)
            r2 = engine2.query_guidelines("IEEE", "Secret User", top_k=5)
            assert any("User 1" in r for r in r1)
            assert all("User 1" not in r for r in r2)
            assert any("User 2" in r for r in r2)
            assert all("User 2" not in r for r in r1)


class TestIndexCorruption:
    @patch("app.pipeline.intelligence.rag_engine.chromadb", None)
    @patch("app.pipeline.intelligence.rag_engine._load_chromadb", return_value=None)
    def test_corrupted_index_file_does_not_crash(self, mock_load, tmp_path):
        from app.pipeline.intelligence.rag_engine import RagEngine
        persist = tmp_path / "rag_corrupt"
        persist.mkdir()
        kb_file = persist / "kb.json"
        kb_file.write_text("[]")
        engine = RagEngine(persist_directory=str(persist), auto_seed=False)
        engine.add_guideline("IEEE", "test", "New guideline after corruption")
        results = engine.query_guidelines("IEEE", "test")
        assert isinstance(results, list)

    @patch("app.pipeline.intelligence.rag_engine.chromadb", None)
    @patch("app.pipeline.intelligence.rag_engine._load_chromadb", return_value=None)
    def test_empty_index_returns_empty(self, mock_load, tmp_path):
        from app.pipeline.intelligence.rag_engine import RagEngine
        persist = tmp_path / "rag_empty_idx"
        persist.mkdir()
        engine = RagEngine(persist_directory=str(persist), auto_seed=False)
        results = engine.query_guidelines("IEEE", "anything")
        assert results == []


class TestEmbeddingModelAdversarial:
    @patch("app.pipeline.intelligence.rag_engine.chromadb", None)
    @patch("app.pipeline.intelligence.rag_engine._load_chromadb", return_value=None)
    def test_adversarial_embedding_text_handled(self, mock_load, tmp_path):
        from app.pipeline.intelligence.rag_engine import RagEngine
        persist = tmp_path / "rag_adv"
        persist.mkdir()
        engine = RagEngine(persist_directory=str(persist), auto_seed=False)
        adversarial_texts = [
            "\x00" * 10000,
            "\xff" * 10000,
            "A" * 100000,
        ]
        for t in adversarial_texts:
            engine.add_guideline("IEEE", "test", t)
            assert len(engine.knowledge_base) > 0


class TestLargePayload:
    @patch("app.pipeline.intelligence.rag_engine.chromadb", None)
    @patch("app.pipeline.intelligence.rag_engine._load_chromadb", return_value=None)
    def test_oversized_document_handled(self, mock_load, tmp_path):
        from app.pipeline.intelligence.rag_engine import RagEngine
        persist = tmp_path / "rag_large"
        persist.mkdir()
        engine = RagEngine(persist_directory=str(persist), auto_seed=False)
        engine.add_guideline("IEEE", "section", "A" * 50000)
        engine.add_guideline("IEEE", "section", "B" * 75000)
        assert len(engine.knowledge_base) == 2


class TestNamespaceAccess:
    @patch("app.pipeline.intelligence.rag_engine.chromadb", None)
    @patch("app.pipeline.intelligence.rag_engine._load_chromadb", return_value=None)
    def test_empty_publisher_returns_empty(self, mock_load, tmp_path):
        from app.pipeline.intelligence.rag_engine import RagEngine
        persist = tmp_path / "rag_ns"
        persist.mkdir()
        engine = RagEngine(persist_directory=str(persist), auto_seed=False)
        engine.add_guideline("PUB1", "test", "Content1")
        engine.add_guideline("PUB2", "test", "Content2")
        r = engine.query_guidelines("NONEXISTENT", "test")
        assert r == []

    @patch("app.pipeline.intelligence.rag_engine.chromadb", None)
    @patch("app.pipeline.intelligence.rag_engine._load_chromadb", return_value=None)
    def test_query_rules_handles_unknown_template(self, mock_load, tmp_path):
        from app.pipeline.intelligence.rag_engine import RagEngine
        persist = tmp_path / "rag_qt"
        persist.mkdir()
        engine = RagEngine(persist_directory=str(persist), auto_seed=False)
        rules = engine.query_rules("UNKNOWN_TEMPLATE", "general")
        assert rules == []
