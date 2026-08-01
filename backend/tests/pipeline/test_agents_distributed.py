# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.pipeline]


class TestAgentRole:
    def test_enum_values(self):
        from app.pipeline.agents.distributed import AgentRole
        assert AgentRole.COORDINATOR.value == "coordinator"
        assert AgentRole.METADATA_SPECIALIST.value == "metadata_specialist"
        assert AgentRole.LAYOUT_SPECIALIST.value == "layout_specialist"
        assert AgentRole.VALIDATION_SPECIALIST.value == "validation_specialist"
        assert AgentRole.REFERENCE_SPECIALIST.value == "reference_specialist"

    def test_enum_members(self):
        from app.pipeline.agents.distributed import AgentRole
        assert len(AgentRole) == 5


class TestAgentTask:
    def test_create_task(self):
        from app.pipeline.agents.distributed import AgentRole, AgentTask
        task = AgentTask(task_id="test_1", role=AgentRole.METADATA_SPECIALIST, document_path="/path/doc.pdf")
        assert task.task_id == "test_1"
        assert task.role == AgentRole.METADATA_SPECIALIST
        assert task.document_path == "/path/doc.pdf"
        assert task.parameters == {}

    def test_create_task_with_parameters(self):
        from app.pipeline.agents.distributed import AgentRole, AgentTask
        task = AgentTask(task_id="test_2", role=AgentRole.LAYOUT_SPECIALIST, document_path="/path/doc.pdf", parameters={"fast": True})
        assert task.parameters == {"fast": True}


class TestSpecialistAgentInit:
    def test_init_valid(self):
        from app.pipeline.agents.distributed import AgentRole, SpecialistAgent
        agent = SpecialistAgent(AgentRole.METADATA_SPECIALIST, tools=["tool1"])
        assert agent.role == AgentRole.METADATA_SPECIALIST
        assert agent.tools == ["tool1"]
        assert agent.task_count == 0

    def test_init_no_tools(self):
        from app.pipeline.agents.distributed import AgentRole, SpecialistAgent
        agent = SpecialistAgent(AgentRole.LAYOUT_SPECIALIST, tools=None)
        assert agent.tools == []

    def test_init_invalid_role(self):
        from app.pipeline.agents.distributed import SpecialistAgent
        try:
            SpecialistAgent("not_a_role", tools=[])
            raise AssertionError()
        except ValueError as e:
            assert "AgentRole" in str(e)


class TestSpecialistAgentProcess:
    def test_process_none_task(self):
        from app.pipeline.agents.distributed import AgentRole, SpecialistAgent
        agent = SpecialistAgent(AgentRole.METADATA_SPECIALIST, tools=[])
        result = agent.process(None)
        assert result["error"] == "task is None"
        assert result["role"] == "metadata_specialist"

    def test_process_metadata(self):
        from app.pipeline.agents.distributed import AgentRole, AgentTask, SpecialistAgent
        agent = SpecialistAgent(AgentRole.METADATA_SPECIALIST, tools=[])
        task = AgentTask("m1", AgentRole.METADATA_SPECIALIST, "/doc.pdf")
        result = agent.process(task)
        assert result["result"] == "metadata_extracted"
        assert "title" in result["data"]
        assert agent.task_count == 1

    def test_process_layout(self):
        from app.pipeline.agents.distributed import AgentRole, AgentTask, SpecialistAgent
        agent = SpecialistAgent(AgentRole.LAYOUT_SPECIALIST, tools=[])
        task = AgentTask("l1", AgentRole.LAYOUT_SPECIALIST, "/doc.pdf")
        result = agent.process(task)
        assert result["result"] == "layout_analyzed"
        assert result["data"]["blocks"] == 50

    def test_process_validation(self):
        from app.pipeline.agents.distributed import AgentRole, AgentTask, SpecialistAgent
        agent = SpecialistAgent(AgentRole.VALIDATION_SPECIALIST, tools=[])
        task = AgentTask("v1", AgentRole.VALIDATION_SPECIALIST, "/doc.pdf")
        result = agent.process(task)
        assert result["result"] == "validation_complete"
        assert result["data"]["errors"] == 0

    def test_process_references(self):
        from app.pipeline.agents.distributed import AgentRole, AgentTask, SpecialistAgent
        agent = SpecialistAgent(AgentRole.REFERENCE_SPECIALIST, tools=[])
        task = AgentTask("r1", AgentRole.REFERENCE_SPECIALIST, "/doc.pdf")
        result = agent.process(task)
        assert result["result"] == "references_extracted"
        assert result["data"]["count"] == 25

    def test_process_unknown_role(self):
        from app.pipeline.agents.distributed import AgentRole, AgentTask, SpecialistAgent
        agent = SpecialistAgent(AgentRole.METADATA_SPECIALIST, tools=[])
        agent.role = AgentRole.COORDINATOR
        task = AgentTask("u1", AgentRole.COORDINATOR, "/doc.pdf")
        result = agent.process(task)
        assert "Unknown role" in result["error"]

    def test_process_exception_safe(self):
        from app.pipeline.agents.distributed import AgentRole, AgentTask, SpecialistAgent
        agent = SpecialistAgent(AgentRole.METADATA_SPECIALIST, tools=[])
        task = AgentTask("fail", AgentRole.METADATA_SPECIALIST, "/doc.pdf")
        original = agent._process_metadata
        agent._process_metadata = MagicMock(side_effect=RuntimeError("fail"))
        result = agent.process(task)
        assert "error" in result
        agent._process_metadata = original


class TestSpecialistAgentSubprocessors:
    def test_process_metadata_structure(self):
        from app.pipeline.agents.distributed import AgentRole, AgentTask, SpecialistAgent
        agent = SpecialistAgent(AgentRole.METADATA_SPECIALIST, tools=[])
        task = AgentTask("m1", AgentRole.METADATA_SPECIALIST, "/doc.pdf")
        result = agent._process_metadata(task)
        assert result["task_id"] == "m1"
        assert result["data"]["authors"] == ["Author 1", "Author 2"]

    def test_process_layout_structure(self):
        from app.pipeline.agents.distributed import AgentRole, AgentTask, SpecialistAgent
        agent = SpecialistAgent(AgentRole.LAYOUT_SPECIALIST, tools=[])
        task = AgentTask("l1", AgentRole.LAYOUT_SPECIALIST, "/doc.pdf")
        result = agent._process_layout(task)
        assert result["data"]["figures"] == 5

    def test_process_validation_structure(self):
        from app.pipeline.agents.distributed import AgentRole, AgentTask, SpecialistAgent
        agent = SpecialistAgent(AgentRole.VALIDATION_SPECIALIST, tools=[])
        task = AgentTask("v1", AgentRole.VALIDATION_SPECIALIST, "/doc.pdf")
        result = agent._process_validation(task)
        assert result["data"]["warnings"] == 2

    def test_process_references_structure(self):
        from app.pipeline.agents.distributed import AgentRole, AgentTask, SpecialistAgent
        agent = SpecialistAgent(AgentRole.REFERENCE_SPECIALIST, tools=[])
        task = AgentTask("r1", AgentRole.REFERENCE_SPECIALIST, "/doc.pdf")
        result = agent._process_references(task)
        assert result["data"]["with_dois"] == 20


class TestDistributedCoordinatorInit:
    def test_init_defaults(self):
        from app.pipeline.agents.distributed import AgentRole, DistributedCoordinator
        dc = DistributedCoordinator()
        assert dc.max_workers == 4
        assert len(dc.specialists) == 4
        assert AgentRole.METADATA_SPECIALIST in dc.specialists
        assert AgentRole.LAYOUT_SPECIALIST in dc.specialists
        assert AgentRole.VALIDATION_SPECIALIST in dc.specialists
        assert AgentRole.REFERENCE_SPECIALIST in dc.specialists

    def test_init_custom_max_workers(self):
        from app.pipeline.agents.distributed import DistributedCoordinator
        dc = DistributedCoordinator(max_workers=8)
        assert dc.max_workers == 8

    def test_init_invalid_max_workers(self):
        from app.pipeline.agents.distributed import DistributedCoordinator
        try:
            DistributedCoordinator(max_workers=0)
            raise AssertionError()
        except ValueError as e:
            assert "max_workers" in str(e)

    def test_init_specialist_initialization_failure(self):
        with patch("app.pipeline.agents.distributed.SpecialistAgent", side_effect=RuntimeError("init fail")):
            from app.pipeline.agents.distributed import DistributedCoordinator
            dc = DistributedCoordinator()
            assert len(dc.specialists) == 0


class TestDistributedCoordinatorProcessDocument:
    def test_process_document_valid(self):
        from app.pipeline.agents.distributed import DistributedCoordinator
        dc = DistributedCoordinator()
        result = dc.process_document("/path/doc.pdf")
        assert result["document_path"] == "/path/doc.pdf"
        assert result["success"] is True
        assert len(result["specialist_results"]) == 4

    def test_process_document_empty_path(self):
        from app.pipeline.agents.distributed import DistributedCoordinator
        dc = DistributedCoordinator()
        result = dc.process_document("")
        assert result["success"] is False
        assert result["specialist_results"] == []

    def test_process_document_no_specialists(self):
        from app.pipeline.agents.distributed import DistributedCoordinator
        dc = DistributedCoordinator()
        dc.specialists = {}
        result = dc.process_document("/path/doc.pdf")
        assert result["success"] is False
        assert result["specialist_results"] == []


class TestDistributedCoordinatorProcessParallel:
    def test_process_parallel(self):
        from app.pipeline.agents.distributed import AgentRole, AgentTask, DistributedCoordinator
        dc = DistributedCoordinator()
        tasks = [
            AgentTask("m1", AgentRole.METADATA_SPECIALIST, "/doc.pdf"),
            AgentTask("l1", AgentRole.LAYOUT_SPECIALIST, "/doc.pdf"),
        ]
        results = dc._process_parallel(tasks)
        assert len(results) == 2

    def test_process_parallel_future_exception(self):
        from app.pipeline.agents.distributed import AgentRole, AgentTask, DistributedCoordinator
        dc = DistributedCoordinator()
        dc.specialists[AgentRole.METADATA_SPECIALIST].process = MagicMock(side_effect=RuntimeError("task fail"))
        tasks = [
            AgentTask("m1", AgentRole.METADATA_SPECIALIST, "/doc.pdf"),
        ]
        with patch("app.pipeline.agents.distributed.as_completed") as mock_ac:
            from concurrent.futures import Future
            f = Future()
            f.set_exception(RuntimeError("future fail"))
            mock_ac.return_value = [f]
            {f: tasks[0]}
            with patch.object(dc.specialists[AgentRole.METADATA_SPECIALIST], "process"):
                pass
            with patch("app.pipeline.agents.distributed.ThreadPoolExecutor") as mock_tpe:
                mock_tpe_instance = MagicMock()
                mock_tpe.return_value.__enter__.return_value = mock_tpe_instance
                mock_tpe_instance.submit.return_value = f
                results = dc._process_parallel(tasks)
                assert len(results) == 0 or "error" in results[0]


class TestDistributedCoordinatorGetStatistics:
    def test_get_statistics(self):
        from app.pipeline.agents.distributed import DistributedCoordinator
        dc = DistributedCoordinator()
        stats = dc.get_statistics()
        assert "specialists" in stats
        assert "total_tasks" in stats
        assert stats["total_tasks"] == 0

    def test_get_statistics_with_task_counts(self):
        from app.pipeline.agents.distributed import AgentRole, DistributedCoordinator
        dc = DistributedCoordinator()
        dc.specialists[AgentRole.METADATA_SPECIALIST].task_count = 5
        stats = dc.get_statistics()
        assert stats["total_tasks"] >= 5

    def test_get_statistics_exception_safe(self):
        from app.pipeline.agents.distributed import DistributedCoordinator
        dc = DistributedCoordinator()
        dc.specialists = None
        result = dc.get_statistics()
        assert result == {"specialists": {}, "total_tasks": 0}
