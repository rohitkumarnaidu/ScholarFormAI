# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Figure Quality Analyzer
Analyzes images for resolution, aspect ratio, and potential quality issues.
"""

import os
from typing import Dict, Any, Optional
from PIL import Image

class FigureAnalyzer:
    """
    Analyzes figure images for quality assurance.
    
    Checks:
    - Resolution (DPI estimation)
    - Aspect Ratio
    - Minimum dimension requirements
    """
    
    def __init__(self, min_width: int = 300, min_height: int = 300, min_dpi: int = 150):
        self.min_width = min_width
        self.min_height = min_height
        self.min_dpi = min_dpi
        
    def downsample_if_needed(self, image_path: str, max_size_bytes: int = 2_000_000) -> Optional[str]:
        """
        Downsample image if it exceeds size threshold.
        Returns path to downsampled image (same as input if no change needed).
        """
        if not os.path.exists(image_path):
            return None
            
        file_size = os.path.getsize(image_path)
        if file_size <= max_size_bytes:
            return image_path
            
        try:
            with Image.open(image_path) as img:
                # Maintain aspect ratio while ensuring max dimension is ~1024
                img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
                
                # Save back to same format or JPEG if memory fails
                # For safety, we save to a temporary file in the same directory
                base, ext = os.path.splitext(image_path)
                downsampled_path = f"{base}_downsampled{ext}"
                
                img.save(downsampled_path, quality=85, optimize=True)
                return downsampled_path
        except Exception as e:
            from logging import getLogger
            getLogger(__name__).error(f"Downsampling failed for {image_path}: {e}")
            return image_path

    def analyze_image(self, image_path: str) -> Dict[str, Any]:
        """
        Analyze an image file.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary containing analysis results
        """
        if not os.path.exists(image_path):
            return {"error": "File not found", "path": image_path}
            
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                format = img.format
                mode = img.mode
                
                # Estimate DPI (Pillow defaults to 72x72 if not set)
                dpi = img.info.get('dpi', (72, 72))
                if isinstance(dpi, tuple):
                    dpi_x, dpi_y = dpi
                else:
                    dpi_x = dpi_y = dpi
                    
                # Quality Checks
                issues = []
                
                if width < self.min_width or height < self.min_height:
                    issues.append(f"Low resolution: {width}x{height} (Min: {self.min_width}x{self.min_height})")
                    
                if max(dpi_x, dpi_y) < self.min_dpi:
                    issues.append(f"Low DPI: {int(max(dpi_x, dpi_y))} (Recommended: {self.min_dpi}+)")
                
                aspect_ratio = round(width / height, 2)
                
                return {
                    "valid": len(issues) == 0,
                    "width": width,
                    "height": height,
                    "dpi": f"{int(dpi_x)}x{int(dpi_y)}",
                    "format": format,
                    "mode": mode,
                    "aspect_ratio": aspect_ratio,
                    "issues": issues
                }
                
        except Exception as e:
            return {"error": f"Analysis failed: {str(e)}", "path": image_path}

# Global instance
figure_analyzer = FigureAnalyzer()
