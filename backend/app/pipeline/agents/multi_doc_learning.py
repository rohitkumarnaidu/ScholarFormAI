# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Multi-document learning for cross-document insights.
"""
import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# Maximum quality trend entries to keep in memory
_MAX_QUALITY_TRENDS = 100


class MultiDocumentLearner:
    """
    Learn patterns across multiple documents.

    Tracks:
    - Document type patterns
    - Author patterns
    - Venue patterns
    - Quality trends
    """

    def __init__(self, storage_dir: str = ".multi_doc_learning"):
        """
        Initialize multi-document learner.

        Args:
            storage_dir: Directory to store learning data
        """
        try:
            self.storage_dir = Path(storage_dir)
            self.storage_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            logger.error("Failed to create storage directory '%s': %s", storage_dir, exc)
            raise

        self.document_db = self.storage_dir / "documents.jsonl"
        self.insights_file = self.storage_dir / "insights.json"

        self.insights = self._load_insights()

    def _load_insights(self) -> Dict[str, Any]:
        """Load existing insights. Returns default structure on any error."""
        default: Dict[str, Any] = {
            "author_patterns": {},
            "venue_patterns": {},
            "document_types": {},
            "quality_trends": [],
        }
        if not self.insights_file.exists():
            return default
        try:
            with open(self.insights_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                logger.warning("Insights file has unexpected format; using default.")
                return default
            # Ensure all expected keys exist
            for key in default:
                data.setdefault(key, default[key])
            return data
        except Exception as exc:
            logger.error("Failed to load insights from '%s': %s", self.insights_file, exc)
            return default

    def _save_insights(self) -> None:
        """Save insights to file. Logs error but does not raise."""
        try:
            with open(self.insights_file, "w", encoding="utf-8") as f:
                json.dump(self.insights, f, indent=2, default=str)
        except Exception as exc:
            logger.error("Failed to save insights: %s", exc)

    def record_document(
        self,
        document_id: str,
        metadata: Dict[str, Any],
        metrics: Dict[str, Any],
    ) -> None:
        """
        Record a processed document.

        Args:
            document_id: Document ID (non-empty string)
            metadata: Document metadata (title, authors, venue, etc.)
            metrics: Processing metrics
        """
        if not document_id:
            logger.warning("record_document called with empty document_id; skipping.")
            return
        if not isinstance(metadata, dict):
            logger.warning("record_document: metadata must be a dict; using empty dict.")
            metadata = {}
        if not isinstance(metrics, dict):
            logger.warning("record_document: metrics must be a dict; using empty dict.")
            metrics = {}

        record: Dict[str, Any] = {
            "document_id": document_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata,
            "metrics": metrics,
        }

        try:
            with open(self.document_db, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, default=str) + "\n")
        except Exception as exc:
            logger.error("Failed to write document record to DB: %s", exc)

        # Update insights regardless of file write success
        try:
            self._update_insights(metadata, metrics)
        except Exception as exc:
            logger.error("Failed to update insights for document '%s': %s", document_id, exc)

    def _update_insights(self, metadata: Dict[str, Any], metrics: Dict[str, Any]) -> None:
        """Update insights based on new document."""
        # Author patterns
        authors = metadata.get("authors", [])
        if isinstance(authors, list):
            for author in authors:
                if not isinstance(author, str) or not author:
                    continue
                if author not in self.insights["author_patterns"]:
                    self.insights["author_patterns"][author] = {
                        "document_count": 0,
                        "avg_references": 0.0,
                        "avg_quality": 0.0,
                    }
                pattern = self.insights["author_patterns"][author]
                pattern["document_count"] += 1
                n = pattern["document_count"]
                pattern["avg_references"] = (
                    (pattern["avg_references"] * (n - 1) + float(metrics.get("references_count", 0))) / n
                )
                pattern["avg_quality"] = (
                    (pattern["avg_quality"] * (n - 1) + (1.0 if metrics.get("success", False) else 0.0)) / n
                )

        # Venue patterns
        venue = str(metadata.get("venue", "unknown") or "unknown")
        if venue not in self.insights["venue_patterns"]:
            self.insights["venue_patterns"][venue] = {
                "document_count": 0,
                "avg_references": 0.0,
                "avg_figures": 0.0,
            }
        vp = self.insights["venue_patterns"][venue]
        vp["document_count"] += 1
        n = vp["document_count"]
        vp["avg_references"] = (
            (vp["avg_references"] * (n - 1) + float(metrics.get("references_count", 0))) / n
        )
        vp["avg_figures"] = (
            (vp["avg_figures"] * (n - 1) + float(metrics.get("figures_count", 0))) / n
        )

        # Document type patterns
        doc_type = str(metadata.get("document_type", "unknown") or "unknown")
        if doc_type not in self.insights["document_types"]:
            self.insights["document_types"][doc_type] = {
                "count": 0,
                "avg_duration": 0.0,
            }
        tp = self.insights["document_types"][doc_type]
        tp["count"] += 1
        n = tp["count"]
        tp["avg_duration"] = (
            (tp["avg_duration"] * (n - 1) + float(metrics.get("duration_seconds", 0))) / n
        )

        # Quality trends
        self.insights["quality_trends"].append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "success": bool(metrics.get("success", False)),
                "errors": int(metrics.get("validation_errors", 0)),
            }
        )

        # Keep only last N trends
        if len(self.insights["quality_trends"]) > _MAX_QUALITY_TRENDS:
            self.insights["quality_trends"] = self.insights["quality_trends"][-_MAX_QUALITY_TRENDS:]

        self._save_insights()

    def get_author_insights(self, author: str) -> Optional[Dict[str, Any]]:
        """Get insights for a specific author. Returns None if not found."""
        if not author:
            return None
        try:
            return self.insights["author_patterns"].get(author)
        except Exception as exc:
            logger.error("Error in get_author_insights('%s'): %s", author, exc)
            return None

    def get_venue_insights(self, venue: str) -> Optional[Dict[str, Any]]:
        """Get insights for a specific venue. Returns None if not found."""
        if not venue:
            return None
        try:
            return self.insights["venue_patterns"].get(venue)
        except Exception as exc:
            logger.error("Error in get_venue_insights('%s'): %s", venue, exc)
            return None

    def get_similar_documents(
        self,
        metadata: Dict[str, Any],
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Find similar documents based on metadata.

        Args:
            metadata: Document metadata
            limit: Maximum number of similar documents (>= 1)

        Returns:
            List of similar documents sorted by similarity score
        """
        if not isinstance(metadata, dict):
            logger.warning("get_similar_documents: metadata must be a dict.")
            return []
        limit = max(1, int(limit))

        if not self.document_db.exists():
            return []

        similar: List[Dict[str, Any]] = []
        target_authors = set(metadata.get("authors", []))
        target_venue = str(metadata.get("venue", "") or "")

        try:
            with open(self.document_db, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        doc = json.loads(line)
                        if not isinstance(doc, dict):
                            continue
                        doc_meta = doc.get("metadata", {})
                        if not isinstance(doc_meta, dict):
                            continue
                        doc_authors = set(doc_meta.get("authors", []))
                        doc_venue = str(doc_meta.get("venue", "") or "")

                        score = 0
                        if target_authors & doc_authors:
                            score += 2
                        if target_venue and target_venue == doc_venue:
                            score += 1

                        if score > 0:
                            similar.append(
                                {
                                    "document_id": doc.get("document_id", ""),
                                    "similarity_score": score,
                                    "metadata": doc_meta,
                                    "metrics": doc.get("metrics", {}),
                                }
                            )
                    except json.JSONDecodeError as exc:
                        logger.debug("Skipping malformed line in document DB: %s", exc)
                    except Exception as exc:
                        logger.warning("Error processing document DB line: %s", exc)
        except Exception as exc:
            logger.error("Failed to read document DB: %s", exc)
            return []

        similar.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
        return similar[:limit]

    def get_insights_summary(self) -> Dict[str, Any]:
        """Get summary of all insights. Always returns a valid dict."""
        try:
            top_authors = sorted(
                self.insights.get("author_patterns", {}).items(),
                key=lambda x: x[1].get("document_count", 0),
                reverse=True,
            )[:5]
            top_venues = sorted(
                self.insights.get("venue_patterns", {}).items(),
                key=lambda x: x[1].get("document_count", 0),
                reverse=True,
            )[:5]
            return {
                "total_authors": len(self.insights.get("author_patterns", {})),
                "total_venues": len(self.insights.get("venue_patterns", {})),
                "document_types": len(self.insights.get("document_types", {})),
                "quality_trend_count": len(self.insights.get("quality_trends", [])),
                "top_authors": top_authors,
                "top_venues": top_venues,
            }
        except Exception as exc:
            logger.error("Error in get_insights_summary: %s", exc)
            return {
                "total_authors": 0,
                "total_venues": 0,
                "document_types": 0,
                "quality_trend_count": 0,
                "top_authors": [],
                "top_venues": [],
            }
