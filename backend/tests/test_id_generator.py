import pytest
from app.utils.id_generator import (
    generate_block_id, generate_figure_id, generate_table_id,
    generate_reference_id, generate_equation_id, generate_document_id,
)


class TestGenerateBlockId:
    def test_generates_string(self):
        result = generate_block_id(0)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_sequential_indices_differ(self):
        a = generate_block_id(0)
        b = generate_block_id(1)
        assert a != b


class TestGenerateFigureId:
    def test_generates_string(self):
        result = generate_figure_id(0)
        assert isinstance(result, str)
        assert "fig" in result.lower()


class TestGenerateTableId:
    def test_generates_string(self):
        result = generate_table_id(0)
        assert isinstance(result, str)
        assert "tbl" in result.lower()


class TestGenerateReferenceId:
    def test_generates_string(self):
        result = generate_reference_id(0)
        assert isinstance(result, str)
        assert "ref" in result.lower()


class TestGenerateEquationId:
    def test_generates_string(self):
        result = generate_equation_id(0)
        assert isinstance(result, str)
        assert "eqn" in result.lower()


class TestGenerateDocumentId:
    def test_generates_string(self):
        result = generate_document_id()
        assert isinstance(result, str)
        assert "doc" in result.lower()

    def test_custom_prefix(self):
        result = generate_document_id(prefix="paper")
        assert result.startswith("paper_")

    def test_all_start_with_prefix(self):
        ids = [generate_document_id() for _ in range(10)]
        assert all(id.startswith("doc_") for id in ids)
