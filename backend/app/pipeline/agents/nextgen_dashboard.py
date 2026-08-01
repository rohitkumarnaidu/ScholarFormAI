# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Next-generation analytics dashboard.
"""

import logging
from datetime import datetime

from app.pipeline.agents.autoscaling import AutoScalingManager
from app.pipeline.agents.deep_learning import TransformerPatternDetector
from app.pipeline.agents.federated_learning import FederatedLearningNode
from app.pipeline.agents.realtime_adaptation import RealTimeAdaptiveAgent
from app.pipeline.agents.tool_marketplace import ToolMarketplace

logger = logging.getLogger(__name__)


class NextGenDashboard:
    """
    Next-generation analytics dashboard with cutting-edge features.
    """

    def __init__(
        self,
        transformer_detector: TransformerPatternDetector | None = None,
        federated_node: FederatedLearningNode | None = None,
        realtime_agent: RealTimeAdaptiveAgent | None = None,
        autoscaling_manager: AutoScalingManager | None = None,
        tool_marketplace: ToolMarketplace | None = None,
    ):
        """Initialize next-gen dashboard."""
        self.transformer_detector = transformer_detector
        self.federated_node = federated_node
        self.realtime_agent = realtime_agent
        self.autoscaling_manager = autoscaling_manager
        self.tool_marketplace = tool_marketplace

    def generate_html(self, output_path: str) -> str:
        """Generate next-gen HTML dashboard."""
        html = self._build_html()

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info(f"Next-gen dashboard generated: {output_path}")
        return output_path

    def _build_html(self) -> str:
        """Build HTML content."""
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Next-Gen AI Agent Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 50%, #7e22ce 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{ max-width: 1600px; margin: 0 auto; }}
        .header {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            margin-bottom: 30px;
            border: 1px solid rgba(255,255,255,0.2);
        }}
        .header h1 {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 3em;
            margin-bottom: 10px;
            font-weight: 800;
        }}
        .header .subtitle {{
            color: #666;
            font-size: 1.3em;
            font-weight: 500;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 25px;
            margin-bottom: 25px;
        }}
        .card {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            padding: 30px;
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            border: 1px solid rgba(255,255,255,0.2);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}
        .card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.3);
        }}
        .card h2 {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 20px;
            font-size: 1.8em;
            border-bottom: 3px solid #667eea;
            padding-bottom: 12px;
            font-weight: 700;
        }}
        .metric {{
            display: flex;
            justify-content: space-between;
            padding: 12px 0;
            border-bottom: 1px solid #eee;
        }}
        .metric:last-child {{ border-bottom: none; }}
        .metric-label {{ color: #666; font-weight: 600; }}
        .metric-value {{ color: #333; font-weight: 700; font-size: 1.1em; }}
        .badge {{
            display: inline-block;
            padding: 6px 14px;
            border-radius: 25px;
            font-size: 0.9em;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .badge-success {{ background: linear-gradient(135deg, #10b981, #059669); color: white; }}
        .badge-warning {{ background: linear-gradient(135deg, #f59e0b, #d97706); color: white; }}
        .badge-info {{ background: linear-gradient(135deg, #3b82f6, #2563eb); color: white; }}
        .badge-purple {{ background: linear-gradient(135deg, #8b5cf6, #7c3aed); color: white; }}
        .feature-box {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 15px;
            margin: 15px 0;
            box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
        }}
        .feature-box h3 {{ margin-bottom: 12px; font-size: 1.4em; }}
        .stat-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin-top: 15px;
        }}
        .stat-item {{
            background: rgba(255,255,255,0.1);
            padding: 15px;
            border-radius: 10px;
            text-align: center;
        }}
        .stat-value {{
            font-size: 2em;
            font-weight: 800;
            margin-bottom: 5px;
        }}
        .stat-label {{
            font-size: 0.9em;
            opacity: 0.9;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Next-Gen AI Agent Dashboard</h1>
            <p class="subtitle">Deep Learning • Federated Learning • Real-Time Adaptation • Auto-Scaling • Tool Marketplace</p>
            <p style="font-size: 0.9em; color: #999; margin-top: 15px;">
                Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            </p>
        </div>
        
        <div class="grid">
            {self._build_transformer_section()}
            {self._build_federated_section()}
            {self._build_realtime_section()}
            {self._build_autoscaling_section()}
            {self._build_marketplace_section()}
        </div>
        
        {self._build_insights_section()}
    </div>
</body>
</html>
"""

    def _build_transformer_section(self) -> str:
        """Build transformer deep learning section."""
        if not self.transformer_detector:
            return """
            <div class="card">
                <h2>  Deep Learning (Transformers)</h2>
                <p style="color: #999;">Not initialized</p>
            </div>
            """

        summary = self.transformer_detector.get_summary()

        return f"""
        <div class="card">
            <h2>  Deep Learning (Transformers)</h2>
            <div class="metric">
                <span class="metric-label">Model:</span>
                <span class="metric-value">{summary["model_name"]}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Device:</span>
                <span class="badge badge-info">{summary["device"].upper()}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Cached Embeddings:</span>
                <span class="metric-value">{summary["cached_embeddings"]}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Clusters:</span>
                <span class="metric-value">{summary["n_clusters"]}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Status:</span>
                <span class="badge badge-{"success" if summary["clusters_trained"] else "warning"}">
                    {"Trained" if summary["clusters_trained"] else "Not Trained"}
                </span>
            </div>
        </div>
        """

    def _build_federated_section(self) -> str:
        """Build federated learning section."""
        if not self.federated_node:
            return """
            <div class="card">
                <h2>🌐 Federated Learning</h2>
                <p style="color: #999;">Not initialized</p>
            </div>
            """

        status = self.federated_node.get_status()

        return f"""
        <div class="card">
            <h2>🌐 Federated Learning</h2>
            <div class="metric">
                <span class="metric-label">Node ID:</span>
                <span class="metric-value">{status["node_id"]}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Local Updates:</span>
                <span class="metric-value">{status["local_updates"]}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Global Model Version:</span>
                <span class="metric-value">v{status["global_model_version"]}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Coordinator:</span>
                <span class="badge badge-{"success" if status["coordinator_connected"] else "warning"}">
                    {"Connected" if status["coordinator_connected"] else "Offline"}
                </span>
            </div>
        </div>
        """

    def _build_realtime_section(self) -> str:
        """Build real-time adaptation section."""
        if not self.realtime_agent:
            return """
            <div class="card">
                <h2>⚡ Real-Time Adaptation</h2>
                <p style="color: #999;">Not initialized</p>
            </div>
            """

        params = self.realtime_agent.get_current_params()

        return f"""
        <div class="card">
            <h2>⚡ Real-Time Adaptation</h2>
            <div class="metric">
                <span class="metric-label">Timeout:</span>
                <span class="metric-value">{params["timeout"]:.1f}s</span>
            </div>
            <div class="metric">
                <span class="metric-label">Retry Enabled:</span>
                <span class="badge badge-{"success" if params["retry_enabled"] else "warning"}">
                    {"Yes" if params["retry_enabled"] else "No"}
                </span>
            </div>
            <div class="metric">
                <span class="metric-label">Aggressive Mode:</span>
                <span class="badge badge-{"warning" if params["aggressive_mode"] else "info"}">
                    {"Active" if params["aggressive_mode"] else "Normal"}
                </span>
            </div>
        </div>
        """

    def _build_autoscaling_section(self) -> str:
        """Build auto-scaling section."""
        if not self.autoscaling_manager:
            return """
            <div class="card">
                <h2>📊 Auto-Scaling</h2>
                <p style="color: #999;">Not initialized</p>
            </div>
            """

        stats = self.autoscaling_manager.get_statistics()

        return f"""
        <div class="card">
            <h2>📊 Auto-Scaling</h2>
            <div class="metric">
                <span class="metric-label">Current Workers:</span>
                <span class="metric-value">{stats["current_workers"]}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Range:</span>
                <span class="metric-value">{stats["min_workers"]} - {stats["max_workers"]}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Avg CPU:</span>
                <span class="metric-value">{stats["avg_cpu_percent"]:.1f}%</span>
            </div>
            <div class="metric">
                <span class="metric-label">Scaling Events:</span>
                <span class="badge badge-info">{stats["total_scaling_events"]}</span>
            </div>
        </div>
        """

    def _build_marketplace_section(self) -> str:
        """Build tool marketplace section."""
        if not self.tool_marketplace:
            return """
            <div class="card">
                <h2> ️ Tool Marketplace</h2>
                <p style="color: #999;">Not initialized</p>
            </div>
            """

        installed = self.tool_marketplace.get_installed_tools()

        tools_html = ""
        for tool in installed[:5]:
            tools_html += f"""
            <div class="metric">
                <span>{tool["name"]}</span>
                <span class="badge badge-purple">v{tool["version"]}</span>
            </div>
            """

        return f"""
        <div class="card">
            <h2> ️ Tool Marketplace</h2>
            <div class="metric">
                <span class="metric-label">Installed Tools:</span>
                <span class="metric-value">{len(installed)}</span>
            </div>
            {tools_html}
        </div>
        """

    def _build_insights_section(self) -> str:
        """Build insights section."""
        return """
        <div class="feature-box">
            <h3>🎯 Next-Generation Capabilities</h3>
            <div class="stat-grid">
                <div class="stat-item">
                    <div class="stat-value"> </div>
                    <div class="stat-label">Transformer Models</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">🌐</div>
                    <div class="stat-label">Federated Learning</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">⚡</div>
                    <div class="stat-label">Real-Time Adaptation</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">📊</div>
                    <div class="stat-label">Auto-Scaling</div>
                </div>
            </div>
        </div>
        """
