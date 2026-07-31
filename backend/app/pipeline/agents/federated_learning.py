# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Federated learning across multiple deployments.
"""

import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import requests as _requests

    _REQUESTS_AVAILABLE = True
except ImportError:
    _requests = None  # type: ignore[assignment]
    _REQUESTS_AVAILABLE = False
    logger.warning("requests library not available; federated sync will be disabled.")

# Network timeouts
_HTTP_TIMEOUT = 15


class FederatedLearningNode:
    """
    Federated learning node for distributed learning.

    Features:
    - Share model updates without sharing data
    - Aggregate knowledge from multiple deployments
    - Privacy-preserving learning
    - Decentralized coordination
    """

    def __init__(
        self,
        node_id: str,
        storage_dir: str = ".federated_learning",
        coordinator_url: Optional[str] = None,
    ):
        """
        Initialize federated learning node.

        Args:
            node_id: Unique node identifier (non-empty string)
            storage_dir: Local storage directory
            coordinator_url: Optional coordinator server URL
        """
        if not node_id or not str(node_id).strip():
            raise ValueError("node_id must be a non-empty string")

        self.node_id = str(node_id).strip()
        self.coordinator_url = coordinator_url

        try:
            self.storage_dir = Path(storage_dir)
            self.storage_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            logger.error("Failed to create storage directory '%s': %s", storage_dir, exc)
            raise

        self.local_updates_file = self.storage_dir / f"node_{self.node_id}_updates.jsonl"
        self.global_model_file = self.storage_dir / "global_model.json"

        self.local_updates: List[Dict[str, Any]] = []
        self.global_model = self._load_global_model()

    def _load_global_model(self) -> Dict[str, Any]:
        """Load global model state. Returns default if file missing or corrupt."""
        default: Dict[str, Any] = {
            "version": 0,
            "patterns": [],
            "statistics": {},
            "last_updated": None,
        }
        if not self.global_model_file.exists():
            return default
        try:
            with open(self.global_model_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                logger.warning("Global model file has unexpected format; using default.")
                return default
            return data
        except Exception as exc:
            logger.error("Failed to load global model from '%s': %s", self.global_model_file, exc)
            return default

    def _save_global_model(self) -> None:
        """Save global model state. Logs error but does not raise."""
        try:
            with open(self.global_model_file, "w", encoding="utf-8") as f:
                json.dump(self.global_model, f, indent=2, default=str)
        except Exception as exc:
            logger.error("Failed to save global model: %s", exc)

    def record_local_update(self, update_type: str, data: Dict[str, Any]) -> None:
        """
        Record a local model update.

        Args:
            update_type: Type of update (pattern, metric, error, etc.)
            data: Update data
        """
        if not update_type:
            logger.warning("record_local_update called with empty update_type; skipping.")
            return
        if not isinstance(data, dict):
            logger.warning("record_local_update: data must be a dict, got %s; skipping.", type(data))
            return

        update: Dict[str, Any] = {
            "node_id": self.node_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "update_type": update_type,
            "data": data,
            "version": self.global_model.get("version", 0),
        }

        try:
            with open(self.local_updates_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(update, default=str) + "\n")
        except Exception as exc:
            logger.error("Failed to write local update to file: %s", exc)

        self.local_updates.append(update)
        logger.info("Recorded local update: %s", update_type)

    def get_local_updates(self, since_version: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get local updates since a specific version.

        Args:
            since_version: Get updates at or after this version (None = all)

        Returns:
            List of updates
        """
        try:
            if since_version is None:
                return list(self.local_updates)
            return [u for u in self.local_updates if u.get("version", 0) >= since_version]
        except Exception as exc:
            logger.error("Error in get_local_updates: %s", exc)
            return []

    def push_updates_to_coordinator(self) -> bool:
        """
        Push local updates to coordinator.

        Returns:
            True if successful, False otherwise
        """
        if not self.coordinator_url:
            logger.warning("No coordinator URL configured; skipping push.")
            return False
        if not _REQUESTS_AVAILABLE:
            logger.error("requests library not available; cannot push updates.")
            return False

        try:
            updates = self.get_local_updates()
            response = _requests.post(
                f"{self.coordinator_url}/federated/updates",
                json={"node_id": self.node_id, "updates": updates},
                timeout=_HTTP_TIMEOUT,
            )
            if response.status_code == 200:
                logger.info("Pushed %d updates to coordinator", len(updates))
                return True
            else:
                logger.error(
                    "Failed to push updates: HTTP %d - %s",
                    response.status_code,
                    response.text[:200],
                )
                return False
        except Exception as exc:
            logger.error("Failed to push updates to coordinator: %s", exc)
            return False

    def pull_global_model(self) -> bool:
        """
        Pull global model from coordinator.

        Returns:
            True if successful, False otherwise
        """
        if not self.coordinator_url:
            logger.warning("No coordinator URL configured; skipping pull.")
            return False
        if not _REQUESTS_AVAILABLE:
            logger.error("requests library not available; cannot pull global model.")
            return False

        try:
            response = _requests.get(
                f"{self.coordinator_url}/federated/global_model",
                timeout=_HTTP_TIMEOUT,
            )
            if response.status_code == 200:
                new_model = response.json()
                if not isinstance(new_model, dict):
                    logger.error("Coordinator returned unexpected model format.")
                    return False

                current_version = self.global_model.get("version", 0)
                new_version = new_model.get("version", 0)

                if new_version > current_version:
                    self.global_model = new_model
                    self._save_global_model()
                    logger.info("Updated to global model version %d", new_version)
                else:
                    logger.info("Global model is already up to date (version %d)", current_version)
                return True
            else:
                logger.error("Failed to pull global model: HTTP %d", response.status_code)
                return False
        except Exception as exc:
            logger.error("Failed to pull global model: %s", exc)
            return False

    def aggregate_updates(self, all_updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate updates from multiple nodes (coordinator function).

        Args:
            all_updates: Updates from all nodes

        Returns:
            Aggregated model dict
        """
        if not isinstance(all_updates, list):
            logger.warning("aggregate_updates: expected list, got %s", type(all_updates))
            all_updates = []

        patterns: List[Dict[str, Any]] = []
        metrics: List[Dict[str, Any]] = []

        for update in all_updates:
            if not isinstance(update, dict):
                continue
            update_type = update.get("update_type", "")
            data = update.get("data", {})
            if not isinstance(data, dict):
                continue
            if update_type == "pattern":
                patterns.append(data)
            elif update_type == "metric":
                metrics.append(data)

        aggregated_patterns = self._aggregate_patterns(patterns)
        aggregated_metrics = self._aggregate_metrics(metrics)

        try:
            contributing_nodes = len(set(u.get("node_id", "") for u in all_updates if isinstance(u, dict)))
        except Exception:
            contributing_nodes = 0

        return {
            "version": self.global_model.get("version", 0) + 1,
            "patterns": aggregated_patterns,
            "statistics": aggregated_metrics,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "contributing_nodes": contributing_nodes,
        }

    def _aggregate_patterns(self, patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Aggregate patterns from multiple nodes."""
        if not patterns:
            return []
        # Simple aggregation: keep top 10 (placeholder for real clustering)
        return patterns[:10]

    def _aggregate_metrics(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate metrics from multiple nodes."""
        if not metrics:
            return {}
        try:
            n = len(metrics)
            total_docs = sum(m.get("document_count", 0) for m in metrics)
            avg_duration = sum(m.get("avg_duration", 0.0) for m in metrics) / n
            avg_success_rate = sum(m.get("success_rate", 0.0) for m in metrics) / n
            return {
                "total_documents": total_docs,
                "avg_duration": round(avg_duration, 4),
                "avg_success_rate": round(avg_success_rate, 4),
                "contributing_nodes": n,
            }
        except Exception as exc:
            logger.error("Error aggregating metrics: %s", exc)
            return {}

    def sync(self) -> bool:
        """
        Synchronize with coordinator (push + pull).

        Returns:
            True if both push and pull succeeded
        """
        push_success = self.push_updates_to_coordinator()
        pull_success = self.pull_global_model()
        return push_success and pull_success

    def get_status(self) -> Dict[str, Any]:
        """Get node status. Always returns a valid dict."""
        try:
            return {
                "node_id": self.node_id,
                "local_updates": len(self.local_updates),
                "global_model_version": self.global_model.get("version", 0),
                "coordinator_connected": self.coordinator_url is not None,
                "last_sync": self.global_model.get("last_updated"),
            }
        except Exception as exc:
            logger.error("Error in get_status: %s", exc)
            return {"node_id": self.node_id, "error": str(exc)}


class FederatedCoordinator:
    """
    Coordinator server for federated learning.

    Aggregates updates from multiple nodes and distributes global model.
    """

    def __init__(self, storage_dir: str = ".federated_coordinator"):
        """
        Initialize federated coordinator.

        Args:
            storage_dir: Storage directory
        """
        try:
            self.storage_dir = Path(storage_dir)
            self.storage_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            logger.error("Failed to create coordinator storage dir '%s': %s", storage_dir, exc)
            raise

        self.updates_file = self.storage_dir / "all_updates.jsonl"
        self.global_model_file = self.storage_dir / "global_model.json"

        self.all_updates: List[Dict[str, Any]] = []
        self.global_model = self._load_global_model()
        self.registered_nodes: set = set()

    def _load_global_model(self) -> Dict[str, Any]:
        """Load global model. Returns default if file missing or corrupt."""
        default: Dict[str, Any] = {
            "version": 0,
            "patterns": [],
            "statistics": {},
            "last_updated": None,
        }
        if not self.global_model_file.exists():
            return default
        try:
            with open(self.global_model_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                logger.warning("Coordinator global model file has unexpected format; using default.")
                return default
            return data
        except Exception as exc:
            logger.error("Failed to load coordinator global model: %s", exc)
            return default

    def receive_updates(self, node_id: str, updates: List[Dict[str, Any]]) -> bool:
        """
        Receive updates from a node.

        Args:
            node_id: Node ID
            updates: List of updates

        Returns:
            True if successful
        """
        if not node_id:
            logger.warning("receive_updates called with empty node_id; skipping.")
            return False
        if not isinstance(updates, list):
            logger.warning("receive_updates: updates must be a list, got %s", type(updates))
            return False

        try:
            self.registered_nodes.add(node_id)

            with open(self.updates_file, "a", encoding="utf-8") as f:
                for update in updates:
                    if isinstance(update, dict):
                        f.write(json.dumps(update, default=str) + "\n")

            self.all_updates.extend(u for u in updates if isinstance(u, dict))
            logger.info("Received %d updates from node %s", len(updates), node_id)
            return True
        except Exception as exc:
            logger.error("Failed to receive updates from node %s: %s", node_id, exc)
            return False

    def aggregate_and_update(self) -> Dict[str, Any]:
        """
        Aggregate all updates and create new global model.

        Returns:
            New global model dict
        """
        try:
            temp_node = FederatedLearningNode("coordinator", str(self.storage_dir))
            temp_node.global_model = dict(self.global_model)

            new_model = temp_node.aggregate_updates(self.all_updates)

            self.global_model = new_model
            with open(self.global_model_file, "w", encoding="utf-8") as f:
                json.dump(new_model, f, indent=2, default=str)

            logger.info("Created global model version %d", new_model.get("version", 0))
            return new_model
        except Exception as exc:
            logger.error("Failed to aggregate and update global model: %s", exc)
            return dict(self.global_model)

    def get_global_model(self) -> Dict[str, Any]:
        """Get current global model."""
        return dict(self.global_model)

    def get_statistics(self) -> Dict[str, Any]:
        """Get coordinator statistics. Always returns a valid dict."""
        try:
            return {
                "registered_nodes": len(self.registered_nodes),
                "total_updates": len(self.all_updates),
                "global_model_version": self.global_model.get("version", 0),
                "last_aggregation": self.global_model.get("last_updated"),
            }
        except Exception as exc:
            logger.error("Error in FederatedCoordinator.get_statistics: %s", exc)
            return {
                "registered_nodes": 0,
                "total_updates": 0,
                "global_model_version": 0,
                "last_aggregation": None,
            }
