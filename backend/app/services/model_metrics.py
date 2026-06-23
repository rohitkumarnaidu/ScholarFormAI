# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Model Performance Metrics - Track AI model performance and quality.

Tracks:
- Model usage statistics
- Response times (latency)
- Success/failure rates
- Quality scores (when available)
- Fallback frequency
"""

import time
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from collections import defaultdict
from app.utils.singleton import get_or_create

logger = logging.getLogger(__name__)


class ModelMetrics:
    """Track and analyze AI model performance metrics."""
    
    def __init__(self):
        """Initialize metrics storage."""
        self.metrics = {
            "nvidia": {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "total_latency": 0.0,
                "avg_latency": 0.0,
                "last_used": None
            },
            "deepseek": {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "total_latency": 0.0,
                "avg_latency": 0.0,
                "last_used": None
            },
            "rules": {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "total_latency": 0.0,
                "avg_latency": 0.0,
                "last_used": None
            }
        }
        
        self.fallback_chain = []  # Track fallback sequences
        self.quality_scores = []  # Track quality when available
        self._persistence_enabled = True
        self._missing_table_logged = False
    
    def record_call(
        self,
        model: str,
        success: bool,
        latency: float,
        quality_score: Optional[float] = None
    ):
        """
        Record a model API call.
        
        Args:
            model: Model name ('nvidia', 'deepseek', 'rules')
            success: Whether call succeeded
            latency: Response time in seconds
            quality_score: Optional quality score (0.0 to 1.0)
        """
        model_key = model.lower()
        if model_key not in self.metrics:
            return
        
        metrics = self.metrics[model_key]
        metrics["total_calls"] += 1
        
        if success:
            metrics["successful_calls"] += 1
        else:
            metrics["failed_calls"] += 1
        
        metrics["total_latency"] += latency
        metrics["avg_latency"] = metrics["total_latency"] / metrics["total_calls"]
        metrics["last_used"] = datetime.now(timezone.utc).isoformat()
        
        if quality_score is not None:
            self.quality_scores.append({
                "model": model,
                "score": quality_score,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
        self._persist_metric(model, latency, success, quality_score)
        
    def _persist_metric(self, model: str, latency: float, success: bool, quality_score: Optional[float]):
        """Persist to Supabase in a background thread to prevent pipeline crashes."""
        import threading
        if not self._persistence_enabled:
            return
        
        def _task():
            try:
                from app.db.supabase_client import get_supabase_client
                sb = get_supabase_client()
                if not sb:
                    return
                # latency_ms as requested
                sb.table("model_metrics").insert({
                    "model_name": model,
                    "latency_ms": latency * 1000.0,
                    "success": success,
                    "quality_score": quality_score
                }).execute()
            except Exception as exc:
                import logging
                err = str(exc)
                missing_table = (
                    "model_metrics" in err
                    and ("schema cache" in err or "PGRST205" in err or "Could not find the table" in err)
                )
                if missing_table:
                    self._persistence_enabled = False
                    if not self._missing_table_logged:
                        logging.getLogger(__name__).warning(
                            "Supabase table 'model_metrics' not found; metric persistence disabled."
                        )
                        self._missing_table_logged = True
                    return
                logging.getLogger(__name__).warning("Failed to persist model metric to Supabase: %s", exc)
                
        threading.Thread(target=_task, daemon=True).start()
    
    def record_fallback(self, from_model: str, to_model: str, reason: str):
        """Record a fallback event."""
        self.fallback_chain.append({
            "from": from_model,
            "to": to_model,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        return {
            "models": self.metrics,
            "fallback_rate": len(self.fallback_chain) / max(1, sum(m["total_calls"] for m in self.metrics.values())),
            "total_fallbacks": len(self.fallback_chain),
            "avg_quality_scores": {
                model: sum(s["score"] for s in self.quality_scores if s["model"] == model) / max(1, len([s for s in self.quality_scores if s["model"] == model]))
                for model in ["nvidia", "deepseek", "rules"]
            }
        }
    
    def get_model_comparison(self) -> Dict[str, Any]:
        """Compare model performance."""
        nvidia_calls = max(1, self.metrics["nvidia"]["total_calls"])
        deepseek_calls = max(1, self.metrics["deepseek"]["total_calls"])
        rules_calls = max(1, self.metrics["rules"]["total_calls"])
        
        return {
            "nvidia_vs_deepseek": {
                "nvidia_success_rate": self.metrics["nvidia"]["successful_calls"] / nvidia_calls,
                "deepseek_success_rate": self.metrics["deepseek"]["successful_calls"] / deepseek_calls,
                "nvidia_avg_latency": self.metrics["nvidia"]["avg_latency"],
                "deepseek_avg_latency": self.metrics["deepseek"]["avg_latency"],
                "nvidia_faster": self.metrics["nvidia"]["avg_latency"] < self.metrics["deepseek"]["avg_latency"]
            },
            "agent_vs_legacy": {
                "agent_total_calls": self.metrics["nvidia"]["total_calls"] + self.metrics["deepseek"]["total_calls"],
                "legacy_total_calls": self.metrics["rules"]["total_calls"],
                "agent_success_rate": (self.metrics["nvidia"]["successful_calls"] + self.metrics["deepseek"]["successful_calls"]) / (nvidia_calls + deepseek_calls),
                "legacy_success_rate": self.metrics["rules"]["successful_calls"] / rules_calls,
                "automation_level": "High" if self.metrics["rules"]["total_calls"] < (nvidia_calls + deepseek_calls) * 0.2 else "Low - Reliance on Fallbacks"
            }
        }
    
    def export_metrics(self, filepath: str):
        """Export metrics to JSON file."""
        data = {
            "metrics": self.metrics,
            "fallback_chain": self.fallback_chain,
            "quality_scores": self.quality_scores,
            "summary": self.get_summary(),
            "comparison": self.get_model_comparison(),
            "exported_at": datetime.now(timezone.utc).isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info("Metrics exported to %s", filepath)


# Global metrics instance
_model_metrics: Optional[ModelMetrics] = None


def get_model_metrics() -> ModelMetrics:
    """Get global metrics instance."""
    global _model_metrics
    _model_metrics = get_or_create(_model_metrics, ModelMetrics)
    return _model_metrics
