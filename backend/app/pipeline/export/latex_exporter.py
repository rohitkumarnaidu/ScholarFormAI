# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
from pathlib import Path

from app.models.pipeline_document import PipelineDocument

logger = logging.getLogger(__name__)

JOURNAL_TEMPLATES: dict[str, dict[str, str]] = {
    "ieee": {
        "documentclass": r"\documentclass[conference]{IEEEtran}",
        "packages": r"\usepackage{cite}\usepackage{amsmath,amssymb,amsfonts}\usepackage{algorithmic}\usepackage{graphicx}\usepackage{textcomp}\usepackage{xcolor}\usepackage{hyperref}",
        "bibliographystyle": r"\bibliographystyle{IEEEtran}",
    },
    "acm": {
        "documentclass": r"\documentclass[sigconf]{acmart}",
        "packages": r"\usepackage{amsmath,amssymb}\usepackage{graphicx}\usepackage{hyperref}",
        "bibliographystyle": r"\bibliographystyle{ACM-Reference-Format}",
    },
    "apa": {
        "documentclass": r"\documentclass[man]{apa7}",
        "packages": r"\usepackage{amsmath,amssymb}\usepackage{graphicx}\usepackage{hyperref}\usepackage{apacite}",
        "bibliographystyle": r"\bibliographystyle{apacite}",
    },
    "springer": {
        "documentclass": r"\documentclass[sn-basic]{sn-jnl}",
        "packages": r"\usepackage{amsmath,amssymb}\usepackage{graphicx}\usepackage{hyperref}\usepackage{natbib}",
        "bibliographystyle": r"\bibliographystyle{sn-chicago}",
    },
    "nature": {
        "documentclass": r"\documentclass[review]{article}",
        "packages": r"\usepackage{amsmath,amssymb}\usepackage{graphicx}\usepackage{hyperref}\usepackage{natbib}",
        "bibliographystyle": r"\bibliographystyle{naturemag}",
    },
    "elsevier": {
        "documentclass": r"\documentclass[review]{elsarticle}",
        "packages": r"\usepackage{amsmath,amssymb}\usepackage{graphicx}\usepackage{hyperref}\usepackage{natbib}",
        "bibliographystyle": r"\bibliographystyle{elsarticle-num}",
    },
    "mla": {
        "documentclass": r"\documentclass[12pt]{article}",
        "packages": r"\usepackage{amsmath,amssymb}\usepackage{graphicx}\usepackage{hyperref}\usepackage[style=mla]{biblatex}",
        "bibliographystyle": "",
    },
    "chicago": {
        "documentclass": r"\documentclass[12pt]{article}",
        "packages": r"\usepackage{amsmath,amssymb}\usepackage{graphicx}\usepackage{hyperref}\usepackage[style=chicago-authordate]{biblatex}",
        "bibliographystyle": "",
    },
    "vancouver": {
        "documentclass": r"\documentclass[12pt]{article}",
        "packages": r"\usepackage{amsmath,amssymb}\usepackage{graphicx}\usepackage{hyperref}\usepackage{natbib}",
        "bibliographystyle": r"\bibliographystyle{vancouver}",
    },
    "harvard": {
        "documentclass": r"\documentclass[12pt]{article}",
        "packages": r"\usepackage{amsmath,amssymb}\usepackage{graphicx}\usepackage{hyperref}\usepackage[style=apa]{biblatex}",
        "bibliographystyle": "",
    },
    "default": {
        "documentclass": r"\documentclass[11pt,a4paper]{article}",
        "packages": r"\usepackage[utf8]{inputenc}\usepackage[T1]{fontenc}\usepackage{amsmath,amssymb}\usepackage{graphicx}\usepackage{hyperref}\usepackage{geometry}\geometry{margin=1in}",
        "bibliographystyle": r"\bibliographystyle{plain}",
    },
}


def escape_latex(text: str) -> str:
    chars = {
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
        "\\": r"\textbackslash{}",
    }
    pattern = re.compile("|".join(re.escape(c) for c in chars))
    return pattern.sub(lambda m: chars[m.group(0)], text)


def _resolve_pandoc_binary() -> str | None:
    configured = (os.getenv("PANDOC_PATH") or "").strip()
    if configured:
        return configured
    return shutil.which("pandoc")


def _convert_via_pandoc(docx_path: str, output_path: str, timeout: int) -> bool:
    pandoc = _resolve_pandoc_binary()
    if not pandoc:
        return False
    cmd = [pandoc, docx_path, "--from=docx", "--to=latex", "--standalone", "--output", output_path]
    try:
        result = subprocess.run(cmd, check=False, timeout=timeout, capture_output=True, text=True)
        if result.returncode == 0 and os.path.exists(output_path):
            logger.info("Pandoc conversion succeeded: %s", output_path)
            return True
        logger.warning(
            "Pandoc failed (exit %d): %s", result.returncode, (result.stderr or result.stdout or "").strip()[:500]
        )
    except subprocess.TimeoutExpired:
        logger.warning("Pandoc timed out after %ds", timeout)
    except OSError as exc:
        logger.warning("Pandoc execution error: %s", exc)
    return False


class LaTeXExporter:
    def __init__(self, timeout_seconds: int = 120):
        self.timeout = int(timeout_seconds)

    def convert_to_latex(self, docx_path: str, output_dir: str, template_name: str = "default") -> str:
        source = Path(docx_path)
        if not source.exists():
            raise RuntimeError(f"DOCX not found: {docx_path}")

        if not _resolve_pandoc_binary():
            raise RuntimeError("Pandoc is not installed. Install Pandoc or set PANDOC_PATH to the binary location.")

        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        tex_path = out_dir / f"{source.stem}.tex"

        if _convert_via_pandoc(docx_path, str(tex_path), self.timeout):
            return str(tex_path)

        raise RuntimeError("Pandoc conversion failed and no document structure fallback available")

    def export_from_document(self, doc: PipelineDocument, output_dir: str) -> str:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        template_key = "default"
        if doc.template and doc.template.template_name:
            t = doc.template.template_name.lower().replace(" ", "_").replace("-", "_")
            if t in JOURNAL_TEMPLATES:
                template_key = t

        tpl = JOURNAL_TEMPLATES.get(template_key, JOURNAL_TEMPLATES["default"])
        stem = "manuscript"
        tex_path = out_dir / f"{stem}.tex"
        bib_path = out_dir / f"{stem}.bib"

        lines: list[str] = []
        lines.append(tpl["documentclass"])
        lines.append(tpl["packages"])
        lines.append(r"\usepackage[style=ieee]{biblatex}" if template_key in ("ieee",) else "")
        lines.append(
            r"\addbibresource{" + stem + ".bib}"
            if tpl["bibliographystyle"] and not tpl["bibliographystyle"].startswith(r"\bibliographystyle")
            else ""
        )
        lines.append(r"\begin{document}")
        lines.append("")

        self._write_title_authors(lines, doc)
        self._write_abstract(lines, doc)
        self._write_sections(lines, doc)
        self._write_figures(lines, doc, out_dir)
        self._write_tables(lines, doc)
        self._write_equations(lines, doc)

        if doc.references:
            lines.append(
                r"\printbibliography"
                if not tpl["bibliographystyle"] or "biblatex" in tpl["packages"]
                else r"\bibliography{" + stem + "}"
            )
            lines.append("")

        lines.append(r"\end{document}")
        lines.append("")

        content = "\n".join(lines)
        tex_path.write_text(content, encoding="utf-8")

        self._write_bibtex(doc, bib_path)

        logger.info("LaTeX document written: %s (template=%s, %d chars)", tex_path, template_key, len(content))
        return str(tex_path)

    def _write_title_authors(self, lines: list[str], doc: PipelineDocument) -> None:
        meta = doc.metadata
        title = escape_latex(meta.title or "Untitled")
        lines.append(r"\title{" + title + "}")
        if meta.authors:
            authors = r"\and ".join(escape_latex(a) for a in meta.authors)
            lines.append(r"\author{" + authors + "}")
        if meta.publication_date:
            lines.append(r"\date{" + escape_latex(str(meta.publication_date)) + "}")
        else:
            lines.append(r"\date{\today}")
        lines.append(r"\maketitle")
        lines.append("")

    def _write_abstract(self, lines: list[str], doc: PipelineDocument) -> None:
        if doc.metadata.abstract:
            lines.append(r"\begin{abstract}")
            lines.append(escape_latex(doc.metadata.abstract))
            lines.append(r"\end{abstract}")
            lines.append("")
        if doc.metadata.keywords:
            kw = ", ".join(escape_latex(k) for k in doc.metadata.keywords)
            lines.append(r"\textbf{Keywords:} " + kw)
            lines.append("")

    def _write_sections(self, lines: list[str], doc: PipelineDocument) -> None:
        for block in sorted(doc.blocks, key=lambda b: b.index):
            text = (block.text or "").strip()
            if not text:
                continue
            btype = (block.block_type or "").lower()
            escaped = escape_latex(text)
            if btype.startswith("heading_1"):
                lines.append(r"\section{" + escaped + "}")
            elif btype.startswith("heading_2"):
                lines.append(r"\subsection{" + escaped + "}")
            elif btype.startswith("heading_3"):
                lines.append(r"\subsubsection{" + escaped + "}")
            elif btype in ("reference_entry", "references_heading") or btype in ("figure", "table", "equation"):
                continue
            else:
                lines.append(escaped)
            lines.append("")

    def _write_figures(self, lines: list[str], doc: PipelineDocument, out_dir: Path | None = None) -> None:
        for fig in sorted(doc.figures, key=lambda f: f.index):
            caption = escape_latex(fig.caption_text or "") if fig.caption_text else "Figure"
            lines.append(r"\begin{figure}[htbp]")
            if fig.image_data and out_dir:
                ext = str(fig.image_format or "png")
                img_name = f"fig_{fig.index}.{ext}"
                img_path = out_dir / img_name
                if not img_path.exists():
                    img_path.write_bytes(fig.image_data)
                lines.append(r"\includegraphics[width=\textwidth]{" + img_name + "}")
            lines.append(r"\caption{" + caption + "}")
            if fig.label:
                lines.append(r"\label{" + escape_latex(str(fig.label)) + "}")
            lines.append(r"\end{figure}")
            lines.append("")

    def _write_tables(self, lines: list[str], doc: PipelineDocument) -> None:
        for tbl in sorted(doc.tables, key=lambda t: t.index):
            caption = escape_latex(tbl.caption_text or "Table") if tbl.caption_text else "Table"
            lines.append(r"\begin{table}[htbp]")
            lines.append(r"\centering")
            if tbl.rows:
                ncols = max(len(r) for r in tbl.rows) if tbl.rows else 1
                col_spec = "|" + "c|" * ncols
                lines.append(r"\begin{tabular}{" + col_spec + "}")
                lines.append(r"\hline")
                for row_idx, row in enumerate(tbl.rows):
                    cell_text = " & ".join(escape_latex(str(c)) for c in row)
                    lines.append(cell_text + r" \\")
                    if row_idx == 0:
                        lines.append(r"\hline")
                lines.append(r"\hline")
                lines.append(r"\end{tabular}")
            lines.append(r"\caption{" + caption + "}")
            lines.append(r"\end{table}")
            lines.append("")

    def _write_equations(self, lines: list[str], doc: PipelineDocument) -> None:
        for eq in sorted(doc.equations, key=lambda e: e.index):
            tex = (eq.text or eq.mathml or eq.omml or "").strip()
            if not tex:
                continue
            if tex.startswith(r"\begin{equation}") or tex.startswith(r"\begin{align}"):
                lines.append(tex)
            else:
                lines.append(r"\begin{equation}")
                lines.append(tex)
                lines.append(r"\end{equation}")
            lines.append("")

    def _write_bibtex(self, doc: PipelineDocument, bib_path: Path) -> None:
        if not doc.references:
            return
        entries: list[str] = []
        for i, ref in enumerate(doc.references):
            ref_id = f"ref_{i + 1}"
            raw = (ref.formatted_text or ref.raw_text or "").strip()
            if not raw:
                continue
            authors = ""
            title = ""
            year = ""
            journal = ""
            doi = ""
            if ref.metadata:
                authors = ref.metadata.get("authors", "")
                title = ref.metadata.get("title", "")
                year = str(ref.metadata.get("year", ""))
                journal = ref.metadata.get("journal", "")
                doi = ref.metadata.get("doi", "")
            if title:
                entry_lines = [f"@article{{{ref_id},"]
                if authors:
                    entry_lines.append(f"  author = {{{escape_latex(str(authors))}}},")
                entry_lines.append(f"  title = {{{escape_latex(title)}}},")
                if journal:
                    entry_lines.append(f"  journal = {{{escape_latex(journal)}}},")
                if year:
                    entry_lines.append(f"  year = {{{escape_latex(year)}}},")
                if doi:
                    entry_lines.append(f"  doi = {{{escape_latex(doi)}}},")
                entry_lines.append("}")
                entries.append("\n".join(entry_lines))
            else:
                entries.append(f"@misc{{{ref_id},\n  note = {{{escape_latex(raw)}}}\n}}")
        if entries:
            bib_path.write_text("\n\n".join(entries) + "\n", encoding="utf-8")
            logger.info("BibTeX file written: %s (%d entries)", bib_path, len(entries))
