# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import logging
from datetime import datetime

from lxml import etree

from app.models.pipeline_document import PipelineDocument

logger = logging.getLogger(__name__)


class JATSGenerator:
    """
    Generates JATS XML (Journal Article Tag Suite) from a PipelineDocument.
    Focuses on metadata, structural sections, and MathML equations.
    """

    def __init__(self):
        self.nsmap = {"mml": "http://www.w3.org/1998/Math/MathML", "xlink": "http://www.w3.org/1999/xlink"}

    def to_xml(self, doc_obj: PipelineDocument) -> str:
        """Create a JATS XML string."""
        root = etree.Element("article", nsmap=self.nsmap)
        root.set("article-type", "research-article")
        root.set("dtd-version", "1.2")

        # 1. Front Matter (Metadata)
        front = etree.SubElement(root, "front")
        self._add_metadata(front, doc_obj)

        # 2. Body (Sections & Equations)
        body = etree.SubElement(root, "body")
        self._add_body(body, doc_obj)

        # 3. Back Matter (References)
        back = etree.SubElement(root, "back")
        self._add_references(back, doc_obj)

        return etree.tostring(
            root,
            encoding="unicode",
            pretty_print=True,
            doctype='<!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Archiving and Interchange DTD v1.2 20190208//EN" "JATS-archivearticle1.dtd">',
        )

    def _add_references(self, parent, doc_obj):
        """Add reference list to back matter."""
        if not doc_obj.references:
            logger.debug("JATS export: No references found, skipping ref-list")
            return

        ref_list = etree.SubElement(parent, "ref-list")
        title = etree.SubElement(ref_list, "title")
        title.text = "References"

        for idx, ref in enumerate(doc_obj.references, start=1):
            ref_elem = etree.SubElement(ref_list, "ref")
            ref_elem.set("id", ref.reference_id or f"ref_{idx}")

            # Mixed citation (simple text representation)
            mixed_citation = etree.SubElement(ref_elem, "mixed-citation")
            mixed_citation.text = ref.raw_text or "Reference text unavailable"

            # Add structured metadata if available
            if ref.metadata and "doi" in ref.metadata:
                pub_id = etree.SubElement(mixed_citation, "pub-id")
                pub_id.set("pub-id-type", "doi")
                pub_id.text = ref.metadata["doi"]

    def _add_metadata(self, parent, doc_obj):
        article_meta = etree.SubElement(parent, "article-meta")

        # Title
        title_group = etree.SubElement(article_meta, "title-group")
        article_title = etree.SubElement(title_group, "article-title")
        article_title.text = doc_obj.metadata.title or "Untitled Manuscript"

        # Authors - Validate at least one exists
        if not doc_obj.metadata.authors:
            logger.warning("JATS export: No authors found, adding placeholder")
            doc_obj.metadata.authors = ["Unknown Author"]

        contrib_group = etree.SubElement(article_meta, "contrib-group")
        for author in doc_obj.metadata.authors:
            contrib = etree.SubElement(contrib_group, "contrib", contrib_type="author")
            name = etree.SubElement(contrib, "name")
            surname = etree.SubElement(name, "surname")
            surname.text = author.split()[-1] if author.split() else author
            given_names = etree.SubElement(name, "given-names")
            given_names.text = " ".join(author.split()[:-1]) if len(author.split()) > 1 else author

        # Publication Date
        if doc_obj.metadata.publication_date:
            pub_date = etree.SubElement(article_meta, "pub-date")
            dt = doc_obj.metadata.publication_date
            if isinstance(dt, datetime):
                etree.SubElement(pub_date, "year").text = str(dt.year)
                etree.SubElement(pub_date, "month").text = str(dt.month).zfill(2)
                etree.SubElement(pub_date, "day").text = str(dt.day).zfill(2)
            else:
                try:
                    date_parts = str(dt).split("-")
                    if len(date_parts) >= 1:
                        etree.SubElement(pub_date, "year").text = date_parts[0]
                    if len(date_parts) >= 2:
                        etree.SubElement(pub_date, "month").text = date_parts[1]
                    if len(date_parts) >= 3:
                        etree.SubElement(pub_date, "day").text = date_parts[2][:2]
                except:
                    pass  # intentionally ignored

        # Volume / Issue
        if doc_obj.metadata.volume:
            vol = etree.SubElement(article_meta, "volume")
            vol.text = str(doc_obj.metadata.volume)

        if doc_obj.metadata.issue:
            iss = etree.SubElement(article_meta, "issue")
            iss.text = str(doc_obj.metadata.issue)

        # Abstract
        if doc_obj.metadata.abstract:
            abstract = etree.SubElement(article_meta, "abstract")
            abstract_p = etree.SubElement(abstract, "p")
            abstract_p.text = doc_obj.metadata.abstract
        else:
            logger.info("JATS export: No abstract found, skipping abstract element")

    def _add_body(self, parent, doc_obj):
        # Map sections
        current_sec = None
        for block in doc_obj.blocks:
            intent = block.metadata.get("semantic_intent", "body")

            if intent == "heading":
                current_sec = etree.SubElement(parent, "sec")
                title = etree.SubElement(current_sec, "title")
                title.text = block.text
            else:
                target = current_sec if current_sec is not None else parent
                p = etree.SubElement(target, "p")
                p.text = block.text

        # Map Equations
        for eqn in doc_obj.equations:
            if eqn.mathml:
                formula_tag = "disp-formula" if eqn.is_block else "inline-formula"
                formula = etree.SubElement(parent, formula_tag)
                formula.set("id", eqn.equation_id)

                # Import MathML fragment
                try:
                    mathml_tree = etree.fromstring(eqn.mathml)
                    formula.append(mathml_tree)
                except:
                    pass  # intentionally ignored
