# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Advanced analytics dashboard for ML insights.
"""

import logging
from typing import Optional
import json
from datetime import datetime
from app.pipeline.agents.ml_patterns import MLPatternDetector
from app.pipeline.agents.multi_doc_learning import MultiDocumentLearner
from app.pipeline.agents.adaptive import AdaptiveStrategy
from app.pipeline.agents.distributed import DistributedCoordinator

logger = logging.getLogger(__name__)


class AdvancedAnalyticsDashboard:
    """
    Advanced analytics dashboard with ML insights.
    """

    def __init__(
        self,
        ml_detector: Optional[MLPatternDetector] = None,
        multi_doc_learner: Optional[MultiDocumentLearner] = None,
        adaptive_strategy: Optional[AdaptiveStrategy] = None,
        distributed_coord: Optional[DistributedCoordinator] = None,
    ):
        """
        Initialize advanced analytics dashboard.

        Args:
            ml_detector: ML pattern detector
            multi_doc_learner: Multi-document learner
            adaptive_strategy: Adaptive strategy
            distributed_coord: Distributed coordinator
        """
        self.ml_detector = ml_detector
        self.multi_doc_learner = multi_doc_learner
        self.adaptive_strategy = adaptive_strategy
        self.distributed_coord = distributed_coord

    def generate_html(self, output_path: str) -> str:
        """
        Generate advanced HTML dashboard.

        Args:
            output_path: Output file path

        Returns:
            Path to generated dashboard
        """
        html = self._build_html()

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info(f"Advanced dashboard generated: {output_path}")
        return output_path

    def _build_html(self) -> str:
        """Build HTML content."""
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Advanced Agent Analytics</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        .header {{
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 30px;
        }}
        .header h1 {{
            color: #667eea;
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .header p {{
            color: #666;
            font-size: 1.1em;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        .card {{
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }}
        .card h2 {{
            color: #667eea;
            margin-bottom: 15px;
            font-size: 1.5em;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        .metric {{
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }}
        .metric:last-child {{ border-bottom: none; }}
        .metric-label {{
            color: #666;
            font-weight: 500;
        }}
        .metric-value {{
            color: #333;
            font-weight: bold;
        }}
        .badge {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
        }}
        .badge-success {{ background: #10b981; color: white; }}
        .badge-warning {{ background: #f59e0b; color: white; }}
        .badge-info {{ background: #3b82f6; color: white; }}
        .pattern-list {{
            list-style: none;
            padding: 0;
        }}
        .pattern-item {{
            background: #f8f9fa;
            padding: 15px;
            margin: 10px 0;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}
        .insight-box {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin: 15px 0;
        }}
        .insight-box h3 {{
            margin-bottom: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Advanced Agent Analytics</h1>
            <p>ML-Powered Insights & Multi-Agent Coordination</p>
            <p style="font-size: 0.9em; color: #999; margin-top: 10px;">
                Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            </p>
        </div>
        
        <div class="grid">
            {self._build_ml_patterns_section()}
            {self._build_multi_doc_section()}
            {self._build_adaptive_section()}
            {self._build_distributed_section()}
        </div>
        
        {self._build_insights_section()}
    </div>
</body>
</html>
"""

    def _build_ml_patterns_section(self) -> str:
        """Build ML patterns section."""
        if not self.ml_detector:
            return """
            <div class="card">
                <h2>ML Pattern Detection</h2>
                <p style="color: #999;">Not initialized</p>
            </div>
            """

        summary = self.ml_detector.get_pattern_summary()
        patterns_html = ""

        for pattern in summary.get("patterns", [])[:5]:
            patterns_html += f"""
            <div class="pattern-item">
                <strong>Pattern #{pattern["cluster_id"]}</strong>
                <div class="metric">
                    <span>Samples:</span>
                    <span>{pattern["sample_count"]}</span>
                </div>
                <div class="metric">
                    <span>Avg Duration:</span>
                    <span>{pattern["avg_duration"]:.1f}s</span>
                </div>
                <div class="metric">
                    <span>Success Rate:</span>
                    <span class="badge badge-success">{pattern["success_rate"]:.1%}</span>
                </div>
            </div>
            """

        return f"""
        <div class="card">
            <h2>ML Pattern Detection</h2>
            <div class="metric">
                <span class="metric-label">Patterns Detected:</span>
                <span class="metric-value">{summary["pattern_count"]}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Model Status:</span>
                <span class="badge badge-{"success" if summary["trained"] else "warning"}">
                    {"Trained" if summary["trained"] else "Not Trained"}
                </span>
            </div>
            <ul class="pattern-list">
                {patterns_html}
            </ul>
        </div>
        """

    def _build_multi_doc_section(self) -> str:
        """Build multi-document learning section."""
        if not self.multi_doc_learner:
            return """
            <div class="card">
                <h2>Multi-Document Learning</h2>
                <p style="color: #999;">Not initialized</p>
            </div>
            """

        summary = self.multi_doc_learner.get_insights_summary()

        top_authors_html = ""
        for author, data in summary.get("top_authors", [])[:3]:
            top_authors_html += f"""
            <div class="metric">
                <span>{author[:30]}...</span>
                <span class="badge badge-info">{data["document_count"]} docs</span>
            </div>
            """

        return f"""
        <div class="card">
            <h2>Multi-Document Learning</h2>
            <div class="metric">
                <span class="metric-label">Total Authors:</span>
                <span class="metric-value">{summary["total_authors"]}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Total Venues:</span>
                <span class="metric-value">{summary["total_venues"]}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Document Types:</span>
                <span class="metric-value">{summary["document_types"]}</span>
            </div>
            <h3 style="margin-top: 15px; color: #667eea;">Top Authors</h3>
            {top_authors_html}
        </div>
        """

    def _build_adaptive_section(self) -> str:
        """Build adaptive strategy section."""
        if not self.adaptive_strategy:
            return """
            <div class="card">
                <h2>Adaptive Strategies</h2>
                <p style="color: #999;">Not initialized</p>
            </div>
            """

        config = self.adaptive_strategy.get_config()

        return f"""
        <div class="card">
            <h2>Adaptive Strategies</h2>
            <div class="metric">
                <span class="metric-label">Max Retries:</span>
                <span class="metric-value">{config["max_retries"]}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Timeout:</span>
                <span class="metric-value">{config["timeout_seconds"]}s</span>
            </div>
            <div class="metric">
                <span class="metric-label">Fallback Threshold:</span>
                <span class="metric-value">{config["fallback_threshold"]:.1%}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Caching:</span>
                <span class="badge badge-{"success" if config["enable_caching"] else "warning"}">
                    {"Enabled" if config["enable_caching"] else "Disabled"}
                </span>
            </div>
        </div>
        """

    def _build_distributed_section(self) -> str:
        """Build distributed processing section."""
        if not self.distributed_coord:
            return """
            <div class="card">
                <h2>Distributed Processing</h2>
                <p style="color: #999;">Not initialized</p>
            </div>
            """

        stats = self.distributed_coord.get_statistics()

        specialists_html = ""
        for name, data in stats["specialists"].items():
            specialists_html += f"""
            <div class="metric">
                <span>{name.replace("_", " ").title()}:</span>
                <span class="badge badge-info">{data["task_count"]} tasks</span>
            </div>
            """

        return f"""
        <div class="card">
            <h2>Distributed Processing</h2>
            <div class="metric">
                <span class="metric-label">Total Tasks:</span>
                <span class="metric-value">{stats["total_tasks"]}</span>
            </div>
            <h3 style="margin-top: 15px; color: #667eea;">Specialists</h3>
            {specialists_html}
        </div>
        """

    def _build_insights_section(self) -> str:
        """Build insights section."""
        insights = []

        if self.ml_detector and self.ml_detector.patterns:
            best_pattern = max(self.ml_detector.patterns, key=lambda p: p.get("success_rate", 0))
            insights.append(f"""
            <div class="insight-box">
                <h3>Best Performing Pattern</h3>
                <p>Pattern #{best_pattern["cluster_id"]} has a {best_pattern["success_rate"]:.1%} success rate 
                with {best_pattern["sample_count"]} samples. Average processing time: {best_pattern["avg_duration"]:.1f}s</p>
            </div>
            """)

        if self.multi_doc_learner:
            summary = self.multi_doc_learner.get_insights_summary()
            if summary["top_authors"]:
                top_author, data = summary["top_authors"][0]
                insights.append(f"""
                <div class="insight-box">
                    <h3>Most Prolific Author</h3>
                    <p>{top_author} has {data["document_count"]} documents with an average of 
                    {data["avg_references"]:.0f} references per paper.</p>
                </div>
                """)

        return "".join(insights) if insights else ""

    def generate_json_report(self, output_path: str) -> str:
        """Generate JSON report."""
        report = {
            "generated_at": datetime.now().isoformat(),
            "ml_patterns": self.ml_detector.get_pattern_summary() if self.ml_detector else None,
            "multi_doc_insights": self.multi_doc_learner.get_insights_summary() if self.multi_doc_learner else None,
            "adaptive_config": self.adaptive_strategy.get_config() if self.adaptive_strategy else None,
            "distributed_stats": self.distributed_coord.get_statistics() if self.distributed_coord else None,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        return output_path
