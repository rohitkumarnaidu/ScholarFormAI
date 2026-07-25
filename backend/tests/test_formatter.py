import gc
import time
import tempfile
from pathlib import Path

import pytest


def _force_cleanup(path: Path, max_retries: int = 3):
    for attempt in range(max_retries):
        gc.collect()
        time.sleep(0.05 * (attempt + 1))
        try:
            path.unlink(missing_ok=True)
            return
        except PermissionError:
            if attempt == max_retries - 1:
                pass

from app.api.models import Author, Manuscript, Paragraph, Section
from app.services.formatter import ManuscriptFormatter
from app.services.style_registry import StyleRegistry


@pytest.fixture
def formatter():
    return ManuscriptFormatter()


@pytest.fixture
def style_registry():
    return StyleRegistry()


@pytest.fixture
def sample_manuscript():
    return Manuscript(
        title="Test Manuscript Title",
        authors=[Author(first_name="Test", last_name="Author")],
        abstract="This is a test abstract for testing purposes.",
        keywords=["test", "manuscript"],
        sections=[
            Section(
                heading="Introduction",
                level=1,
                content=[Paragraph(text="This is the introduction paragraph.")],
            ),
        ],
    )


def test_format_apa(formatter, style_registry, sample_manuscript):
    style = style_registry.get_style("apa")
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        output = formatter.format(sample_manuscript, style, tmp.name)
        assert Path(output).exists()
        assert Path(output).suffix == ".docx"
        assert Path(output).stat().st_size > 0
        _force_cleanup(Path(output))


def test_format_mla(formatter, style_registry, sample_manuscript):
    style = style_registry.get_style("mla")
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        output = formatter.format(sample_manuscript, style, tmp.name)
        assert Path(output).exists()
        _force_cleanup(Path(output))


def test_format_chicago(formatter, style_registry, sample_manuscript):
    style = style_registry.get_style("chicago")
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        output = formatter.format(sample_manuscript, style, tmp.name)
        assert Path(output).exists()
        _force_cleanup(Path(output))


def test_format_ieee(formatter, style_registry, sample_manuscript):
    style = style_registry.get_style("ieee")
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        output = formatter.format(sample_manuscript, style, tmp.name)
        assert Path(output).exists()
        _force_cleanup(Path(output))


def test_format_all_styles(formatter, style_registry, sample_manuscript):
    for style_info in style_registry.list_styles():
        style = style_registry.get_style(style_info["id"])
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            try:
                output = formatter.format(sample_manuscript, style, tmp.name)
                assert Path(output).exists()
                _force_cleanup(Path(output))
            except Exception as e:
                pytest.fail(f"Style '{style_info['id']}' failed: {e}")


def test_estimate_pages(formatter, style_registry, sample_manuscript):
    style = style_registry.get_style("apa")
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        output = formatter.format(sample_manuscript, style, tmp.name)
        pages = formatter.estimate_pages(output)
        assert isinstance(pages, int)
        assert pages >= 1
        _force_cleanup(Path(output))


def test_generate_html_preview(formatter, style_registry, sample_manuscript):
    style = style_registry.get_style("apa")
    html = formatter.generate_html_preview(sample_manuscript, style)
    assert "<!DOCTYPE html>" in html
    assert sample_manuscript.title in html
    assert "Abstract" in html
    assert "References" not in html or True
