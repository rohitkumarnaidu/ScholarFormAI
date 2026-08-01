# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Exporter Module - Handles saving of formatted documents.
"""

import html as html_mod
import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

from app.models import PipelineDocument as Document
from app.pipeline.export.jats_generator import JATSGenerator
from app.pipeline.export.latex_exporter import LaTeXExporter
from app.pipeline.export.pdf_exporter import PDFExporter
from app.utils.serialization import safe_model_dump

logger = logging.getLogger(__name__)


class Exporter:
    """
    Handles file output operations.

    Supports DOCX, PDF, JATS XML, JSON, Markdown, HTML, and LaTeX exports.
    """

    def __init__(self):
        self.pdf_exporter = PDFExporter()
        self.latex_exporter = LaTeXExporter()

    def process(self, document: Document) -> Document:
        """Standard pipeline stage entry point."""
        export_formats = self._get_export_formats(document)

        if (
            "docx" in export_formats
            and hasattr(document, "generated_doc")
            and document.generated_doc
            and document.output_path
        ):
            self.export(document.generated_doc, document.output_path)

        if document.output_path and document.output_path.endswith(".docx"):
            if "json" in export_formats:
                json_path = document.output_path.replace(".docx", ".json")
                self.export_json(document, json_path)

            if "markdown" in export_formats:
                md_path = document.output_path.replace(".docx", ".md")
                self.export_markdown(document, md_path)

            if "pdf" in export_formats:
                try:
                    # PDF export requires the DOCX to be saved first
                    output_dir = os.path.dirname(document.output_path)
                    self.pdf_exporter.convert_to_pdf(document.output_path, output_dir)
                except Exception as e:
                    logger.warning("Exporter: PDF export failed: %s", e)

            if "html" in export_formats:
                html_path = document.output_path.replace(".docx", ".html")
                self.export_html(document, html_path)

            if "latex" in export_formats:
                tex_path = document.output_path.replace(".docx", ".tex")
                self.export_latex(document, tex_path)

            # Keep JATS side-by-side for compatibility with existing pipeline behavior.
            xml_path = document.output_path.replace(".docx", ".xml")
            self.export_jats(document, xml_path)

        return document

    def export(self, word_doc: Any, output_path: str) -> str:
        """Save the Word document to disk."""
        if not word_doc:
            return None
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        word_doc.save(output_path)
        return output_path

    def export_json(self, doc_obj: Document, output_path: str) -> str | None:
        """Export document with metadata to JSON."""
        try:
            payload = self._build_export_payload(doc_obj)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            return output_path
        except Exception as e:
            logger.warning("Exporter: JSON export failed: %s", e)
            return None

    def export_markdown(self, doc_obj: Document, output_path: str) -> str | None:
        """Export document with metadata and content to Markdown."""
        try:
            markdown = self._build_markdown(doc_obj)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(markdown)
            return output_path
        except Exception as e:
            logger.warning("Exporter: Markdown export failed: %s", e)
            return None

    def export_jats(self, doc_obj: Document, output_path: str) -> str | None:
        """Generate and save JATS XML."""
        try:
            generator = JATSGenerator()
            xml_content = generator.to_xml(doc_obj)

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(xml_content)
            return output_path
        except Exception as e:
            logger.warning("Exporter: JATS export failed: %s", e)
            return None

    def export_html(self, doc_obj: Document, output_path: str) -> str | None:
        """Export document to HTML format."""
        try:
            markdown = self._build_markdown(doc_obj)
            lines = markdown.split("\n")
            html_lines = [
                "<!DOCTYPE html>",
                "<html>",
                "<head>",
                f"<title>{html_mod.escape(doc_obj.metadata.title or 'Document')}</title>",
                "</head>",
                "<body>",
            ]

            in_list = False
            for line in lines:
                if not line.strip():
                    continue
                if line.startswith("# "):
                    html_lines.append(f"<h1>{html_mod.escape(line[2:])}</h1>")
                elif line.startswith("## "):
                    html_lines.append(f"<h2>{html_mod.escape(line[3:])}</h2>")
                elif line.startswith("**") and ":" in line:
                    parts = line[2:].split("**")
                    if len(parts) >= 2:
                        html_lines.append(
                            f"<p><strong>{html_mod.escape(parts[0])}</strong>{html_mod.escape(parts[1])}</p>"
                        )
                elif line[0].isdigit() and len(line) > 1 and line[1] == ".":
                    if not in_list:
                        html_lines.append("<ol>")
                        in_list = True
                    html_lines.append(f"<li>{html_mod.escape(line[line.find('.') + 1 :].strip())}</li>")
                else:
                    if in_list:
                        html_lines.append("</ol>")
                        in_list = False
                    html_lines.append(f"<p>{html_mod.escape(line)}</p>")

            if in_list:
                html_lines.append("</ol>")

            html_lines.extend(["</body>", "</html>"])

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(html_lines))
            return output_path
        except Exception as e:
            logger.warning("Exporter: HTML export failed: %s", e)
            return None

    def export_latex(self, doc_obj: Document, output_path: str) -> str | None:
        try:
            if not doc_obj.output_path:
                return None
            template_name = doc_obj.template.template_name if doc_obj.template else "default"
            try:
                converted_path = self.latex_exporter.convert_to_latex(
                    doc_obj.output_path,
                    os.path.dirname(output_path),
                    template_name=template_name,
                )
                if converted_path != output_path and os.path.exists(converted_path):
                    os.replace(converted_path, output_path)
                return output_path
            except RuntimeError:
                converted_path = self.latex_exporter.export_from_document(
                    doc_obj,
                    os.path.dirname(output_path),
                )
                if converted_path != output_path and os.path.exists(converted_path):
                    os.replace(converted_path, output_path)
                return output_path
        except Exception as e:
            logger.warning("Exporter: LaTeX export failed: %s", e)
            return None

    def _get_export_formats(self, document: Document) -> list[str]:
        """
        Resolve export formats from formatting options.
        Defaults to DOCX + JSON + Markdown.
        """
        options = document.formatting_options or {}
        raw_formats = options.get("export_formats", ["docx", "json", "markdown"])

        if not isinstance(raw_formats, list):
            raw_formats = [str(raw_formats)]

        normalized: list[str] = []
        for fmt in raw_formats:
            name = str(fmt).strip().lower()
            if name and name not in normalized:
                normalized.append(name)

        # DOCX remains primary output artifact.
        if "docx" not in normalized:
            normalized.insert(0, "docx")

        return normalized

    def _build_export_payload(self, doc_obj: Document) -> dict[str, Any]:
        """Create a serializable export payload preserving metadata."""
        template_name = doc_obj.template.template_name if doc_obj.template else None

        return {
            "document_id": doc_obj.document_id,
            "original_filename": doc_obj.original_filename,
            "source_path": doc_obj.source_path,
            "output_path": doc_obj.output_path,
            "template": template_name,
            "metadata": safe_model_dump(doc_obj.metadata),
            "stats": doc_obj.get_stats(),
            "validation": {
                "is_valid": doc_obj.is_valid,
                "errors": doc_obj.validation_errors,
                "warnings": doc_obj.validation_warnings,
            },
            "blocks": [safe_model_dump(block) for block in doc_obj.blocks],
            "references": [safe_model_dump(ref) for ref in doc_obj.references],
            "figures": [safe_model_dump(figure) for figure in doc_obj.figures],
            "tables": [safe_model_dump(table) for table in doc_obj.tables],
            "equations": [safe_model_dump(equation) for equation in doc_obj.equations],
            "processing_history": [safe_model_dump(stage) for stage in doc_obj.processing_history],
            "exported_at": datetime.now(UTC).isoformat(),
        }

    def _build_markdown(self, doc_obj: Document) -> str:
        """Build markdown export preserving metadata and content."""
        metadata = doc_obj.metadata
        lines: list[str] = []

        title = metadata.title or doc_obj.original_filename or "Untitled Manuscript"
        lines.append(f"# {title}")
        lines.append("")

        if metadata.authors:
            lines.append(f"**Authors:** {', '.join(metadata.authors)}")
        if metadata.affiliations:
            lines.append(f"**Affiliations:** {'; '.join(metadata.affiliations)}")
        if metadata.doi:
            lines.append(f"**DOI:** {metadata.doi}")
        if doc_obj.template and doc_obj.template.template_name:
            lines.append(f"**Template:** {doc_obj.template.template_name}")
        lines.append("")

        if metadata.abstract:
            lines.append("## Abstract")
            lines.append(metadata.abstract)
            lines.append("")

        if metadata.keywords:
            lines.append(f"**Keywords:** {', '.join(metadata.keywords)}")
            lines.append("")

        current_heading: str | None = None
        for block in sorted(doc_obj.blocks, key=lambda b: b.index):
            block_type = str(block.block_type).lower()
            text = (block.text or "").strip()
            if not text:
                continue

            if block_type.startswith("heading_"):
                current_heading = text
                lines.append(f"## {current_heading}")
                lines.append("")
                continue

            if block_type in {"reference_entry", "references_heading"}:
                continue

            lines.append(text)
            lines.append("")

        references = [
            (ref.formatted_text or ref.raw_text or "").strip()
            for ref in sorted(doc_obj.references, key=lambda r: r.index)
            if (ref.formatted_text or ref.raw_text or "").strip()
        ]
        if references:
            lines.append("## References")
            lines.append("")
            for idx, ref_text in enumerate(references, start=1):
                lines.append(f"{idx}. {ref_text}")
            lines.append("")

        return "\n".join(lines).strip() + "\n"
