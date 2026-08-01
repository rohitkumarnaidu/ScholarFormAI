# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import logging
import os

from lxml import etree

from app.models import PipelineDocument
from app.utils.singleton import get_or_create

logger = logging.getLogger(__name__)


class EquationStandardizer:
    """
    Pipeline stage to standardize mathematical equations.
    Converts OMML (Word) to MathML and LaTeX.
    """

    def __init__(self, xsl_path: str = None):
        if xsl_path is None:
            # Default to bundled XSL in the same directory
            base_dir = os.path.dirname(os.path.abspath(__file__))
            xsl_path = os.path.join(base_dir, "omml2mml.xsl")

        self.xsl_path = xsl_path
        self._xslt = None

        if os.path.exists(self.xsl_path):
            try:
                xslt_doc = etree.parse(self.xsl_path)
                self._xslt = etree.XSLT(xslt_doc)
            except Exception as exc:
                logger.warning("EquationStandardizer: Failed to load XSLT: %s", exc)
        else:
            logger.warning("EquationStandardizer: XSLT not found at %s", self.xsl_path)

    def process(self, doc_obj: PipelineDocument) -> PipelineDocument:
        """Standardize all equations in the document."""
        try:
            if not doc_obj.equations:
                return doc_obj

            success_count = 0
            failure_count = 0

            for eqn in doc_obj.equations:
                try:
                    if eqn.omml:
                        # 1. Convert to MathML
                        mathml = self._convert_omml_to_mathml(eqn.omml)
                        if mathml:
                            eqn.mathml = mathml
                            success_count += 1
                        else:
                            failure_count += 1

                        # 2. Heuristic LaTeX extraction (Placeholder)
                        if not eqn.metadata:
                            eqn.metadata = {}
                        eqn.metadata["conversion_engine"] = "xslt-1.0"
                except Exception as exc:
                    logger.warning("EquationStandardizer: Failed to process equation: %s", exc)
                    failure_count += 1

            # Log detailed conversion statistics
            total = success_count + failure_count
            message = f"Converted {success_count}/{total} equations to MathML"
            if failure_count > 0:
                message += f" ({failure_count} failed)"

            doc_obj.add_processing_stage(
                stage_name="equation_standardization",
                status="success" if failure_count == 0 else "partial",
                message=message,
            )
        except Exception as exc:
            logger.error("EquationStandardizer.process failed: %s", exc, exc_info=True)
            doc_obj.add_processing_stage(
                stage_name="equation_standardization", status="error", message=f"Equation standardization failed: {exc}"
            )
        return doc_obj

    def _convert_omml_to_mathml(self, omml_xml: str) -> str:
        """Apply XSLT transformation to OMML string."""
        if not self._xslt:
            return ""

        try:
            # Parse OMML string
            dom = etree.fromstring(omml_xml)

            # Validate and normalize namespaces
            # Ensure OMML namespace is present
            omml_ns = "http://schemas.openxmlformats.org/officeDocument/2006/math"
            if dom.nsmap and None not in dom.nsmap:
                # If no default namespace, check if OMML namespace exists
                has_omml_ns = any(ns == omml_ns for ns in dom.nsmap.values())
                if not has_omml_ns:
                    logger.debug("EquationStandardizer: OMML namespace not found, attempting conversion anyway")

            # Apply XSLT transformation
            new_dom = self._xslt(dom)
            return etree.tostring(new_dom, encoding="unicode", pretty_print=True)
        except etree.XMLSyntaxError as exc:
            logger.warning("EquationStandardizer: XML syntax error: %s", exc)
            return ""
        except Exception as exc:
            logger.warning("EquationStandardizer: Conversion error: %s", exc)
            return ""


# Singleton Instance
_standardizer = None


def get_equation_standardizer() -> EquationStandardizer:
    global _standardizer
    _standardizer = get_or_create(_standardizer, EquationStandardizer)
    return _standardizer
