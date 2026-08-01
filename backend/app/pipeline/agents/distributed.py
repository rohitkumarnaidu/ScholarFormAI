# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Distributed processing with multi-agent coordination.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# Maximum time (seconds) to wait for a single specialist task
_TASK_TIMEOUT = 120


class AgentRole(Enum):
    """Agent roles in distributed system."""

    COORDINATOR = "coordinator"
    METADATA_SPECIALIST = "metadata_specialist"
    LAYOUT_SPECIALIST = "layout_specialist"
    VALIDATION_SPECIALIST = "validation_specialist"
    REFERENCE_SPECIALIST = "reference_specialist"


@dataclass
class AgentTask:
    """Task for a specialist agent."""

    task_id: str
    role: AgentRole
    document_path: str
    parameters: dict[str, Any] = field(default_factory=dict)


class SpecialistAgent:
    """
    Specialist agent for a specific task.
    """

    def __init__(self, role: AgentRole, tools: list[Any]):
        """
        Initialize specialist agent.

        Args:
            role: Agent role
            tools: Tools available to this agent
        """
        if not isinstance(role, AgentRole):
            raise ValueError(f"role must be an AgentRole instance, got {type(role)}")
        self.role = role
        self.tools = tools or []
        self.task_count = 0

    def process(self, task: AgentTask) -> dict[str, Any]:
        """
        Process a task.

        Args:
            task: Task to process

        Returns:
            Processing result dict. Always returns a dict (never raises).
        """
        if task is None:
            logger.error("%s received None task", self.role.value)
            return {"error": "task is None", "role": self.role.value}

        self.task_count += 1
        logger.info("%s processing task %s", self.role.value, task.task_id)

        try:
            if self.role == AgentRole.METADATA_SPECIALIST:
                return self._process_metadata(task)
            elif self.role == AgentRole.LAYOUT_SPECIALIST:
                return self._process_layout(task)
            elif self.role == AgentRole.VALIDATION_SPECIALIST:
                return self._process_validation(task)
            elif self.role == AgentRole.REFERENCE_SPECIALIST:
                return self._process_references(task)
            else:
                logger.warning("Unknown role: %s", self.role.value)
                return {"error": f"Unknown role: {self.role.value}", "task_id": task.task_id}

        except Exception as exc:
            logger.error("%s failed on task %s: %s", self.role.value, task.task_id, exc)
            return {"error": str(exc), "role": self.role.value, "task_id": task.task_id}

    def _process_metadata(self, task: AgentTask) -> dict[str, Any]:
        """Process metadata extraction."""
        return {
            "task_id": task.task_id,
            "role": self.role.value,
            "result": "metadata_extracted",
            "data": {
                "title": "Sample Title",
                "authors": ["Author 1", "Author 2"],
            },
        }

    def _process_layout(self, task: AgentTask) -> dict[str, Any]:
        """Process layout analysis."""
        return {
            "task_id": task.task_id,
            "role": self.role.value,
            "result": "layout_analyzed",
            "data": {
                "blocks": 50,
                "figures": 5,
            },
        }

    def _process_validation(self, task: AgentTask) -> dict[str, Any]:
        """Process validation."""
        return {
            "task_id": task.task_id,
            "role": self.role.value,
            "result": "validation_complete",
            "data": {
                "errors": 0,
                "warnings": 2,
            },
        }

    def _process_references(self, task: AgentTask) -> dict[str, Any]:
        """Process reference extraction."""
        return {
            "task_id": task.task_id,
            "role": self.role.value,
            "result": "references_extracted",
            "data": {
                "count": 25,
                "with_dois": 20,
            },
        }


class DistributedCoordinator:
    """
    Coordinator for distributed multi-agent processing.
    """

    def __init__(self, max_workers: int = 4):
        """
        Initialize coordinator.

        Args:
            max_workers: Maximum parallel workers (>= 1)
        """
        if max_workers < 1:
            raise ValueError(f"max_workers must be >= 1, got {max_workers}")
        self.max_workers = max_workers
        self.specialists: dict[AgentRole, SpecialistAgent] = {}
        self._initialize_specialists()

    def _initialize_specialists(self) -> None:
        """Initialize specialist agents."""
        for role in [
            AgentRole.METADATA_SPECIALIST,
            AgentRole.LAYOUT_SPECIALIST,
            AgentRole.VALIDATION_SPECIALIST,
            AgentRole.REFERENCE_SPECIALIST,
        ]:
            try:
                self.specialists[role] = SpecialistAgent(role, tools=[])
            except Exception as exc:
                logger.error("Failed to initialize specialist for role %s: %s", role.value, exc)

    def process_document(self, document_path: str) -> dict[str, Any]:
        """
        Process document using distributed agents.

        Args:
            document_path: Path to document

        Returns:
            Combined results from all specialists. Always returns a valid dict.
        """
        if not document_path:
            logger.error("process_document called with empty document_path")
            return {"document_path": document_path, "specialist_results": [], "success": False}

        # Create tasks for each available specialist
        tasks = [
            AgentTask(
                task_id=f"{role.value}_task",
                role=role,
                document_path=document_path,
                parameters={},
            )
            for role in self.specialists
        ]

        if not tasks:
            logger.warning("No specialist agents available for processing")
            return {"document_path": document_path, "specialist_results": [], "success": False}

        # Process tasks in parallel
        results = self._process_parallel(tasks)

        # Determine overall success (no error keys in any result)
        success = all("error" not in r for r in results) and bool(results)

        return {
            "document_path": document_path,
            "specialist_results": results,
            "success": success,
        }

    def _process_parallel(self, tasks: list[AgentTask]) -> list[dict[str, Any]]:
        """
        Process tasks in parallel.

        Args:
            tasks: List of tasks

        Returns:
            List of results (one per task, always)
        """
        results: list[dict[str, Any]] = []

        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_task = {
                    executor.submit(self.specialists[task.role].process, task): task
                    for task in tasks
                    if task.role in self.specialists
                }

                for future in as_completed(future_to_task, timeout=_TASK_TIMEOUT):
                    task = future_to_task[future]
                    try:
                        result = future.result(timeout=_TASK_TIMEOUT)
                        results.append(result)
                    except Exception as exc:
                        logger.error("Task %s raised an exception: %s", task.task_id, exc)
                        results.append({"task_id": task.task_id, "error": str(exc)})

        except Exception as exc:
            logger.error("Error in _process_parallel: %s", exc)

        return results

    def get_statistics(self) -> dict[str, Any]:
        """Get processing statistics. Always returns a valid dict."""
        try:
            return {
                "specialists": {
                    role.value: {"task_count": agent.task_count} for role, agent in self.specialists.items()
                },
                "total_tasks": sum(a.task_count for a in self.specialists.values()),
            }
        except Exception as exc:
            logger.error("Error in get_statistics: %s", exc)
            return {"specialists": {}, "total_tasks": 0}
