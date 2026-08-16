# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


class TestPipelineStage:
    def test_abstract_cannot_instantiate(self):
        from app.pipeline.base import PipelineStage

        with pytest.raises(TypeError):
            PipelineStage()

    def test_concrete_implementation(self):
        from app.pipeline.base import PipelineStage

        class ConcreteStage(PipelineStage):
            def process(self, document):
                document.processed = True
                return document

        doc = MagicMock()
        result = ConcreteStage().process(doc)
        assert result.processed is True
