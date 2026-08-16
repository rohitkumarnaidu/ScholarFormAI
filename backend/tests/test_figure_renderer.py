from unittest.mock import MagicMock, patch


def _make_figure(
    width=800, height=600, export_path=None, image_data=None, caption_text="Figure 1: Test caption", figure_id="fig-1"
):
    fig = MagicMock()
    fig.width = width
    fig.height = height
    fig.export_path = export_path
    fig.image_data = image_data
    fig.caption_text = caption_text
    fig.figure_id = figure_id
    return fig


class TestCalculateImageSize:
    def test_fits_within_bounds(self):
        from app.pipeline.figures.renderer import FigureRenderer

        renderer = FigureRenderer()
        fig = _make_figure(width=480, height=360)
        w, h = renderer.calculate_image_size(fig)
        assert w.inches == 5.0
        assert h.inches == 3.75

    def test_wider_than_max(self):
        from app.pipeline.figures.renderer import FigureRenderer

        renderer = FigureRenderer()
        fig = _make_figure(width=2000, height=1000)
        w, h = renderer.calculate_image_size(fig)
        assert w.inches <= 6.5

    def test_narrower_than_min(self):
        from app.pipeline.figures.renderer import FigureRenderer

        renderer = FigureRenderer()
        fig = _make_figure(width=100, height=200)
        w, h = renderer.calculate_image_size(fig)
        assert w.inches >= 2.0

    def test_no_dimensions(self):
        from app.pipeline.figures.renderer import FigureRenderer

        renderer = FigureRenderer()
        fig = _make_figure(width=None, height=None)
        w, h = renderer.calculate_image_size(fig)
        assert w.inches == 5.0
        assert h is None

    def test_taller_than_max(self):
        from app.pipeline.figures.renderer import FigureRenderer

        renderer = FigureRenderer()
        fig = _make_figure(width=200, height=2000)
        w, h = renderer.calculate_image_size(fig)
        assert h.inches <= 9.0


class TestRender:
    def test_render_from_export_path(self):
        from app.pipeline.figures.renderer import FigureRenderer

        renderer = FigureRenderer()
        fig = _make_figure(export_path="/tmp/fig.png")
        doc = MagicMock()

        with patch("os.path.exists", return_value=True):
            renderer.render(doc, fig, 1)
        doc.add_paragraph.assert_called()

    def test_render_from_image_data(self):
        from app.pipeline.figures.renderer import FigureRenderer

        renderer = FigureRenderer()
        fig = _make_figure(image_data=b"pngdata")
        doc = MagicMock()

        renderer.render(doc, fig, 1)
        doc.add_paragraph.assert_called()

    def test_render_no_data(self):
        from app.pipeline.figures.renderer import FigureRenderer

        renderer = FigureRenderer()
        fig = _make_figure(export_path=None, image_data=None)
        doc = MagicMock()

        renderer.render(doc, fig, 1)
        doc.add_paragraph.assert_called()

    def test_render_export_path_missing(self):
        from app.pipeline.figures.renderer import FigureRenderer

        renderer = FigureRenderer()
        fig = _make_figure(export_path="/tmp/missing.png")
        doc = MagicMock()

        with patch("os.path.exists", return_value=False):
            renderer.render(doc, fig, 1)
        doc.add_paragraph.assert_called()

    def test_render_export_path_exception(self):
        from app.pipeline.figures.renderer import FigureRenderer

        renderer = FigureRenderer()
        fig = _make_figure(export_path="/tmp/fig.png")
        doc = MagicMock()
        doc.add_paragraph.side_effect = Exception("doc error")

        with patch("os.path.exists", return_value=True):
            renderer.render(doc, fig, 1)
        doc.add_paragraph.assert_called()


class TestAddCaption:
    def test_caption_with_prefix(self):
        from app.pipeline.figures.renderer import FigureRenderer

        renderer = FigureRenderer()
        fig = _make_figure(caption_text="Figure 1: Some caption", figure_id="fig-1")
        doc = MagicMock()
        cap_para = MagicMock()
        doc.add_paragraph.return_value = cap_para

        renderer._add_caption(doc, fig, 1)
        doc.add_paragraph.assert_called_with(style="Caption")

    def test_caption_without_prefix(self):
        from app.pipeline.figures.renderer import FigureRenderer

        renderer = FigureRenderer()
        fig = _make_figure(caption_text="A generic caption", figure_id="fig-1")
        doc = MagicMock()

        renderer._add_caption(doc, fig, 1)
        doc.add_paragraph.assert_called_with(style="Caption")

    def test_no_caption(self):
        from app.pipeline.figures.renderer import FigureRenderer

        renderer = FigureRenderer()
        fig = _make_figure(caption_text="", figure_id="fig-1")
        doc = MagicMock()

        renderer._add_caption(doc, fig, 1)
        doc.add_paragraph.assert_not_called()
