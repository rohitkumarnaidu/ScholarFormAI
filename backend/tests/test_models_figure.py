# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Dedicated tests for the Figure model.

Covers construction, serialization, enum values, image data, and helper methods.
"""

from __future__ import annotations


class TestFigureMinimumFields:
    def test_creation_with_minimum_fields(self):
        from app.models.figure import Figure

        fig = Figure(figure_id="fig_min", index=0)
        assert fig.figure_id == "fig_min"
        assert fig.index == 0
        assert fig.number is None
        assert fig.image_data is None
        assert fig.caption_text is None
        assert fig.label is None
        assert fig.is_valid is True

    def test_default_image_format_is_unknown(self):
        from app.models.figure import Figure, ImageFormat

        fig = Figure(figure_id="fig_def", index=0)
        assert fig.image_format == ImageFormat.UNKNOWN

    def test_default_figure_type_is_unknown(self):
        from app.models.figure import Figure, FigureType

        fig = Figure(figure_id="fig_def", index=0)
        assert fig.figure_type == FigureType.UNKNOWN


class TestFigureAllFields:
    def test_creation_with_all_fields(self):
        from app.models.figure import Figure, FigureType, ImageFormat

        fig = Figure(
            figure_id="fig_full",
            number=3,
            image_data=b"fake-image-bytes",
            image_format=ImageFormat.PNG,
            width=800.0,
            height=600.0,
            page_number=5,
            index=2,
            caption_text="Figure 3: System Architecture Overview",
            caption_block_id="blk_cap_003",
            label="Figure 3",
            title="System Architecture Overview",
            figure_type=FigureType.DIAGRAM,
            referenced_by=["blk_010", "blk_011"],
            section_name="Methodology",
            is_valid=True,
            warnings=["Low resolution"],
            placement="top",
            export_filename="figure_3.png",
            export_path="/exports/figures/figure_3.png",
            metadata={"dpi": 300, "color_space": "RGB"},
        )
        assert fig.figure_id == "fig_full"
        assert fig.number == 3
        assert fig.image_data == b"fake-image-bytes"
        assert fig.image_format == ImageFormat.PNG
        assert fig.width == 800.0
        assert fig.height == 600.0
        assert fig.page_number == 5
        assert fig.index == 2
        assert fig.caption_text == "Figure 3: System Architecture Overview"
        assert fig.caption_block_id == "blk_cap_003"
        assert fig.label == "Figure 3"
        assert fig.title == "System Architecture Overview"
        assert fig.figure_type == FigureType.DIAGRAM
        assert fig.referenced_by == ["blk_010", "blk_011"]
        assert fig.section_name == "Methodology"
        assert fig.is_valid is True
        assert fig.warnings == ["Low resolution"]
        assert fig.placement == "top"
        assert fig.export_filename == "figure_3.png"
        assert fig.export_path == "/exports/figures/figure_3.png"
        assert fig.metadata["dpi"] == 300


class TestFigureSerialization:
    def test_serialization_roundtrip(self):
        from app.models.figure import Figure, FigureType, ImageFormat

        fig = Figure(
            figure_id="fig_ser",
            number=1,
            image_format=ImageFormat.JPEG,
            width=1024.0,
            height=768.0,
            index=0,
            caption_text="Figure 1: Results",
            label="Figure 1",
            figure_type=FigureType.GRAPH,
            metadata={"source": "matplotlib"},
        )
        data = fig.model_dump(mode="json")
        restored = Figure(**data)
        assert restored.figure_id == fig.figure_id
        assert restored.number == fig.number
        assert restored.image_format == fig.image_format
        assert restored.width == fig.width
        assert restored.caption_text == fig.caption_text
        assert restored.figure_type == fig.figure_type

    def test_serialization_handles_bytes(self):
        from app.models.figure import Figure

        fig = Figure(
            figure_id="fig_bytes",
            index=0,
            image_data=b"\x89PNG\r\n\x1a\nraw-bytes",
        )
        data = fig.model_dump()
        assert data["image_data"] == b"\x89PNG\r\n\x1a\nraw-bytes"

    def test_use_enum_values_in_serialization(self):
        from app.models.figure import Figure, FigureType, ImageFormat

        fig = Figure(
            figure_id="fig_enum",
            index=0,
            figure_type=FigureType.CHART,
            image_format=ImageFormat.SVG,
        )
        data = fig.model_dump(mode="json")
        assert data["figure_type"] == "chart"
        assert data["image_format"] == "svg"


class TestFigureTypeEnum:
    def test_diagram_value(self):
        from app.models.figure import FigureType

        assert FigureType.DIAGRAM.value == "diagram"

    def test_chart_value(self):
        from app.models.figure import FigureType

        assert FigureType.CHART.value == "chart"

    def test_graph_value(self):
        from app.models.figure import FigureType

        assert FigureType.GRAPH.value == "graph"

    def test_photograph_value(self):
        from app.models.figure import FigureType

        assert FigureType.PHOTOGRAPH.value == "photograph"

    def test_screenshot_value(self):
        from app.models.figure import FigureType

        assert FigureType.SCREENSHOT.value == "screenshot"

    def test_illustration_value(self):
        from app.models.figure import FigureType

        assert FigureType.ILLUSTRATION.value == "illustration"

    def test_unknown_value(self):
        from app.models.figure import FigureType

        assert FigureType.UNKNOWN.value == "unknown"


class TestImageFormatEnum:
    def test_png_value(self):
        from app.models.figure import ImageFormat

        assert ImageFormat.PNG.value == "png"

    def test_jpeg_value(self):
        from app.models.figure import ImageFormat

        assert ImageFormat.JPEG.value == "jpeg"

    def test_jpg_value(self):
        from app.models.figure import ImageFormat

        assert ImageFormat.JPG.value == "jpg"

    def test_gif_value(self):
        from app.models.figure import ImageFormat

        assert ImageFormat.GIF.value == "gif"

    def test_bmp_value(self):
        from app.models.figure import ImageFormat

        assert ImageFormat.BMP.value == "bmp"

    def test_tiff_value(self):
        from app.models.figure import ImageFormat

        assert ImageFormat.TIFF.value == "tiff"

    def test_svg_value(self):
        from app.models.figure import ImageFormat

        assert ImageFormat.SVG.value == "svg"

    def test_emf_value(self):
        from app.models.figure import ImageFormat

        assert ImageFormat.EMF.value == "emf"

    def test_wmf_value(self):
        from app.models.figure import ImageFormat

        assert ImageFormat.WMF.value == "wmf"

    def test_unknown_value(self):
        from app.models.figure import ImageFormat

        assert ImageFormat.UNKNOWN.value == "unknown"


class TestFigureImageData:
    def test_with_image_data_bytes(self):
        from app.models.figure import Figure

        raw = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        fig = Figure(figure_id="fig_img", index=0, image_data=raw)
        assert fig.image_data == raw
        assert isinstance(fig.image_data, bytes)

    def test_empty_image_data(self):
        from app.models.figure import Figure

        fig = Figure(figure_id="fig_noimg", index=0)
        assert fig.image_data is None


class TestFigureCaption:
    def test_with_caption(self):
        from app.models.figure import Figure

        fig = Figure(figure_id="fig_cap", index=0, caption_text="Figure 2: Data Flow")
        assert fig.has_caption() is True

    def test_empty_caption(self):
        from app.models.figure import Figure

        fig = Figure(figure_id="fig_nocap", index=0, caption_text="")
        assert fig.has_caption() is False

    def test_whitespace_caption(self):
        from app.models.figure import Figure

        fig = Figure(figure_id="fig_wscap", index=0, caption_text="   ")
        assert fig.has_caption() is False

    def test_caption_with_title(self):
        from app.models.figure import Figure

        fig = Figure(
            figure_id="fig_ct",
            index=0,
            caption_text="Figure 4: Training Loss",
            title="Training Loss",
        )
        assert fig.title == "Training Loss"
        assert fig.has_caption() is True


class TestFigureLabel:
    def test_with_label(self):
        from app.models.figure import Figure

        fig = Figure(figure_id="fig_lbl", index=0, label="Fig. 1")
        assert fig.label == "Fig. 1"
        assert fig.get_display_label() == "Fig. 1"

    def test_label_with_number_fallback(self):
        from app.models.figure import Figure

        fig = Figure(figure_id="fig_fn", index=0, number=7)
        assert fig.get_display_label() == "Figure 7"

    def test_label_fallback_to_id(self):
        from app.models.figure import Figure

        fig = Figure(figure_id="fig_fallback", index=0)
        assert "Figure fig_fallback" in fig.get_display_label()

    def test_label_precedes_number(self):
        from app.models.figure import Figure

        fig = Figure(figure_id="fig_choice", index=0, label="Fig. A", number=99)
        assert fig.get_display_label() == "Fig. A"
