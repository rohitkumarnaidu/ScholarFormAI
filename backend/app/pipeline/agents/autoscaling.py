# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Auto-scaling for dynamic specialist pool sizing.
"""

import logging
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor
import time

logger = logging.getLogger(__name__)

try:
    import psutil

    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False
    logger.warning("psutil not available; system metrics will return defaults.")


class AutoScalingManager:
    """
    Manage auto-scaling of specialist agent pools.

    Features:
    - Monitor system resources (CPU, memory)
    - Scale specialist pool up/down dynamically
    - Load balancing across specialists
    - Resource-aware scheduling
    """

    def __init__(
        self,
        min_workers: int = 2,
        max_workers: int = 8,
        target_cpu_percent: float = 70.0,
        target_memory_percent: float = 80.0,
    ):
        """
        Initialize auto-scaling manager.

        Args:
            min_workers: Minimum number of workers (>= 1)
            max_workers: Maximum number of workers (>= min_workers)
            target_cpu_percent: Target CPU utilization (0-100)
            target_memory_percent: Target memory utilization (0-100)
        """
        if min_workers < 1:
            raise ValueError(f"min_workers must be >= 1, got {min_workers}")
        if max_workers < min_workers:
            raise ValueError(f"max_workers ({max_workers}) must be >= min_workers ({min_workers})")
        if not (0.0 < target_cpu_percent <= 100.0):
            raise ValueError(f"target_cpu_percent must be in (0, 100], got {target_cpu_percent}")
        if not (0.0 < target_memory_percent <= 100.0):
            raise ValueError(f"target_memory_percent must be in (0, 100], got {target_memory_percent}")

        self.min_workers = min_workers
        self.max_workers = max_workers
        self.target_cpu_percent = target_cpu_percent
        self.target_memory_percent = target_memory_percent

        self.current_workers = min_workers
        self.executor = ThreadPoolExecutor(max_workers=min_workers)

        self.metrics_history: List[Dict[str, float]] = []
        self.scaling_events: List[Dict[str, Any]] = []

    def get_system_metrics(self) -> Dict[str, float]:
        """
        Get current system metrics.

        Returns:
            System metrics dict. Falls back to safe defaults if psutil unavailable.
        """
        if not _PSUTIL_AVAILABLE:
            return {
                "cpu_percent": 0.0,
                "memory_percent": 0.0,
                "memory_available_gb": 0.0,
                "timestamp": time.time(),
            }
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            return {
                "cpu_percent": float(cpu_percent),
                "memory_percent": float(memory.percent),
                "memory_available_gb": float(memory.available / (1024**3)),
                "timestamp": time.time(),
            }
        except Exception as exc:
            logger.error("Failed to get system metrics: %s", exc)
            return {
                "cpu_percent": 0.0,
                "memory_percent": 0.0,
                "memory_available_gb": 0.0,
                "timestamp": time.time(),
            }

    def should_scale_up(self, metrics: Dict[str, float]) -> bool:
        """
        Determine if should scale up.

        Args:
            metrics: Current system metrics

        Returns:
            True if should scale up
        """
        try:
            cpu = metrics.get("cpu_percent", 0.0)
            mem = metrics.get("memory_percent", 0.0)

            # Scale up if CPU is high and we have capacity
            if cpu > self.target_cpu_percent and self.current_workers < self.max_workers:
                return True

            # Scale up if CPU is moderate and memory is available
            if cpu > 50 and mem < self.target_memory_percent and self.current_workers < self.max_workers:
                return True
        except Exception as exc:
            logger.error("Error in should_scale_up: %s", exc)
        return False

    def should_scale_down(self, metrics: Dict[str, float]) -> bool:
        """
        Determine if should scale down.

        Args:
            metrics: Current system metrics

        Returns:
            True if should scale down
        """
        try:
            cpu = metrics.get("cpu_percent", 0.0)
            mem = metrics.get("memory_percent", 0.0)

            # Scale down if CPU is low
            if cpu < 30 and self.current_workers > self.min_workers:
                return True

            # Scale down if memory is high
            if mem > self.target_memory_percent and self.current_workers > self.min_workers:
                return True
        except Exception as exc:
            logger.error("Error in should_scale_down: %s", exc)
        return False

    def scale_up(self) -> None:
        """Scale up the worker pool. Safe – never raises."""
        try:
            new_workers = min(self.current_workers + 1, self.max_workers)

            if new_workers > self.current_workers:
                old_executor = self.executor
                self.executor = ThreadPoolExecutor(max_workers=new_workers)
                old_executor.shutdown(wait=False)

                old_workers = self.current_workers
                self.current_workers = new_workers

                self.scaling_events.append(
                    {
                        "type": "scale_up",
                        "from": old_workers,
                        "to": new_workers,
                        "timestamp": time.time(),
                    }
                )
                logger.info("Scaled up from %d to %d workers", old_workers, new_workers)
        except Exception as exc:
            logger.error("Error during scale_up: %s", exc)

    def scale_down(self) -> None:
        """Scale down the worker pool. Safe – never raises."""
        try:
            new_workers = max(self.current_workers - 1, self.min_workers)

            if new_workers < self.current_workers:
                old_executor = self.executor
                self.executor = ThreadPoolExecutor(max_workers=new_workers)
                # Graceful shutdown of old executor
                old_executor.shutdown(wait=True)

                old_workers = self.current_workers
                self.current_workers = new_workers

                self.scaling_events.append(
                    {
                        "type": "scale_down",
                        "from": old_workers,
                        "to": new_workers,
                        "timestamp": time.time(),
                    }
                )
                logger.info("Scaled down from %d to %d workers", old_workers, new_workers)
        except Exception as exc:
            logger.error("Error during scale_down: %s", exc)

    def auto_scale(self) -> None:
        """Perform auto-scaling based on current metrics. Safe – never raises."""
        try:
            metrics = self.get_system_metrics()
            self.metrics_history.append(metrics)

            # Keep only recent history
            if len(self.metrics_history) > 100:
                self.metrics_history = self.metrics_history[-100:]

            # Make scaling decision
            if self.should_scale_up(metrics):
                self.scale_up()
            elif self.should_scale_down(metrics):
                self.scale_down()
        except Exception as exc:
            logger.error("Error in auto_scale: %s", exc)

    def get_executor(self) -> ThreadPoolExecutor:
        """
        Get current executor, triggering an auto-scale check first.

        Returns:
            Thread pool executor
        """
        self.auto_scale()
        return self.executor

    def get_statistics(self) -> Dict[str, Any]:
        """Get scaling statistics. Always returns a valid dict."""
        try:
            recent_metrics = self.metrics_history[-10:] if self.metrics_history else []
            n = len(recent_metrics)

            avg_cpu = sum(m.get("cpu_percent", 0.0) for m in recent_metrics) / n if n > 0 else 0.0
            avg_memory = sum(m.get("memory_percent", 0.0) for m in recent_metrics) / n if n > 0 else 0.0

            return {
                "current_workers": self.current_workers,
                "min_workers": self.min_workers,
                "max_workers": self.max_workers,
                "avg_cpu_percent": round(avg_cpu, 2),
                "avg_memory_percent": round(avg_memory, 2),
                "total_scaling_events": len(self.scaling_events),
                "scale_up_count": sum(1 for e in self.scaling_events if e.get("type") == "scale_up"),
                "scale_down_count": sum(1 for e in self.scaling_events if e.get("type") == "scale_down"),
            }
        except Exception as exc:
            logger.error("Error in get_statistics: %s", exc)
            return {
                "current_workers": self.current_workers,
                "min_workers": self.min_workers,
                "max_workers": self.max_workers,
                "avg_cpu_percent": 0.0,
                "avg_memory_percent": 0.0,
                "total_scaling_events": 0,
                "scale_up_count": 0,
                "scale_down_count": 0,
            }

    def shutdown(self) -> None:
        """Shutdown the executor gracefully. Safe – never raises."""
        try:
            self.executor.shutdown(wait=True)
            logger.info("AutoScalingManager executor shut down.")
        except Exception as exc:
            logger.error("Error during shutdown: %s", exc)
