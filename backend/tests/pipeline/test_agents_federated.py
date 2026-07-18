# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch, mock_open
import pytest

pytestmark = [pytest.mark.pipeline]


class TestFederatedLearningNodeInit:
    def test_init_valid(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        storage = str(tmp_path / "fl")
        node = FederatedLearningNode("node1", storage_dir=storage)
        assert node.node_id == "node1"
        assert node.coordinator_url is None
        assert node.storage_dir.exists()
        assert node.local_updates == []
        assert node.global_model["version"] == 0

    def test_init_empty_node_id(self):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        try:
            FederatedLearningNode("")
            assert False
        except ValueError as e:
            assert "node_id" in str(e)

    def test_init_whitespace_node_id(self):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        try:
            FederatedLearningNode("   ")
            assert False
        except ValueError as e:
            assert "node_id" in str(e)

    def test_init_with_coordinator_url(self):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("node1", coordinator_url="http://coord:8000", storage_dir=".")
        assert node.coordinator_url == "http://coord:8000"

    def test_init_storage_dir_creation_failure(self):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        with patch("pathlib.Path.mkdir", side_effect=PermissionError("no permission")):
            try:
                FederatedLearningNode("node1", storage_dir="/invalid/path")
                assert False
            except PermissionError:
                pass


class TestFederatedLearningNodeLoadGlobalModel:
    def test_load_default_when_missing(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("node1", storage_dir=str(tmp_path / "f1"))
        model = node._load_global_model()
        assert model["version"] == 0
        assert model["patterns"] == []
        assert model["last_updated"] is None

    def test_load_valid_file(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        storage = tmp_path / "f2"
        storage.mkdir()
        model_file = storage / "global_model.json"
        model_file.write_text(json.dumps({"version": 5, "patterns": [{"p": 1}], "statistics": {}, "last_updated": "now"}))
        node = FederatedLearningNode("node1", storage_dir=str(storage))
        assert node.global_model["version"] == 5
        assert node.global_model["patterns"] == [{"p": 1}]

    def test_load_corrupt_file(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        storage = tmp_path / "f3"
        storage.mkdir()
        model_file = storage / "global_model.json"
        model_file.write_text("not valid json")
        node = FederatedLearningNode("node1", storage_dir=str(storage))
        assert node.global_model["version"] == 0

    def test_load_non_dict_file(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        storage = tmp_path / "f4"
        storage.mkdir()
        model_file = storage / "global_model.json"
        model_file.write_text(json.dumps(["list", "not", "dict"]))
        node = FederatedLearningNode("node1", storage_dir=str(storage))
        assert node.global_model["version"] == 0


class TestFederatedLearningNodeSaveGlobalModel:
    def test_save_global_model(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        storage = str(tmp_path / "f5")
        node = FederatedLearningNode("node1", storage_dir=storage)
        node.global_model["version"] = 42
        node._save_global_model()
        saved = json.loads((tmp_path / "f5" / "global_model.json").read_text())
        assert saved["version"] == 42

    def test_save_global_model_exception(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("node1", storage_dir=str(tmp_path / "f6"))
        with patch("builtins.open", side_effect=PermissionError("denied")):
            node._save_global_model()


class TestFederatedLearningNodeRecordLocalUpdate:
    def test_record_update(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        storage = str(tmp_path / "f7")
        node = FederatedLearningNode("node1", storage_dir=storage)
        node.record_local_update("pattern", {"key": "value"})
        assert len(node.local_updates) == 1
        assert node.local_updates[0]["update_type"] == "pattern"
        assert node.local_updates[0]["data"]["key"] == "value"

    def test_record_update_empty_type(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        storage = str(tmp_path / "f8")
        node = FederatedLearningNode("node1", storage_dir=storage)
        node.record_local_update("", {"key": "value"})
        assert len(node.local_updates) == 0

    def test_record_update_non_dict_data(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        storage = str(tmp_path / "f9")
        node = FederatedLearningNode("node1", storage_dir=storage)
        node.record_local_update("metric", "not_a_dict")
        assert len(node.local_updates) == 0

    def test_record_update_file_write_exception(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        storage = str(tmp_path / "f10")
        node = FederatedLearningNode("node1", storage_dir=storage)
        with patch("builtins.open", side_effect=PermissionError("denied")):
            node.record_local_update("pattern", {"key": "value"})
            assert len(node.local_updates) == 1

    def test_record_update_creates_jsonl(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        storage = str(tmp_path / "f11")
        node = FederatedLearningNode("node1", storage_dir=storage)
        node.record_local_update("pattern", {"k": "v"})
        lines = (tmp_path / "f11" / "node_node1_updates.jsonl").read_text().strip().split("\n")
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["update_type"] == "pattern"

    def test_record_update_multiple(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        storage = str(tmp_path / "f12")
        node = FederatedLearningNode("node1", storage_dir=storage)
        node.record_local_update("pattern", {"i": 1})
        node.record_local_update("metric", {"i": 2})
        assert len(node.local_updates) == 2


class TestFederatedLearningNodeGetLocalUpdates:
    def test_get_all_updates(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        storage = str(tmp_path / "f13")
        node = FederatedLearningNode("node1", storage_dir=storage)
        node.record_local_update("pattern", {"i": 1})
        node.record_local_update("metric", {"i": 2})
        updates = node.get_local_updates()
        assert len(updates) == 2

    def test_get_updates_since_version(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        storage = str(tmp_path / "f14")
        node = FederatedLearningNode("node1", storage_dir=storage)
        node.record_local_update("pattern", {"i": 1})
        node.global_model = {"version": 1}
        node.record_local_update("metric", {"i": 2})
        updates = node.get_local_updates(since_version=1)
        assert len(updates) == 1
        assert updates[0]["update_type"] == "metric"

    def test_get_updates_empty(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        storage = str(tmp_path / "f15")
        node = FederatedLearningNode("node1", storage_dir=storage)
        updates = node.get_local_updates()
        assert updates == []

    def test_get_updates_exception_safe(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("node1", storage_dir=str(tmp_path / "f16"))
        node.local_updates = [{"version": 1}]
        node.local_updates = None
        updates = node.get_local_updates()
        assert updates == []


class TestFederatedLearningNodePushUpdates:
    def test_push_no_coordinator(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("node1", storage_dir=str(tmp_path / "f17"))
        result = node.push_updates_to_coordinator()
        assert result is False

    def test_push_requests_unavailable(self, tmp_path):
        with patch("app.pipeline.agents.federated_learning._REQUESTS_AVAILABLE", False):
            from app.pipeline.agents.federated_learning import FederatedLearningNode
            node = FederatedLearningNode("node1", storage_dir=str(tmp_path / "f18"), coordinator_url="http://coord:8000")
            result = node.push_updates_to_coordinator()
            assert result is False

    def test_push_success(self, tmp_path):
        with patch("app.pipeline.agents.federated_learning._REQUESTS_AVAILABLE", True):
            with patch("app.pipeline.agents.federated_learning._requests") as mock_requests:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_requests.post.return_value = mock_response
                from app.pipeline.agents.federated_learning import FederatedLearningNode
                node = FederatedLearningNode("node1", storage_dir=str(tmp_path / "f19"), coordinator_url="http://coord:8000")
                node.record_local_update("pattern", {"k": "v"})
                result = node.push_updates_to_coordinator()
                assert result is True
                mock_requests.post.assert_called_once()

    def test_push_http_error(self, tmp_path):
        with patch("app.pipeline.agents.federated_learning._REQUESTS_AVAILABLE", True):
            with patch("app.pipeline.agents.federated_learning._requests") as mock_requests:
                mock_response = MagicMock()
                mock_response.status_code = 500
                mock_response.text = "Internal Server Error"
                mock_requests.post.return_value = mock_response
                from app.pipeline.agents.federated_learning import FederatedLearningNode
                node = FederatedLearningNode("node1", storage_dir=str(tmp_path / "f20"), coordinator_url="http://coord:8000")
                result = node.push_updates_to_coordinator()
                assert result is False

    def test_push_exception(self, tmp_path):
        with patch("app.pipeline.agents.federated_learning._REQUESTS_AVAILABLE", True):
            with patch("app.pipeline.agents.federated_learning._requests") as mock_requests:
                mock_requests.post.side_effect = RuntimeError("connection failed")
                from app.pipeline.agents.federated_learning import FederatedLearningNode
                node = FederatedLearningNode("node1", storage_dir=str(tmp_path / "f21"), coordinator_url="http://coord:8000")
                result = node.push_updates_to_coordinator()
                assert result is False


class TestFederatedLearningNodePullGlobalModel:
    def test_pull_no_coordinator(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("node1", storage_dir=str(tmp_path / "f22"))
        result = node.pull_global_model()
        assert result is False

    def test_pull_requests_unavailable(self, tmp_path):
        with patch("app.pipeline.agents.federated_learning._REQUESTS_AVAILABLE", False):
            from app.pipeline.agents.federated_learning import FederatedLearningNode
            node = FederatedLearningNode("node1", storage_dir=str(tmp_path / "f23"), coordinator_url="http://coord:8000")
            result = node.pull_global_model()
            assert result is False

    def test_pull_new_version(self, tmp_path):
        with patch("app.pipeline.agents.federated_learning._REQUESTS_AVAILABLE", True):
            with patch("app.pipeline.agents.federated_learning._requests") as mock_requests:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"version": 10, "patterns": [], "statistics": {}, "last_updated": "now"}
                mock_requests.get.return_value = mock_response
                from app.pipeline.agents.federated_learning import FederatedLearningNode
                storage = str(tmp_path / "f24")
                node = FederatedLearningNode("node1", storage_dir=storage)
                node.coordinator_url = "http://coord:8000"
                result = node.pull_global_model()
                assert result is True
                assert node.global_model["version"] == 10

    def test_pull_same_version(self, tmp_path):
        with patch("app.pipeline.agents.federated_learning._REQUESTS_AVAILABLE", True):
            with patch("app.pipeline.agents.federated_learning._requests") as mock_requests:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"version": 0, "patterns": [], "statistics": {}, "last_updated": "now"}
                mock_requests.get.return_value = mock_response
                from app.pipeline.agents.federated_learning import FederatedLearningNode
                storage = str(tmp_path / "f25")
                node = FederatedLearningNode("node1", storage_dir=storage)
                node.coordinator_url = "http://coord:8000"
                result = node.pull_global_model()
                assert result is True
                assert node.global_model["version"] == 0

    def test_pull_http_error(self, tmp_path):
        with patch("app.pipeline.agents.federated_learning._REQUESTS_AVAILABLE", True):
            with patch("app.pipeline.agents.federated_learning._requests") as mock_requests:
                mock_response = MagicMock()
                mock_response.status_code = 404
                mock_requests.get.return_value = mock_response
                from app.pipeline.agents.federated_learning import FederatedLearningNode
                node = FederatedLearningNode("node1", storage_dir=str(tmp_path / "f26"), coordinator_url="http://coord:8000")
                result = node.pull_global_model()
                assert result is False

    def test_pull_non_dict_response(self, tmp_path):
        with patch("app.pipeline.agents.federated_learning._REQUESTS_AVAILABLE", True):
            with patch("app.pipeline.agents.federated_learning._requests") as mock_requests:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = ["not", "a", "dict"]
                mock_requests.get.return_value = mock_response
                from app.pipeline.agents.federated_learning import FederatedLearningNode
                node = FederatedLearningNode("node1", storage_dir=str(tmp_path / "f27"), coordinator_url="http://coord:8000")
                result = node.pull_global_model()
                assert result is False

    def test_pull_exception(self, tmp_path):
        with patch("app.pipeline.agents.federated_learning._REQUESTS_AVAILABLE", True):
            with patch("app.pipeline.agents.federated_learning._requests") as mock_requests:
                mock_requests.get.side_effect = RuntimeError("timeout")
                from app.pipeline.agents.federated_learning import FederatedLearningNode
                node = FederatedLearningNode("node1", storage_dir=str(tmp_path / "f28"), coordinator_url="http://coord:8000")
                result = node.pull_global_model()
                assert result is False


class TestFederatedLearningNodeAggregateUpdates:
    def test_aggregate_updates_non_list(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("node1", storage_dir=str(tmp_path / "f29"))
        result = node.aggregate_updates("not_a_list")
        assert "version" in result

    def test_aggregate_updates_empty(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("node1", storage_dir=str(tmp_path / "f30"))
        result = node.aggregate_updates([])
        assert result["patterns"] == []
        assert result["statistics"] == {}
        assert result["contributing_nodes"] == 0

    def test_aggregate_updates_with_patterns(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("node1", storage_dir=str(tmp_path / "f31"))
        updates = [
            {"node_id": "n1", "update_type": "pattern", "data": {"p": 1}},
            {"node_id": "n2", "update_type": "pattern", "data": {"p": 2}},
        ]
        result = node.aggregate_updates(updates)
        assert len(result["patterns"]) == 2
        assert result["contributing_nodes"] == 2

    def test_aggregate_updates_with_metrics(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("node1", storage_dir=str(tmp_path / "f32"))
        updates = [
            {"node_id": "n1", "update_type": "metric", "data": {"document_count": 10, "avg_duration": 5.0, "success_rate": 0.9}},
            {"node_id": "n2", "update_type": "metric", "data": {"document_count": 20, "avg_duration": 15.0, "success_rate": 0.8}},
        ]
        result = node.aggregate_updates(updates)
        assert result["statistics"]["total_documents"] == 30
        assert result["statistics"]["avg_duration"] == 10.0
        assert result["statistics"]["avg_success_rate"] == 0.85
        assert result["statistics"]["contributing_nodes"] == 2

    def test_aggregate_updates_skips_non_dict(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("node1", storage_dir=str(tmp_path / "f33"))
        updates = [
            {"node_id": "n1", "update_type": "pattern", "data": {"p": 1}},
            "not_a_dict",
            {"node_id": "n2", "update_type": "metric", "data": {}},
        ]
        result = node.aggregate_updates(updates)
        assert result["contributing_nodes"] == 2

    def test_aggregate_updates_non_dict_data_skipped(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("node1", storage_dir=str(tmp_path / "f34"))
        updates = [
            {"node_id": "n1", "update_type": "pattern", "data": "not_a_dict"},
        ]
        result = node.aggregate_updates(updates)
        assert result["patterns"] == []


class TestFederatedLearningNodeAggregatePatterns:
    def test_aggregate_patterns_empty(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("node1", storage_dir=str(tmp_path / "f35"))
        result = node._aggregate_patterns([])
        assert result == []

    def test_aggregate_patterns_truncates_to_10(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("node1", storage_dir=str(tmp_path / "f36"))
        patterns = [{"id": i} for i in range(20)]
        result = node._aggregate_patterns(patterns)
        assert len(result) == 10


class TestFederatedLearningNodeAggregateMetrics:
    def test_aggregate_metrics_empty(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("node1", storage_dir=str(tmp_path / "f37"))
        result = node._aggregate_metrics([])
        assert result == {}

    def test_aggregate_metrics_exception(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("node1", storage_dir=str(tmp_path / "f38"))
        result = node._aggregate_metrics([None])
        assert result == {}


class TestFederatedLearningNodeSync:
    def test_sync_both_success(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("node1", storage_dir=str(tmp_path / "f39"), coordinator_url="http://coord:8000")
        with patch.object(node, "push_updates_to_coordinator", return_value=True):
            with patch.object(node, "pull_global_model", return_value=True):
                assert node.sync() is True

    def test_sync_push_fails(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("node1", storage_dir=str(tmp_path / "f40"), coordinator_url="http://coord:8000")
        with patch.object(node, "push_updates_to_coordinator", return_value=False):
            with patch.object(node, "pull_global_model", return_value=True):
                assert node.sync() is False

    def test_sync_both_fail(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("node1", storage_dir=str(tmp_path / "f41"), coordinator_url="http://coord:8000")
        with patch.object(node, "push_updates_to_coordinator", return_value=False):
            with patch.object(node, "pull_global_model", return_value=False):
                assert node.sync() is False


class TestFederatedLearningNodeGetStatus:
    def test_get_status(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        storage = str(tmp_path / "f42")
        node = FederatedLearningNode("node1", storage_dir=storage)
        node.record_local_update("pattern", {"k": "v"})
        status = node.get_status()
        assert status["node_id"] == "node1"
        assert status["local_updates"] == 1
        assert status["global_model_version"] == 0
        assert status["coordinator_connected"] is False

    def test_get_status_with_coordinator(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("node1", storage_dir=str(tmp_path / "f43"), coordinator_url="http://coord:8000")
        status = node.get_status()
        assert status["coordinator_connected"] is True

    def test_get_status_exception_safe(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedLearningNode
        node = FederatedLearningNode("node1", storage_dir=str(tmp_path / "f44"))
        node.global_model = None
        status = node.get_status()
        assert status["node_id"] == "node1"
        assert "error" in status


class TestFederatedCoordinatorInit:
    def test_init_defaults(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedCoordinator
        storage = str(tmp_path / "fc1")
        coord = FederatedCoordinator(storage_dir=storage)
        assert coord.storage_dir.exists()
        assert coord.all_updates == []
        assert coord.global_model["version"] == 0
        assert coord.registered_nodes == set()

    def test_init_storage_failure(self):
        from app.pipeline.agents.federated_learning import FederatedCoordinator
        with patch("pathlib.Path.mkdir", side_effect=PermissionError("no permission")):
            try:
                FederatedCoordinator(storage_dir="/invalid/path")
                assert False
            except PermissionError:
                pass


class TestFederatedCoordinatorLoadGlobalModel:
    def test_load_default_when_missing(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedCoordinator
        coord = FederatedCoordinator(storage_dir=str(tmp_path / "fc2"))
        model = coord._load_global_model()
        assert model["version"] == 0

    def test_load_valid_file(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedCoordinator
        storage = tmp_path / "fc3"
        storage.mkdir()
        (storage / "global_model.json").write_text(json.dumps({"version": 3, "patterns": [], "statistics": {}, "last_updated": "now"}))
        coord = FederatedCoordinator(storage_dir=str(storage))
        assert coord.global_model["version"] == 3

    def test_load_corrupt_file(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedCoordinator
        storage = tmp_path / "fc4"
        storage.mkdir()
        (storage / "global_model.json").write_text("corrupt")
        coord = FederatedCoordinator(storage_dir=str(storage))
        assert coord.global_model["version"] == 0

    def test_load_non_dict(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedCoordinator
        storage = tmp_path / "fc5"
        storage.mkdir()
        (storage / "global_model.json").write_text(json.dumps(["list"]))
        coord = FederatedCoordinator(storage_dir=str(storage))
        assert coord.global_model["version"] == 0


class TestFederatedCoordinatorReceiveUpdates:
    def test_receive_updates_valid(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedCoordinator
        storage = str(tmp_path / "fc6")
        coord = FederatedCoordinator(storage_dir=storage)
        result = coord.receive_updates("node1", [{"update_type": "pattern", "data": {"p": 1}}])
        assert result is True
        assert "node1" in coord.registered_nodes
        assert len(coord.all_updates) == 1

    def test_receive_updates_empty_node_id(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedCoordinator
        coord = FederatedCoordinator(storage_dir=str(tmp_path / "fc7"))
        result = coord.receive_updates("", [{"update_type": "pattern"}])
        assert result is False

    def test_receive_updates_non_list(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedCoordinator
        coord = FederatedCoordinator(storage_dir=str(tmp_path / "fc8"))
        result = coord.receive_updates("node1", "not_a_list")
        assert result is False

    def test_receive_updates_skips_non_dict(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedCoordinator
        storage = str(tmp_path / "fc9")
        coord = FederatedCoordinator(storage_dir=storage)
        result = coord.receive_updates("node1", [{"valid": True}, "invalid", {"also_valid": True}])
        assert result is True
        assert len(coord.all_updates) == 2

    def test_receive_updates_file_exception(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedCoordinator
        coord = FederatedCoordinator(storage_dir=str(tmp_path / "fc10"))
        with patch("builtins.open", side_effect=PermissionError("denied")):
            result = coord.receive_updates("node1", [{"update_type": "pattern"}])
            assert result is False


class TestFederatedCoordinatorAggregateAndUpdate:
    def test_aggregate_and_update(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedCoordinator
        storage = str(tmp_path / "fc11")
        coord = FederatedCoordinator(storage_dir=storage)
        coord.all_updates = [
            {"node_id": "n1", "update_type": "pattern", "data": {"p": 1}},
            {"node_id": "n2", "update_type": "metric", "data": {"document_count": 10, "avg_duration": 5.0, "success_rate": 0.9}},
        ]
        result = coord.aggregate_and_update()
        assert result["version"] == 1
        assert coord.global_model["version"] == 1
        saved = json.loads((tmp_path / "fc11" / "global_model.json").read_text())
        assert saved["version"] == 1

    def test_aggregate_and_update_exception(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedCoordinator
        storage = str(tmp_path / "fc12")
        coord = FederatedCoordinator(storage_dir=storage)
        with patch.object(coord, "global_model", {"version": 0}):
            with patch("app.pipeline.agents.federated_learning.FederatedLearningNode.aggregate_updates", side_effect=RuntimeError("agg fail")):
                result = coord.aggregate_and_update()
                assert result == {"version": 0}


class TestFederatedCoordinatorGetGlobalModel:
    def test_get_global_model(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedCoordinator
        coord = FederatedCoordinator(storage_dir=str(tmp_path / "fc13"))
        model = coord.get_global_model()
        assert model["version"] == 0

    def test_get_global_model_returns_copy(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedCoordinator
        coord = FederatedCoordinator(storage_dir=str(tmp_path / "fc14"))
        model = coord.get_global_model()
        model["version"] = 999
        assert coord.global_model["version"] == 0


class TestFederatedCoordinatorGetStatistics:
    def test_get_statistics(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedCoordinator
        coord = FederatedCoordinator(storage_dir=str(tmp_path / "fc15"))
        coord.registered_nodes.add("node1")
        coord.all_updates = [{"u": 1}, {"u": 2}]
        stats = coord.get_statistics()
        assert stats["registered_nodes"] == 1
        assert stats["total_updates"] == 2
        assert stats["global_model_version"] == 0

    def test_get_statistics_exception_safe(self, tmp_path):
        from app.pipeline.agents.federated_learning import FederatedCoordinator
        coord = FederatedCoordinator(storage_dir=str(tmp_path / "fc16"))
        coord.registered_nodes = None
        stats = coord.get_statistics()
        assert stats["registered_nodes"] == 0
