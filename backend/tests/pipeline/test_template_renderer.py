# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from app.models import PipelineDocument as Document
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation, TableCell, TextStyle, ImageFormat, BClass, EClass, RClass
from app.pipeline.formatting.formatter import Formatter
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation
from __future__ import annotations
import os
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from pathlib import Path

from app.pipeline.formatting.template_renderer import TemplateRenderer


class TestTemplateRendererCoerceBool:
    def test_none_defaults_to_false(self):
        assert TemplateRenderer._coerce_bool(None, False) is False

    def test_none_defaults_to_true(self):
        assert TemplateRenderer._coerce_bool(None, True) is True

    def test_bool_passthrough(self):
        assert TemplateRenderer._coerce_bool(True, False) is True
        assert TemplateRenderer._coerce_bool(False, True) is False

    def test_int_zero(self):
        assert TemplateRenderer._coerce_bool(0, False) is False

    def test_int_nonzero(self):
        assert TemplateRenderer._coerce_bool(1, False) is True
        assert TemplateRenderer._coerce_bool(42, False) is True

    def test_float(self):
        assert TemplateRenderer._coerce_bool(0.0, False) is False
        assert TemplateRenderer._coerce_bool(0.5, False) is True

    def test_string_true_values(self):
        for val in ["1", "true", "True", "yes", "on"]:
            assert TemplateRenderer._coerce_bool(val, False) is True

    def test_string_false_values(self):
        for val in ["0", "false", "False", "no", "off"]:
            assert TemplateRenderer._coerce_bool(val, True) is False

    def test_string_unknown_defaults(self):
        assert TemplateRenderer._coerce_bool("maybe", True) is True
        assert TemplateRenderer._coerce_bool("maybe", False) is True


@pytest.fixture
def renderer():
    return TemplateRenderer(templates_dir="app/templates")


class TestTemplateRendererInit:
    def test_init_default_path(self):
        r = TemplateRenderer()
        assert "templates" in str(r.templates_dir)

    def test_init_custom_path(self):
        r = TemplateRenderer(templates_dir="/custom/path")
        assert os.path.normpath(str(r.templates_dir)) == os.path.normpath("/custom/path")


@patch("app.pipeline.formatting.template_renderer.DocxTemplate")
class TestTemplateRendererRender:
    def test_render_docx_no_markers(self, mock_docxtpl_cls, renderer, tmp_path):
        mock_instance = MagicMock()
        mock_docxtpl_cls.return_value = mock_instance
        mock_template = tmp_path / "template.docx"
        mock_template.write_text("")
        mock_instance.get_xml.return_value = "<w:document/>"

        doc = MagicMock()
        result = renderer.render(
            document=doc,
            template_name="report",
        )
        assert result is not None
