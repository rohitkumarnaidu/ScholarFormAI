from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class HeadingStyle:
    font_family: str = "Times New Roman"
    font_size: int = 14
    bold: bool = True
    italic: bool = False
    alignment: str = "left"
    space_before: int = 12
    space_after: int = 6
    level: int = 1


@dataclass
class FormattingStyle:
    id: str
    name: str
    version: str
    description: str
    citation_format: str
    font_family: str = "Times New Roman"
    font_size: int = 12
    line_spacing: float = 2.0
    margin_inches: float = 1.0
    heading_styles: dict[int, dict[str, Any]] = field(default_factory=dict)
    page_numbers: bool = True
    running_header: bool = True
    title_page: bool = True
    abstract_required: bool = True
    keywords_required: bool = True
    reference_format: str = "hanging"
    first_line_indent: float = 0.5
    paragraph_spacing: float = 0.0


class StyleRegistry:
    _styles: dict[str, FormattingStyle] = {}

    def __init__(self):
        self._register_builtin_styles()

    def _register_builtin_styles(self):
        self._styles["apa"] = FormattingStyle(
            id="apa",
            name="APA 7th Edition",
            version="7.0",
            description=(
                "American Psychological Association 7th edition style. "
                "Widely used in social sciences, psychology, education, and nursing."
            ),
            citation_format="apa",
            font_family="Times New Roman",
            font_size=12,
            line_spacing=2.0,
            margin_inches=1.0,
            heading_styles={
                1: {"font_size": 14, "bold": True, "alignment": "center"},
                2: {"font_size": 12, "bold": True, "alignment": "left"},
                3: {"font_size": 12, "bold": True, "italic": True, "alignment": "left"},
                4: {
                    "font_size": 12,
                    "bold": False,
                    "italic": True,
                    "alignment": "left",
                    "indented": True,
                },
            },
            first_line_indent=0.5,
            reference_format="hanging",
            running_header=True,
        )

        self._styles["mla"] = FormattingStyle(
            id="mla",
            name="MLA 9th Edition",
            version="9.0",
            description=(
                "Modern Language Association 9th edition. Standard for humanities, literature, and language arts."
            ),
            citation_format="mla",
            font_family="Times New Roman",
            font_size=12,
            line_spacing=2.0,
            margin_inches=1.0,
            heading_styles={1: {"font_size": 12, "bold": False, "alignment": "left"}},
            first_line_indent=0.5,
            reference_format="hanging",
            running_header=False,
        )

        self._styles["chicago"] = FormattingStyle(
            id="chicago",
            name="Chicago Manual of Style 17th Edition",
            version="17.0",
            description=(
                "Chicago Manual of Style 17th edition (Notes & Bibliography). Used in history, arts, and humanities."
            ),
            citation_format="chicago",
            font_family="Times New Roman",
            font_size=12,
            line_spacing=2.0,
            margin_inches=1.0,
            heading_styles={
                1: {"font_size": 14, "bold": True, "alignment": "center"},
                2: {"font_size": 12, "bold": True, "alignment": "center"},
                3: {"font_size": 12, "bold": False, "italic": True, "alignment": "left"},
            },
            first_line_indent=0.5,
            reference_format="hanging",
            running_header=False,
        )

        self._styles["ieee"] = FormattingStyle(
            id="ieee",
            name="IEEE Citation Guide",
            version="2023",
            description=(
                "Institute of Electrical and Electronics Engineers style. "
                "Standard for engineering, computer science, and technology."
            ),
            citation_format="ieee",
            font_family="Times New Roman",
            font_size=10,
            line_spacing=1.15,
            margin_inches=1.0,
            heading_styles={
                1: {"font_size": 12, "bold": True, "alignment": "center"},
                2: {"font_size": 11, "bold": True, "alignment": "left"},
                3: {"font_size": 10, "bold": True, "italic": True, "alignment": "left"},
            },
            first_line_indent=0.0,
            reference_format="numbered",
            running_header=False,
        )

        self._styles["harvard"] = FormattingStyle(
            id="harvard",
            name="Harvard Referencing Style",
            version="2023",
            description=(
                "Harvard referencing style. Widely used in UK and Australian universities across many disciplines."
            ),
            citation_format="harvard",
            font_family="Times New Roman",
            font_size=12,
            line_spacing=1.5,
            margin_inches=1.0,
            heading_styles={1: {"font_size": 14, "bold": True, "alignment": "left"}},
            first_line_indent=0.0,
            reference_format="hanging",
            running_header=False,
        )

        self._styles["vancouver"] = FormattingStyle(
            id="vancouver",
            name="Vancouver Style",
            version="2023",
            description=("Vancouver referencing style. Standard for biomedical and health sciences journals."),
            citation_format="vancouver",
            font_family="Times New Roman",
            font_size=12,
            line_spacing=1.5,
            margin_inches=1.0,
            heading_styles={1: {"font_size": 13, "bold": True, "alignment": "left"}},
            first_line_indent=0.0,
            reference_format="numbered",
            running_header=False,
        )

        self._styles["turabian"] = FormattingStyle(
            id="turabian",
            name="Turabian 9th Edition",
            version="9.0",
            description=(
                "Turabian style (based on Chicago). Designed for student research papers, theses, and dissertations."
            ),
            citation_format="chicago",
            font_family="Times New Roman",
            font_size=12,
            line_spacing=2.0,
            margin_inches=1.0,
            heading_styles={
                1: {"font_size": 14, "bold": True, "alignment": "center"},
                2: {"font_size": 12, "bold": True, "alignment": "center"},
            },
            first_line_indent=0.5,
            reference_format="hanging",
            running_header=False,
            title_page=True,
        )

        self._styles["acs"] = FormattingStyle(
            id="acs",
            name="ACS Style Guide",
            version="2023",
            description=("American Chemical Society style. Standard for chemistry and related sciences."),
            citation_format="acs",
            font_family="Times New Roman",
            font_size=12,
            line_spacing=1.5,
            margin_inches=1.0,
            heading_styles={1: {"font_size": 13, "bold": True, "alignment": "left"}},
            first_line_indent=0.0,
            reference_format="numbered",
            running_header=False,
        )

        self._styles["ama"] = FormattingStyle(
            id="ama",
            name="AMA Manual of Style 11th Edition",
            version="11.0",
            description=("American Medical Association style. Standard for medical research and health sciences."),
            citation_format="ama",
            font_family="Times New Roman",
            font_size=12,
            line_spacing=2.0,
            margin_inches=1.0,
            heading_styles={1: {"font_size": 13, "bold": True, "alignment": "left"}},
            first_line_indent=0.0,
            reference_format="numbered",
            running_header=False,
        )

    def list_styles(self) -> list[dict[str, Any]]:
        return [self.get_style_info(sid) for sid in self._styles]

    def get_style(self, style_id: str) -> FormattingStyle:
        return self._styles.get(style_id)

    def get_style_info(self, style_id: str) -> dict[str, Any]:
        style = self._styles.get(style_id)
        if not style:
            return None
        info = asdict(style)
        info["is_builtin"] = True
        return info

    def register_style(self, style: FormattingStyle):
        self._styles[style.id] = style
