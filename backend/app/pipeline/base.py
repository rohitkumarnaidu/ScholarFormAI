# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from abc import ABC, abstractmethod
from app.models import PipelineDocument


class PipelineStage(ABC):
    """
    Abstract base class for all pipeline stages.

    All stages must implement the process() method which takes a PipelineDocument
    and returns a PipelineDocument (usually modified in-place).
    """

    @abstractmethod
    def process(self, document: PipelineDocument) -> PipelineDocument:
        """
        Main processing logic for the stage.

        Args:
            document: The document model to process.

        Returns:
            The processed document model.
        """
        pass
