# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI


import sys
from pathlib import Path
from PIL import Image

# Add backend to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.pipeline.figures.analyzer import FigureAnalyzer
from app.services.model_metrics import ModelMetrics

def test_figure_analyzer(tmp_path):
    """Test FigureAnalyzer with a generated image."""
    analyzer = FigureAnalyzer(min_width=100, min_height=100, min_dpi=72)
    
    # Create a dummy image
    img_path = tmp_path / "test_image.png"
    img = Image.new('RGB', (200, 200), color = 'red')
    img.save(img_path, dpi=(96, 96))
    
    # Test analysis
    result = analyzer.analyze_image(str(img_path))
    
    assert result["valid"] is True
    assert result["width"] == 200
    assert result["height"] == 200
    assert "96x96" in result["dpi"]

def test_model_metrics_comparison():
    """Test Agent vs Legacy comparison logic."""
    metrics = ModelMetrics()
    
    # Simulate data
    # Agent calls (Nvidia + DeepSeek)
    # Agent calls (Nvidia + DeepSeek)
    for _ in range(10):
        metrics.record_call("nvidia", True, 0.5)
    metrics.record_call("deepseek", True, 1.0)
    
    # Legacy calls
    metrics.record_call("rules", True, 0.1)
    
    comparison = metrics.get_model_comparison()
    
    # Debug print
    print("\nDEBUG STATS:", comparison["agent_vs_legacy"])
    
    assert "agent_vs_legacy" in comparison
    stats = comparison["agent_vs_legacy"]
    
    assert stats["agent_total_calls"] == 11
    assert stats["legacy_total_calls"] == 1
    assert stats["agent_success_rate"] == 1.0
    assert stats["automation_level"] == "High"

if __name__ == "__main__":
    # Manually run if executed directly
    print("Running manual verification...")
    test_model_metrics_comparison()
    print("Metrics Verified.")
