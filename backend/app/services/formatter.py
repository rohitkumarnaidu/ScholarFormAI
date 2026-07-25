import html
import logging
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

from app.api.models import FormattingOptions, Manuscript, Paragraph, Section
from app.services.style_registry import FormattingStyle

logger = logging.getLogger(__name__)


class ManuscriptFormatter:
    def format(
        self,
        manuscript: Manuscript,
        style: FormattingStyle,
        output_path: str,
        options: FormattingOptions | None = None,
    ) -> str:
        doc = Document()

        self._set_margins(doc, style)
        self._set_default_font(doc, style)
        self._apply_line_spacing(doc, style)

        if style.title_page:
            self._create_title_page(doc, manuscript, style)

        if style.running_header:
            self._add_running_header(doc, manuscript, style)

        self._add_abstract(doc, manuscript, style)
        self._add_keywords(doc, manuscript, style)
        self._create_body(doc, manuscript, style)
        self._add_references(doc, manuscript, style)

        if style.page_numbers:
            self._add_page_numbers(doc)

        doc.save(output_path)
        logger.info("Saved formatted document to %s", output_path)
        return output_path

    def _set_margins(self, doc: Document, style: FormattingStyle):
        for section in doc.sections:
            section.top_margin = Inches(style.margin_inches)
            section.bottom_margin = Inches(style.margin_inches)
            section.left_margin = Inches(style.margin_inches)
            section.right_margin = Inches(style.margin_inches)

    def _set_default_font(self, doc: Document, style: FormattingStyle):
        style_obj = doc.styles["Normal"]
        font = style_obj.font
        font.name = style.font_family
        font.size = Pt(style.font_size)
        pf = style_obj.paragraph_format
        pf.line_spacing = style.line_spacing
        pf.space_after = Pt(style.paragraph_spacing)

    def _apply_line_spacing(self, doc: Document, style: FormattingStyle):
        style_obj = doc.styles["Normal"]
        style_obj.paragraph_format.line_spacing = style.line_spacing

    def _create_title_page(self, doc: Document, manuscript: Manuscript, style: FormattingStyle):
        for _ in range(3):
            doc.add_paragraph()

        title_para = doc.add_paragraph()
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = title_para.add_run(manuscript.title)
        run.bold = True
        run.font.size = Pt(16)
        run.font.name = style.font_family

        authors_text = (
            ", ".join(f"{a.first_name} {a.last_name}" for a in manuscript.authors)
            if manuscript.authors
            else ""
        )
        if authors_text:
            auth_para = doc.add_paragraph()
            auth_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = auth_para.add_run(authors_text)
            run.font.size = Pt(style.font_size)
            run.font.name = style.font_family

        if manuscript.corresponding_author:
            corr = manuscript.corresponding_author
            corr_para = doc.add_paragraph()
            corr_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = corr_para.add_run(f"Corresponding Author: {corr.first_name} {corr.last_name}")
            run.font.size = Pt(10)
            run.font.name = style.font_family
            if corr.email:
                email_para = doc.add_paragraph()
                email_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = email_para.add_run(corr.email)
                run.font.size = Pt(10)

        doc.add_page_break()

    def _add_running_header(self, doc: Document, manuscript: Manuscript, style: FormattingStyle):
        for section in doc.sections:
            header = section.header
            header.is_linked_to_previous = False
            p = header.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            run = p.add_run(self._generate_running_head(manuscript.title))
            run.font.size = Pt(10)
            run.font.name = style.font_family

    def _generate_running_head(self, title: str) -> str:
        words = re.sub(r"[^a-zA-Z0-9\s]", "", title).split()
        short = " ".join(words[:5])
        return short.upper() if len(short) <= 50 else short[:50].upper()

    def _add_abstract(self, doc: Document, manuscript: Manuscript, style: FormattingStyle):
        if not manuscript.abstract:
            return

        heading = doc.add_paragraph()
        heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = heading.add_run("Abstract")
        run.bold = True
        run.font.size = Pt(style.font_size)
        run.font.name = style.font_family

        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = Inches(style.first_line_indent)
        run = p.add_run(manuscript.abstract)
        run.font.size = Pt(style.font_size)
        run.font.name = style.font_family

    def _add_keywords(self, doc: Document, manuscript: Manuscript, style: FormattingStyle):
        if not manuscript.keywords:
            return

        p = doc.add_paragraph()
        run = p.add_run("Keywords: ")
        run.bold = True
        run.font.size = Pt(style.font_size)
        run.font.name = style.font_family
        run = p.add_run(", ".join(manuscript.keywords))
        run.font.size = Pt(style.font_size)
        run.font.name = style.font_family

    def _create_body(self, doc: Document, manuscript: Manuscript, style: FormattingStyle):
        for section in manuscript.sections:
            self._render_section(doc, section, style, 1)

    def _render_section(self, doc: Document, section: Section, style: FormattingStyle, level: int):
        heading_style = style.heading_styles.get(level, {})
        hs = doc.add_paragraph()

        align_map = {
            "center": WD_ALIGN_PARAGRAPH.CENTER,
            "left": WD_ALIGN_PARAGRAPH.LEFT,
            "right": WD_ALIGN_PARAGRAPH.RIGHT,
            "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
        }
        hs.alignment = align_map.get(
            heading_style.get("alignment", "left"), WD_ALIGN_PARAGRAPH.LEFT
        )

        run = hs.add_run(section.heading)
        run.bold = heading_style.get("bold", level == 1)
        run.italic = heading_style.get("italic", False)
        run.font.size = Pt(heading_style.get("font_size", 14 - level))
        run.font.name = style.font_family

        for para in section.content:
            self._render_paragraph(doc, para, style)

        for subsection in section.subsections:
            self._render_section(doc, subsection, style, level + 1)

    def _render_paragraph(self, doc: Document, para: Paragraph, style: FormattingStyle):
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = Inches(style.first_line_indent)

        align_map = {
            "left": WD_ALIGN_PARAGRAPH.LEFT,
            "center": WD_ALIGN_PARAGRAPH.CENTER,
            "right": WD_ALIGN_PARAGRAPH.RIGHT,
            "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
        }
        if para.alignment:
            p.alignment = align_map.get(para.alignment, WD_ALIGN_PARAGRAPH.LEFT)

        if para.bullet:
            p.style = doc.styles["List Bullet"]

        run = p.add_run(para.text)
        run.font.name = style.font_family
        run.font.size = Pt(style.font_size)

        if para.style == "italic":
            run.italic = True
        elif para.style == "bold":
            run.bold = True

    def _add_references(self, doc: Document, manuscript: Manuscript, style: FormattingStyle):
        if not manuscript.references:
            return

        doc.add_page_break()

        heading = doc.add_paragraph()
        heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = heading.add_run("References")
        run.bold = True
        run.font.size = Pt(14)
        run.font.name = style.font_family

        numbered = "numbered" in style.reference_format

        for i, ref in enumerate(manuscript.references, 1):
            p = doc.add_paragraph()
            p.paragraph_format.first_line_indent = Inches(-0.5)
            p.paragraph_format.left_indent = Inches(0.5)

            if numbered:
                prefix = f"[{i}] "
            else:
                authors = (
                    ", ".join(f"{a.last_name}, {a.first_name[0]}." for a in ref.authors)
                    if ref.authors
                    else ""
                )
                prefix = f"{authors} ({ref.year}). " if authors and ref.year else ""

            run = p.add_run(prefix)
            run.font.size = Pt(style.font_size)
            run.font.name = style.font_family

            title_text = ref.title
            if ref.journal:
                title_text = f"{title_text}. {ref.journal}"
            if ref.volume:
                title_text = f"{title_text}, {ref.volume}"
                if ref.issue:
                    title_text = f"{title_text}({ref.issue})"
            if ref.pages:
                title_text = f"{title_text}, {ref.pages}"
            if ref.doi:
                title_text = f"{title_text}. https://doi.org/{ref.doi}"

            run = p.add_run(title_text)
            run.font.size = Pt(style.font_size)
            run.font.name = style.font_family

    def _add_page_numbers(self, doc: Document):
        for section in doc.sections:
            footer = section.footer
            footer.is_linked_to_previous = False
            p = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER

            run = p.add_run()
            fld_char1 = OxmlElement("w:fldChar")
            fld_char1.set(qn("w:fldCharType"), "begin")
            run._element.append(fld_char1)

            run2 = p.add_run()
            instr_text = OxmlElement("w:instrText")
            instr_text.set(qn("xml:space"), "preserve")
            instr_text.text = " PAGE "
            run2._element.append(instr_text)

            run3 = p.add_run()
            fld_char2 = OxmlElement("w:fldChar")
            fld_char2.set(qn("w:fldCharType"), "end")
            run3._element.append(fld_char2)

    def estimate_pages(self, docx_path: str) -> int:
        try:
            from docx import Document as DocxDoc

            doc = DocxDoc(docx_path)
            para_count = len(doc.paragraphs)
            return max(1, para_count // 25)
        except Exception:
            return 1

    def generate_html_preview(self, manuscript: Manuscript, style: FormattingStyle) -> str:
        escaped_title = html.escape(manuscript.title)
        parts = [
            f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>{escaped_title}</title>
<style>
  body {{ """
            f"""font-family: {style.font_family}, serif; font-size: {style.font_size}pt; """
            f"""line-height: {style.line_spacing}; margin: {style.margin_inches}in; }}
  h1 {{ font-size: 16pt; font-weight: bold; text-align: center; }}
  h2 {{ font-size: 14pt; font-weight: bold; }}
  h3 {{ font-size: 12pt; font-weight: bold; font-style: italic; }}
  .abstract {{ margin: 1em 0; }}
  .keywords {{ margin: 0.5em 0; }}
  .references {{ margin-top: 2em; }}
  .ref-entry {{ margin-left: 0.5in; text-indent: -0.5in; }}
  @media print {{ .page-break {{ page-break-after: always; }} }}
</style></head><body>"""
        ]

        parts.append(f"<h1>{escaped_title}</h1>")
        if manuscript.authors:
            parts.append(
                f"<p style='text-align:center;'>"
                f"{', '.join(html.escape(f'{a.first_name} {a.last_name}') for a in manuscript.authors)}</p>"
            )

        if manuscript.abstract:
            parts.append(
                f"<div class='abstract'><h2>Abstract</h2><p>{html.escape(manuscript.abstract)}</p></div>"
            )

        if manuscript.keywords:
            parts.append(
                f"<p class='keywords'><strong>Keywords:</strong> "
                f"{', '.join(html.escape(kw) for kw in manuscript.keywords)}</p>"
            )

        for section in manuscript.sections:
            parts.append(self._render_section_html(section, 2))

        if manuscript.references:
            parts.append("<div class='references'><h2>References</h2>")
            for ref in manuscript.references:
                authors = (
                    ", ".join(f"{html.escape(a.last_name)}, {html.escape(a.first_name[0])}." for a in ref.authors)
                    if ref.authors
                    else ""
                )
                parts.append(
                    f"<p class='ref-entry'>{authors} ({html.escape(ref.year or '')}). "
                    f"{html.escape(ref.title)}. <em>{html.escape(ref.journal or '')}</em>.</p>"
                )
            parts.append("</div>")

        parts.append("</body></html>")
        return "\n".join(parts)

    def _render_section_html(self, section: Section, level: int) -> str:
        tag = f"h{min(level, 6)}"
        parts = [f"<{tag}>{html.escape(section.heading)}</{tag}>"]
        for para in section.content:
            parts.append(f"<p>{html.escape(para.text)}</p>")
        for sub in section.subsections:
            parts.append(self._render_section_html(sub, level + 1))
        return "\n".join(parts)
