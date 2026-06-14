"""
Agent memory system for pattern recognition across documents.
"""
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pathlib import Path


class AgentMemory:
    """
    Memory system for the document agent to remember patterns across documents.
    
    Stores:
    - Processing patterns (successful strategies)
    - Common errors and solutions
    - Document type classifications
    - Quality metrics
    """
    
    def __init__(self, memory_dir: str = ".agent_memory"):
        """
        Initialize agent memory.
        
        Args:
            memory_dir: Directory to store memory files
        """
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(exist_ok=True)
        
        self.patterns_file = self.memory_dir / "patterns.json"
        self.errors_file = self.memory_dir / "errors.json"
        self.metrics_file = self.memory_dir / "metrics.json"
        self.corrections_file = self.memory_dir / "corrections.json"
        
        # Load existing memory
        self.patterns = self._load_json(self.patterns_file, default={})
        self.errors = self._load_json(self.errors_file, default=[])
        self.metrics = self._load_json(self.metrics_file, default={})
        self.corrections = self._load_json(self.corrections_file, default=[])
    
    def _load_json(self, file_path: Path, default: Any) -> Any:
        """Load JSON file or return default."""
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return default
        return default
    
    def _save_json(self, file_path: Path, data: Any):
        """Save data to JSON file."""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def remember_pattern(self, pattern_type: str, context: Dict[str, Any], success: bool):
        """
        Remember a processing pattern.
        
        Args:
            pattern_type: Type of pattern (e.g., "metadata_extraction", "layout_analysis")
            context: Context information (document type, tools used, etc.)
            success: Whether the pattern was successful
        """
        if pattern_type not in self.patterns:
            self.patterns[pattern_type] = {
                "successful": [],
                "failed": []
            }
        
        pattern_entry = {
            "context": context,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "count": 1
        }
        
        # Check if similar pattern exists
        target_list = self.patterns[pattern_type]["successful" if success else "failed"]
        
        # Simple deduplication: check if similar context exists
        similar_found = False
        for existing in target_list:
            if existing["context"].get("document_type") == context.get("document_type"):
                existing["count"] = existing.get("count", 1) + 1
                existing["timestamp"] = datetime.now(timezone.utc).isoformat()
                similar_found = True
                break
        
        if not similar_found:
            target_list.append(pattern_entry)
        
        self._save_json(self.patterns_file, self.patterns)
    
    def remember_error(self, error_type: str, error_message: str, solution: Optional[str] = None):
        """
        Remember an error and its solution.
        
        Args:
            error_type: Type of error
            error_message: Error message
            solution: How the error was resolved (if known)
        """
        error_entry = {
            "type": error_type,
            "message": error_message,
            "solution": solution,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "occurrences": 1
        }
        
        # Check for duplicate errors
        for existing in self.errors:
            if existing["type"] == error_type and existing["message"] == error_message:
                existing["occurrences"] += 1
                existing["timestamp"] = datetime.now(timezone.utc).isoformat()
                if solution:
                    existing["solution"] = solution
                self._save_json(self.errors_file, self.errors)
                return
        
        self.errors.append(error_entry)
        self._save_json(self.errors_file, self.errors)
    
    def record_metric(self, metric_name: str, value: float, metadata: Optional[Dict] = None):
        """
        Record a performance metric.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            metadata: Additional metadata
        """
        if metric_name not in self.metrics:
            self.metrics[metric_name] = {
                "values": [],
                "average": 0.0,
                "count": 0
            }
        
        metric = self.metrics[metric_name]
        metric["values"].append({
            "value": value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {}
        })
        
        # Keep only last 100 values
        if len(metric["values"]) > 100:
            metric["values"] = metric["values"][-100:]
        
        # Update average
        metric["count"] += 1
        metric["average"] = sum(v["value"] for v in metric["values"]) / len(metric["values"])
        
        self._save_json(self.metrics_file, self.metrics)
    
    def get_best_pattern(self, pattern_type: str, context: Dict[str, Any]) -> Optional[Dict]:
        """
        Get the best pattern for a given context.
        
        Args:
            pattern_type: Type of pattern to retrieve
            context: Current context
            
        Returns:
            Best matching pattern or None
        """
        if pattern_type not in self.patterns:
            return None
        
        successful = self.patterns[pattern_type]["successful"]
        
        if not successful:
            return None
        
        # Find best match based on document type
        doc_type = context.get("document_type", "unknown")
        
        for pattern in successful:
            if pattern["context"].get("document_type") == doc_type:
                return pattern
        
        # Return most common pattern if no exact match
        return max(successful, key=lambda p: p.get("count", 1))
    
    def get_error_solution(self, error_type: str, error_message: str) -> Optional[str]:
        """
        Get solution for a known error.
        
        Args:
            error_type: Type of error
            error_message: Error message
            
        Returns:
            Solution if known, None otherwise
        """
        for error in self.errors:
            if error["type"] == error_type and error["message"] in error_message:
                return error.get("solution")
        return None
    
    def get_metric_summary(self, metric_name: str) -> Optional[Dict]:
        """
        Get summary of a metric.
        
        Args:
            metric_name: Name of the metric
            
        Returns:
            Metric summary or None
        """
        return self.metrics.get(metric_name)
    
    def remember_correction(self, document_id: str, field: str, original_value: Any, corrected_value: Any):
        """
        Remember a user correction.
        
        Args:
            document_id: ID of the document
            field: Field that was corrected (e.g., "title", "author")
            original_value: Value predicted by the system
            corrected_value: Value provided by the user
        """
        correction_entry = {
            "document_id": document_id,
            "field": field,
            "original": original_value,
            "corrected": corrected_value,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        self.corrections.append(correction_entry)
        self._save_json(self.corrections_file, self.corrections)

    def get_memory_summary(self) -> Dict[str, Any]:
        """Get overall memory summary."""
        return {
            "patterns": {
                pattern_type: {
                    "successful_count": len(data["successful"]),
                    "failed_count": len(data["failed"])
                }
                for pattern_type, data in self.patterns.items()
            },
            "errors": {
                "total_errors": len(self.errors),
                "unique_types": len(set(e["type"] for e in self.errors))
            },
            "metrics": {
                metric_name: {
                    "average": data["average"],
                    "count": data["count"]
                }
                for metric_name, data in self.metrics.items()
            },
            "corrections": {
                "total_corrections": len(self.corrections),
                "fields": list(set(c["field"] for c in self.corrections))
            }
        }

    def format_memory_summary(self) -> str:
        """Get memory summary as a human-readable string (safe for PromptTemplate)."""
        summary = self.get_memory_summary()
        lines = ["Patterns:"]
        pat = summary.get("patterns", {})
        if pat:
            for ptype, data in pat.items():
                lines.append(
                    f"  - {ptype}: {data['successful_count']} successful, "
                    f"{data['failed_count']} failed"
                )
        else:
            lines.append("  (none)")
        err = summary.get("errors", {})
        lines.append(f"Errors: {err.get('total_errors', 0)} total, "
                     f"{err.get('unique_types', 0)} unique types")
        lines.append(f"Metrics tracked: {len(summary.get('metrics', {}))}")
        corr = summary.get("corrections", {})
        lines.append(f"Corrections: {corr.get('total_corrections', 0)} total")
        return "\n".join(lines)
