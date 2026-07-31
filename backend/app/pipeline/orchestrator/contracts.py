# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""Stage contract interfaces using Protocol for the pipeline orchestrator."""

from typing import Protocol, Any, runtime_checkable
from app.pipeline.base import PipelineDocument


@runtime_checkable
class StageContract(Protocol):
    """Contract that every pipeline stage must implement."""

    stage_name: str

    async def execute(self, document: PipelineDocument, context: dict[str, Any]) -> PipelineDocument: ...

    async def validate(self, document: PipelineDocument) -> list[str]: ...

    async def rollback(self, document: PipelineDocument, error: Exception) -> None: ...
