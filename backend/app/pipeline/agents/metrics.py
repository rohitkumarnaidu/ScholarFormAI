# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Performance metrics tracking for agent vs legacy comparison.
"""
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from pathlib import Path
import json

logger = logging.getLogger(__name__)


@dataclass
class ProcessingMetrics:
    """Metrics for a single document processing run."""
    document_id: str
    orchestrator_type: str  # "agent" or "legacy"
    start_time: float
    end_time: float
    duration_seconds: float
    success: bool
    error_message: Optional[str] = None
    
    # Quality metrics
    metadata_extracted: bool = False
    layout_analyzed: bool = False
    references_count: int = 0
    figures_count: int = 0
    validation_errors: int = 0
    validation_warnings: int = 0
    
    # Agent-specific metrics
    tools_used: List[str] = None
    retry_count: int = 0
    fallback_triggered: bool = False
    
    def __post_init__(self):
        if self.tools_used is None:
            self.tools_used = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class PerformanceTracker:
    """
    Track and compare performance between agent and legacy orchestrators.
    """
    
    def __init__(self, metrics_dir: str = ".metrics"):
        """
        Initialize performance tracker.
        
        Args:
            metrics_dir: Directory to store metrics
        """
        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(exist_ok=True)
        
        self.metrics_file = self.metrics_dir / "processing_metrics.jsonl"
        self.summary_file = self.metrics_dir / "summary.json"
        
        self.current_run: Optional[Dict[str, Any]] = None
    
    def start_tracking(self, document_id: str, orchestrator_type: str) -> Dict[str, Any]:
        """
        Start tracking a processing run.
        
        Args:
            document_id: ID of the document being processed
            orchestrator_type: "agent" or "legacy"
            
        Returns:
            Run context dictionary
        """
        self.current_run = {
            "document_id": document_id,
            "orchestrator_type": orchestrator_type,
            "start_time": time.time(),
            "tools_used": [],
            "retry_count": 0
        }
        return self.current_run
    
    def record_tool_use(self, tool_name: str):
        """Record that a tool was used."""
        if self.current_run:
            self.current_run["tools_used"].append(tool_name)
    
    def record_retry(self):
        """Record a retry attempt."""
        if self.current_run:
            self.current_run["retry_count"] += 1
    
    def end_tracking(
        self,
        success: bool,
        document: Any = None,
        error_message: Optional[str] = None,
        fallback_triggered: bool = False
    ) -> ProcessingMetrics:
        """
        End tracking and save metrics.
        
        Args:
            success: Whether processing succeeded
            document: Processed document (for quality metrics)
            error_message: Error message if failed
            fallback_triggered: Whether fallback was triggered
            
        Returns:
            ProcessingMetrics object
        """
        if not self.current_run:
            raise ValueError("No active tracking run")
        
        end_time = time.time()
        duration = end_time - self.current_run["start_time"]
        
        # Extract quality metrics from document
        quality_metrics = self._extract_quality_metrics(document) if document else {}
        
        metrics = ProcessingMetrics(
            document_id=self.current_run["document_id"],
            orchestrator_type=self.current_run["orchestrator_type"],
            start_time=self.current_run["start_time"],
            end_time=end_time,
            duration_seconds=duration,
            success=success,
            error_message=error_message,
            tools_used=self.current_run["tools_used"],
            retry_count=self.current_run["retry_count"],
            fallback_triggered=fallback_triggered,
            **quality_metrics
        )
        
        # Save metrics
        self._save_metrics(metrics)
        
        # Clear current run
        self.current_run = None
        
        return metrics
    
    def _extract_quality_metrics(self, document: Any) -> Dict[str, Any]:
        """Extract quality metrics from document."""
        try:
            return {
                "metadata_extracted": bool(document.metadata.title),
                "layout_analyzed": len(document.blocks) > 0,
                "references_count": len(document.references),
                "figures_count": len(document.figures),
                "validation_errors": len(document.validation_errors),
                "validation_warnings": len(document.validation_warnings)
            }
        except:
            return {}
    
    def _save_metrics(self, metrics: ProcessingMetrics):
        """Save metrics to file."""
        # Append to JSONL file
        with open(self.metrics_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(metrics.to_dict()) + '\n')
        
        # Update summary
        self._update_summary()
    
    def _update_summary(self):
        """Update summary statistics."""
        metrics_list = self.load_all_metrics()
        
        if not metrics_list:
            return
        
        # Separate by orchestrator type
        agent_metrics = [m for m in metrics_list if m["orchestrator_type"] == "agent"]
        legacy_metrics = [m for m in metrics_list if m["orchestrator_type"] == "legacy"]
        
        summary = {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "total_runs": len(metrics_list),
            "agent": self._calculate_stats(agent_metrics),
            "legacy": self._calculate_stats(legacy_metrics)
        }
        
        with open(self.summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
    
    def _calculate_stats(self, metrics_list: List[Dict]) -> Dict[str, Any]:
        """Calculate statistics for a set of metrics."""
        if not metrics_list:
            return {"count": 0}
        
        successful = [m for m in metrics_list if m["success"]]
        
        return {
            "count": len(metrics_list),
            "success_rate": len(successful) / len(metrics_list) if metrics_list else 0,
            "avg_duration": sum(m["duration_seconds"] for m in metrics_list) / len(metrics_list),
            "avg_references": sum(m.get("references_count", 0) for m in successful) / len(successful) if successful else 0,
            "avg_figures": sum(m.get("figures_count", 0) for m in successful) / len(successful) if successful else 0,
            "avg_validation_errors": sum(m.get("validation_errors", 0) for m in successful) / len(successful) if successful else 0,
            "fallback_rate": sum(1 for m in metrics_list if m.get("fallback_triggered", False)) / len(metrics_list) if metrics_list else 0
        }
    
    def load_all_metrics(self) -> List[Dict[str, Any]]:
        """Load all metrics from file."""
        if not self.metrics_file.exists():
            return []
        
        metrics = []
        with open(self.metrics_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    metrics.append(json.loads(line.strip()))
                except:
                    continue
        return metrics
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        if self.summary_file.exists():
            with open(self.summary_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def get_comparison(self) -> Dict[str, Any]:
        """Get agent vs legacy comparison."""
        summary = self.get_summary()
        
        if not summary or "agent" not in summary or "legacy" not in summary:
            return {"error": "Insufficient data for comparison"}
        
        agent = summary["agent"]
        legacy = summary["legacy"]
        
        return {
            "agent_vs_legacy": {
                "speed": {
                    "agent_avg_duration": agent.get("avg_duration", 0),
                    "legacy_avg_duration": legacy.get("avg_duration", 0),
                    "speedup": legacy.get("avg_duration", 1) / agent.get("avg_duration", 1) if agent.get("avg_duration") else 0
                },
                "quality": {
                    "agent_success_rate": agent.get("success_rate", 0),
                    "legacy_success_rate": legacy.get("success_rate", 0),
                    "agent_avg_errors": agent.get("avg_validation_errors", 0),
                    "legacy_avg_errors": legacy.get("avg_validation_errors", 0)
                },
                "reliability": {
                    "agent_fallback_rate": agent.get("fallback_rate", 0),
                    "agent_runs": agent.get("count", 0),
                    "legacy_runs": legacy.get("count", 0)
                }
            }
        }
