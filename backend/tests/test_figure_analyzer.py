from unittest.mock import patch


class FakeImage:
    """Simulates PIL.Image for testing."""
    def __init__(self, size=(800, 600), mode="RGB", format="PNG", dpi=(300, 300)):
        self.size = size
        self.mode = mode
        self.format = format
        self.info = {"dpi": dpi}
    def thumbnail(self, size, resample):
        pass
    def save(self, path, **kwargs):
        pass
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass


class TestFigureAnalyzer:
    def test_analyze_image_valid(self):
        from app.pipeline.figures.analyzer import FigureAnalyzer
        with patch("PIL.Image.open", return_value=FakeImage()):
            with patch("os.path.exists", return_value=True):
                analyzer = FigureAnalyzer()
                result = analyzer.analyze_image("/path/img.png")
        assert result["valid"] is True
        assert result["width"] == 800
        assert result["height"] == 600
        assert result["aspect_ratio"] == 1.33

    def test_analyze_image_file_not_found(self):
        from app.pipeline.figures.analyzer import FigureAnalyzer
        with patch("os.path.exists", return_value=False):
            analyzer = FigureAnalyzer()
            result = analyzer.analyze_image("/nonexistent.png")
        assert result["error"] == "File not found"

    def test_analyze_image_low_resolution(self):
        from app.pipeline.figures.analyzer import FigureAnalyzer
        small_img = FakeImage(size=(100, 100))
        with patch("PIL.Image.open", return_value=small_img):
            with patch("os.path.exists", return_value=True):
                analyzer = FigureAnalyzer(min_width=300, min_height=300)
                result = analyzer.analyze_image("/path/small.png")
        assert result["valid"] is False
        assert "Low resolution" in str(result["issues"])

    def test_analyze_image_low_dpi(self):
        from app.pipeline.figures.analyzer import FigureAnalyzer
        low_dpi_img = FakeImage(size=(800, 600), dpi=(72, 72))
        with patch("PIL.Image.open", return_value=low_dpi_img):
            with patch("os.path.exists", return_value=True):
                analyzer = FigureAnalyzer(min_dpi=150)
                result = analyzer.analyze_image("/path/lowdpi.png")
        assert result["valid"] is False
        assert "Low DPI" in str(result["issues"])

    def test_analyze_image_exception(self):
        from app.pipeline.figures.analyzer import FigureAnalyzer
        with patch("PIL.Image.open", side_effect=Exception("corrupt")):
            with patch("os.path.exists", return_value=True):
                analyzer = FigureAnalyzer()
                result = analyzer.analyze_image("/path/bad.png")
        assert "Analysis failed" in result["error"]

    def test_downsample_not_needed(self, tmp_path):
        from app.pipeline.figures.analyzer import FigureAnalyzer
        f = tmp_path / "img.png"
        f.write_text("small file")
        analyzer = FigureAnalyzer()
        result = analyzer.downsample_if_needed(str(f), max_size_bytes=1_000_000)
        assert result == str(f)

    def test_downsample_file_missing(self):
        from app.pipeline.figures.analyzer import FigureAnalyzer
        analyzer = FigureAnalyzer()
        result = analyzer.downsample_if_needed("/nonexistent.png")
        assert result is None

    def test_downsample_needed(self, tmp_path):
        from app.pipeline.figures.analyzer import FigureAnalyzer
        f = tmp_path / "img.png"
        f.write_text("x" * 5_000_000)

        with patch("PIL.Image.open", return_value=FakeImage()):
            analyzer = FigureAnalyzer()
            result = analyzer.downsample_if_needed(str(f), max_size_bytes=100)
        assert result is not None
        assert "_downsampled" in result

    def test_downsample_exception(self, tmp_path):
        from app.pipeline.figures.analyzer import FigureAnalyzer
        f = tmp_path / "img.png"
        f.write_text("x" * 5_000_000)

        with patch("PIL.Image.open", side_effect=Exception("OOM")):
            analyzer = FigureAnalyzer()
            result = analyzer.downsample_if_needed(str(f), max_size_bytes=100)
        assert result == str(f)
