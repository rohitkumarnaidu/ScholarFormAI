# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Performance comparison dashboard generator.
"""
import json
from typing import Dict, Any
from pathlib import Path
from app.pipeline.agents.metrics import PerformanceTracker


class ComparisonDashboard:
    """
    Generate HTML dashboard for agent vs legacy comparison.
    """
    
    def __init__(self, tracker: PerformanceTracker):
        """
        Initialize dashboard generator.
        
        Args:
            tracker: PerformanceTracker instance
        """
        self.tracker = tracker
    
    def generate_html(self, output_path: str = "dashboard.html") -> str:
        """
        Generate HTML dashboard.
        
        Args:
            output_path: Path to save HTML file
            
        Returns:
            Path to generated HTML file
        """
        summary = self.tracker.get_summary()
        comparison = self.tracker.get_comparison()
        
        html = self._build_html(summary, comparison)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return output_path
    
    def _build_html(self, summary: Dict, comparison: Dict) -> str:
        """Build HTML content."""
        agent_stats = summary.get("agent", {})
        legacy_stats = summary.get("legacy", {})
        comp = comparison.get("agent_vs_legacy", {})
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Agent vs Legacy Performance Dashboard</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .stat-card {{
            background: #f9f9f9;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #4CAF50;
        }}
        .stat-card.agent {{
            border-left-color: #2196F3;
        }}
        .stat-card.legacy {{
            border-left-color: #FF9800;
        }}
        .stat-label {{
            font-size: 14px;
            color: #666;
            margin-bottom: 5px;
        }}
        .stat-value {{
            font-size: 28px;
            font-weight: bold;
            color: #333;
        }}
        .comparison-section {{
            margin: 30px 0;
            padding: 20px;
            background: #f0f8ff;
            border-radius: 8px;
        }}
        .winner {{
            color: #4CAF50;
            font-weight: bold;
        }}
        .loser {{
            color: #f44336;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #4CAF50;
            color: white;
        }}
        .metric-bar {{
            height: 20px;
            background: #e0e0e0;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }}
        .metric-fill {{
            height: 100%;
            background: linear-gradient(90deg, #4CAF50, #45a049);
            transition: width 0.3s;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Agent vs Legacy Performance Dashboard</h1>
        <p>Last Updated: {summary.get('last_updated', 'N/A')}</p>
        
        <h2>📊 Overall Statistics</h2>
        <div class="stats-grid">
            <div class="stat-card agent">
                <div class="stat-label">Agent Runs</div>
                <div class="stat-value">{agent_stats.get('count', 0)}</div>
            </div>
            <div class="stat-card legacy">
                <div class="stat-label">Legacy Runs</div>
                <div class="stat-value">{legacy_stats.get('count', 0)}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Runs</div>
                <div class="stat-value">{summary.get('total_runs', 0)}</div>
            </div>
        </div>
        
        <h2>⚡ Performance Comparison</h2>
        <div class="comparison-section">
            <h3>Speed</h3>
            <table>
                <tr>
                    <th>Metric</th>
                    <th>Agent</th>
                    <th>Legacy</th>
                    <th>Winner</th>
                </tr>
                <tr>
                    <td>Avg Duration (seconds)</td>
                    <td>{comp.get('speed', {}).get('agent_avg_duration', 0):.2f}</td>
                    <td>{comp.get('speed', {}).get('legacy_avg_duration', 0):.2f}</td>
                    <td class="{'winner' if comp.get('speed', {}).get('agent_avg_duration', 999) < comp.get('speed', {}).get('legacy_avg_duration', 0) else 'loser'}">
                        {'Agent' if comp.get('speed', {}).get('agent_avg_duration', 999) < comp.get('speed', {}).get('legacy_avg_duration', 0) else 'Legacy'}
                    </td>
                </tr>
            </table>
            
            <h3>Quality</h3>
            <table>
                <tr>
                    <th>Metric</th>
                    <th>Agent</th>
                    <th>Legacy</th>
                    <th>Winner</th>
                </tr>
                <tr>
                    <td>Success Rate</td>
                    <td>{comp.get('quality', {}).get('agent_success_rate', 0):.1%}</td>
                    <td>{comp.get('quality', {}).get('legacy_success_rate', 0):.1%}</td>
                    <td class="{'winner' if comp.get('quality', {}).get('agent_success_rate', 0) > comp.get('quality', {}).get('legacy_success_rate', 0) else 'loser'}">
                        {'Agent' if comp.get('quality', {}).get('agent_success_rate', 0) > comp.get('quality', {}).get('legacy_success_rate', 0) else 'Legacy'}
                    </td>
                </tr>
                <tr>
                    <td>Avg Validation Errors</td>
                    <td>{comp.get('quality', {}).get('agent_avg_errors', 0):.2f}</td>
                    <td>{comp.get('quality', {}).get('legacy_avg_errors', 0):.2f}</td>
                    <td class="{'winner' if comp.get('quality', {}).get('agent_avg_errors', 999) < comp.get('quality', {}).get('legacy_avg_errors', 0) else 'loser'}">
                        {'Agent' if comp.get('quality', {}).get('agent_avg_errors', 999) < comp.get('quality', {}).get('legacy_avg_errors', 0) else 'Legacy'}
                    </td>
                </tr>
            </table>
            
            <h3>Reliability</h3>
            <div class="stat-card agent">
                <div class="stat-label">Agent Fallback Rate</div>
                <div class="stat-value">{comp.get('reliability', {}).get('agent_fallback_rate', 0):.1%}</div>
                <div class="metric-bar">
                    <div class="metric-fill" style="width: {comp.get('reliability', {}).get('agent_fallback_rate', 0) * 100}%"></div>
                </div>
            </div>
        </div>
        
        <h2>📈 Detailed Metrics</h2>
        <div class="stats-grid">
            <div class="stat-card agent">
                <div class="stat-label">Agent Avg References</div>
                <div class="stat-value">{agent_stats.get('avg_references', 0):.1f}</div>
            </div>
            <div class="stat-card legacy">
                <div class="stat-label">Legacy Avg References</div>
                <div class="stat-value">{legacy_stats.get('avg_references', 0):.1f}</div>
            </div>
            <div class="stat-card agent">
                <div class="stat-label">Agent Avg Figures</div>
                <div class="stat-value">{agent_stats.get('avg_figures', 0):.1f}</div>
            </div>
            <div class="stat-card legacy">
                <div class="stat-label">Legacy Avg Figures</div>
                <div class="stat-value">{legacy_stats.get('avg_figures', 0):.1f}</div>
            </div>
        </div>
    </div>
</body>
</html>
"""
        return html
    
    def generate_json_report(self, output_path: str = "comparison_report.json") -> str:
        """
        Generate JSON comparison report.
        
        Args:
            output_path: Path to save JSON file
            
        Returns:
            Path to generated JSON file
        """
        comparison = self.tracker.get_comparison()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(comparison, f, indent=2)
        
        return output_path
