# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
GROBID REST API Client for metadata extraction.

GROBID (GeneRation Of BIbliographic Data) is a machine learning library for
extracting, parsing, and restructuring raw documents into structured XML/TEI.

This client replaces brittle regex-based metadata extraction with trained models
that can extract 68+ metadata labels including:
- Title, authors, affiliations
- Abstract, keywords
- References, citations
- Document structure
"""

import logging
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from requests import RequestException

try:
    from defusedxml import ElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element

from app.config.settings import settings
from app.exceptions import ExternalServiceError
from app.pipeline.safety.safe_execution import safe_function

logger = logging.getLogger(__name__)

try:
    import pybreaker
except Exception:
    pybreaker = None


class GROBIDClient:
    """REST API client for GROBID service."""

    # TEI namespace for XML parsing
    TEI_NS = {"tei": "http://www.tei-c.org/ns/1.0"}
    TRANSIENT_HTTP_STATUSES = {408, 425, 429, 500, 502, 503, 504, 520, 522, 524}
    LAST_GOOD_ENDPOINT_TTL_SECONDS = 300.0

    def __init__(self, base_url: str | None = None):
        """
        Initialize GROBID client.

        Args:
            base_url: Optional primary GROBID URL override.
        """
        configured_urls = list(getattr(settings, "get_grobid_urls", lambda: [])())
        if not configured_urls:
            fallback_url = getattr(settings, "GROBID_URL", "http://localhost:8070")
            configured_urls = [str(fallback_url).rstrip("/")]

        if base_url:
            normalized_base_url = str(base_url).strip().rstrip("/")
            configured_urls = [normalized_base_url] + [url for url in configured_urls if url != normalized_base_url]

        self.base_urls = [url for url in configured_urls if url]
        if not self.base_urls:
            self.base_urls = ["http://localhost:8070"]

        self.base_url = self.base_urls[0]
        health_path = getattr(settings, "get_service_health_path", lambda _name: "/api/isalive")("grobid")
        health_path = str(health_path or "/api/isalive").strip()
        if not health_path.startswith("/"):
            health_path = f"/{health_path}"
        if len(health_path) > 1:
            health_path = health_path.rstrip("/")
        self.health_path = health_path
        parsed_base = urlparse(self.base_url if "://" in self.base_url else f"http://{self.base_url}")
        hostname = (parsed_base.hostname or "").lower()
        self._remote_hosted = hostname not in {"localhost", "127.0.0.1", "0.0.0.0"}  # nosec
        configured_timeout = int(getattr(settings, "GROBID_TIMEOUT", 15))
        # Hosted endpoints (for example HF Spaces) can have cold starts and slower responses.
        timeout_ceiling = 90 if self._remote_hosted else 30
        self.timeout = max(3, min(configured_timeout, timeout_ceiling))
        self.max_retries = max(1, int(getattr(settings, "GROBID_MAX_RETRIES", 3)))
        self.breaker = None
        if bool(getattr(settings, "EXTERNAL_CIRCUIT_BREAKER_ENABLED", True)) and pybreaker is not None:
            fail_max = max(1, int(getattr(settings, "EXTERNAL_CIRCUIT_BREAKER_FAILURE_THRESHOLD", 3)))
            reset_timeout = max(5, int(getattr(settings, "EXTERNAL_CIRCUIT_BREAKER_RESET_SECONDS", 60)))
            if self._remote_hosted:
                # Remote managed services are bursty; avoid tripping too aggressively.
                fail_max = max(fail_max, 6)
                reset_timeout = min(reset_timeout, 30)
            self.breaker = pybreaker.CircuitBreaker(
                fail_max=fail_max,
                reset_timeout=reset_timeout,
                name="grobid",
            )
        self._last_good_base_url = self.base_url
        self._last_good_at = time.monotonic()

    def _endpoint_url(self, base_url: str, path: str) -> str:
        normalized_path = path if path.startswith("/") else f"/{path}"
        return f"{base_url.rstrip('/')}{normalized_path}"

    def _mark_last_good_base_url(self, base_url: str, *, reason: str) -> None:
        previous = self._last_good_base_url
        self._last_good_base_url = base_url
        self._last_good_at = time.monotonic()
        self.base_url = base_url
        if previous and previous != base_url:
            logger.warning(
                "GROBID failover switch: %s -> %s (reason=%s)",
                previous,
                base_url,
                reason,
            )

    def _ordered_base_urls(self) -> list[str]:
        ordered = list(self.base_urls)
        if (
            self._last_good_base_url
            and self._last_good_base_url in ordered
            and (time.monotonic() - self._last_good_at) <= self.LAST_GOOD_ENDPOINT_TTL_SECONDS
        ):
            ordered.remove(self._last_good_base_url)
            ordered.insert(0, self._last_good_base_url)
        return ordered

    def _retry_backoff_seconds(self, attempt: int) -> float:
        return min(float(2 ** max(0, attempt - 1)), 8.0)

    def _request(self, method: str, url: str, **kwargs):
        if "timeout" not in kwargs:
            # Split connect/read to fail fast on bad network while allowing short response processing.
            connect_timeout = 5.0 if self._remote_hosted else 3.0
            kwargs["timeout"] = (connect_timeout, float(self.timeout))

        if self.breaker is None:
            return requests.request(method, url, **kwargs)
        return self.breaker.call(lambda: requests.request(method, url, **kwargs))

    def is_available(self) -> bool:
        """Check if GROBID service is running."""
        for base_url in self._ordered_base_urls():
            endpoint = self._endpoint_url(base_url, self.health_path)
            try:
                # Avoid counting health probes toward circuit-breaker failures.
                response = requests.request("GET", endpoint, timeout=(2.0, 3.0))
                if response.status_code == 200:
                    self._mark_last_good_base_url(base_url, reason="health_probe")
                    return True
                logger.warning(
                    "GROBID health probe unhealthy: url=%s status=%s",
                    endpoint,
                    response.status_code,
                )
            except Exception as exc:
                logger.warning("GROBID health probe failed: url=%s error=%s", endpoint, exc)
        return False

    @safe_function(fallback_value={}, error_message="GROBIDClient.process_header_document")
    def process_header_document(self, file_path: str) -> dict[str, Any]:
        """
        Process document header/metadata using GROBID.

        Args:
            file_path: Path to PDF file

        Returns:
            Dictionary of extracted metadata
        """
        if not Path(file_path).exists():
            logger.warning("GROBID input file does not exist: %s", file_path)
            return self._empty_metadata()

        candidate_urls = self._ordered_base_urls()
        for endpoint_index, base_url in enumerate(candidate_urls, start=1):
            for attempt in range(1, self.max_retries + 1):
                try:
                    with open(file_path, "rb") as fh:
                        files = {"input": fh}
                        response = self._request(
                            "POST",
                            self._endpoint_url(base_url, "/api/processHeaderDocument"),
                            files=files,
                            headers={"Accept": "application/xml", "Connection": "close"},
                        )

                    if response.status_code != 200:
                        logger.error(
                            "GROBID failed with status %s (endpoint=%s attempt=%s/%s endpoint_index=%s/%s)",
                            response.status_code,
                            base_url,
                            attempt,
                            self.max_retries,
                            endpoint_index,
                            len(candidate_urls),
                        )
                        if response.status_code in self.TRANSIENT_HTTP_STATUSES and attempt < self.max_retries:
                            time.sleep(self._retry_backoff_seconds(attempt))
                            continue
                        break

                    response_text = (response.text or "").lstrip()
                    if not response_text.startswith("<"):
                        logger.warning(
                            "GROBID returned non-XML payload (endpoint=%s attempt=%s/%s).",
                            base_url,
                            attempt,
                            self.max_retries,
                        )
                        if attempt < self.max_retries:
                            time.sleep(self._retry_backoff_seconds(attempt))
                            continue
                        break

                    self._mark_last_good_base_url(base_url, reason="process_header")
                    return self._parse_tei_xml(response_text)
                except RequestException as e:
                    logger.error(
                        "GROBID request failed (endpoint=%s attempt=%s/%s): %s",
                        base_url,
                        attempt,
                        self.max_retries,
                        e,
                    )
                    if attempt < self.max_retries:
                        time.sleep(self._retry_backoff_seconds(attempt))
                        continue
                    break
                except Exception as e:
                    logger.error(
                        "GROBID processing failed (endpoint=%s attempt=%s/%s): %s",
                        base_url,
                        attempt,
                        self.max_retries,
                        e,
                    )
                    if attempt < self.max_retries:
                        time.sleep(min(float(attempt), 2.0))
                        continue
                    break

            if endpoint_index < len(candidate_urls):
                logger.warning(
                    "GROBID failover: moving to next endpoint after failures (from=%s to=%s)",
                    base_url,
                    candidate_urls[endpoint_index],
                )

        return self._empty_metadata()

    @safe_function(fallback_value=[], error_message="GROBIDClient.process_references")
    def process_references(self, file_path: str) -> list[dict[str, Any]]:
        """
        Extract references using GROBID.
        """
        if not Path(file_path).exists():
            return []

        if not self.is_available():
            return []

        candidate_urls = self._ordered_base_urls()
        for endpoint_index, base_url in enumerate(candidate_urls, start=1):
            for attempt in range(1, self.max_retries + 1):
                try:
                    with open(file_path, "rb") as fh:
                        files = {"input": fh}
                        response = self._request(
                            "POST",
                            self._endpoint_url(base_url, "/api/processReferences"),
                            files=files,
                            headers={"Accept": "application/xml", "Connection": "close"},
                        )

                    if response.status_code != 200:
                        if response.status_code in self.TRANSIENT_HTTP_STATUSES and attempt < self.max_retries:
                            time.sleep(self._retry_backoff_seconds(attempt))
                            continue
                        break

                    self._mark_last_good_base_url(base_url, reason="process_references")
                    # Parsing logic would go here
                    return []
                except Exception as e:
                    logger.error(
                        "GROBID reference extraction failed (endpoint=%s attempt=%s/%s): %s",
                        base_url,
                        attempt,
                        self.max_retries,
                        e,
                    )
                    if attempt < self.max_retries:
                        time.sleep(min(float(attempt), 2.0))
                        continue
                    break

            if endpoint_index < len(candidate_urls):
                logger.warning(
                    "GROBID reference failover: moving to next endpoint (from=%s to=%s)",
                    base_url,
                    candidate_urls[endpoint_index],
                )
        return []

    def extract_metadata(self, file_path: str) -> dict[str, Any]:
        """
        Backward-compatible metadata extraction API.

        Combines header extraction with reference extraction and returns a
        single metadata dictionary expected by existing tools/tests.
        """
        if not self.is_available():
            raise GROBIDException("GROBID service not available")

        metadata = self.process_header_document(file_path)
        if not metadata:
            return {}

        references = self.process_references(file_path)
        metadata["references"] = references if references else []
        return metadata

    def _parse_tei_xml(self, xml_str: str) -> dict[str, Any]:
        """
        Parse GROBID TEI XML output into structured metadata.

        Args:
            xml_str: TEI XML string from GROBID

        Returns:
            Structured metadata dictionary
        """
        try:
            xml_str = (xml_str or "").lstrip("\ufeff \t\r\n")
            if not xml_str.startswith("<"):
                logger.warning("GROBID XML parse skipped: payload does not start with XML tag.")
                return self._empty_metadata()

            root = ET.fromstring(xml_str)  # nosec B314

            # Extract title
            title = self._extract_title(root)

            # Extract authors and affiliations
            authors, affiliations = self._extract_authors(root)

            # Extract abstract
            abstract = self._extract_abstract(root)

            # Extract keywords
            keywords = self._extract_keywords(root)

            return {
                "title": title,
                "authors": authors,
                "affiliations": affiliations,
                "abstract": abstract,
                "keywords": keywords,
                "raw_xml": xml_str,
                "source": "grobid",
                "confidence": self._calculate_confidence(title, authors),
            }

        except ET.ParseError as e:
            preview = (xml_str or "")[:120].replace("\n", " ").replace("\r", " ")
            logger.warning("Failed to parse GROBID XML (%s). Payload preview: %s", str(e), preview)
            return self._empty_metadata()

    def _extract_title(self, root: Element) -> str:
        """Extract document title from TEI XML."""
        title_elem = root.find(".//tei:titleStmt/tei:title[@type='main']", self.TEI_NS)
        if title_elem is not None and title_elem.text:
            return title_elem.text.strip()

        # Fallback: try any title
        title_elem = root.find(".//tei:titleStmt/tei:title", self.TEI_NS)
        if title_elem is not None and title_elem.text:
            return title_elem.text.strip()

        return ""

    def _extract_authors(self, root: Element) -> tuple[list[dict[str, str]], list[str]]:
        """
        Extract authors and affiliations from TEI XML.

        Returns:
            Tuple of (authors_list, affiliations_list)
        """
        authors = []
        affiliations_set = set()

        # Find all author elements
        author_elems = root.findall(".//tei:sourceDesc//tei:author", self.TEI_NS)

        for author_elem in author_elems:
            # Extract name
            given_name = ""
            family_name = ""

            persName = author_elem.find(".//tei:persName", self.TEI_NS)
            if persName is not None:
                forename = persName.find(".//tei:forename[@type='first']", self.TEI_NS)
                surname = persName.find(".//tei:surname", self.TEI_NS)

                if forename is not None and forename.text:
                    given_name = forename.text.strip()
                if surname is not None and surname.text:
                    family_name = surname.text.strip()

            # Extract affiliation
            affiliation = ""
            affiliation_elem = author_elem.find(".//tei:affiliation/tei:orgName[@type='institution']", self.TEI_NS)
            if affiliation_elem is not None and affiliation_elem.text:
                affiliation = affiliation_elem.text.strip()
                affiliations_set.add(affiliation)

            if given_name or family_name:
                authors.append(
                    {
                        "given": given_name,
                        "family": family_name,
                        "full_name": f"{given_name} {family_name}".strip(),
                        "affiliation": affiliation,
                    }
                )

        return authors, list(affiliations_set)

    def _extract_abstract(self, root: Element) -> str:
        """Extract abstract from TEI XML."""
        abstract_elem = root.find(".//tei:profileDesc/tei:abstract", self.TEI_NS)
        if abstract_elem is not None:
            # Get all text content, joining paragraphs
            paragraphs = abstract_elem.findall(".//tei:p", self.TEI_NS)
            if paragraphs:
                return " ".join(p.text.strip() for p in paragraphs if p.text)
            elif abstract_elem.text:
                return abstract_elem.text.strip()
        return ""

    def _extract_keywords(self, root: Element) -> list[str]:
        """Extract keywords from TEI XML."""
        keywords = []
        keyword_elems = root.findall(".//tei:keywords/tei:term", self.TEI_NS)
        for kw in keyword_elems:
            if kw.text:
                keywords.append(kw.text.strip())
        return keywords

    def _calculate_confidence(self, title: str, authors: list[dict]) -> float:
        """
        Calculate confidence score for extracted metadata.

        Score based on:
        - Title presence and length
        - Number of authors
        - Completeness of author names

        Returns:
            Confidence score (0.0 to 1.0)
        """
        score = 0.0

        # Title check (40% weight)
        if title:
            if len(title) > 10:
                score += 0.4
            else:
                score += 0.2

        # Authors check (40% weight)
        if authors:
            if len(authors) >= 1:
                score += 0.2
            if len(authors) >= 2:
                score += 0.1
            # Check name completeness
            complete_names = sum(1 for a in authors if a.get("given") and a.get("family"))
            if complete_names == len(authors):
                score += 0.1

        # Abstract/keywords (20% weight) - placeholder for future
        score += 0.2

        return min(score, 1.0)

    def _empty_metadata(self) -> dict[str, Any]:
        """Return empty metadata structure."""
        return {
            "title": "",
            "authors": [],
            "affiliations": [],
            "abstract": "",
            "keywords": [],
            "raw_xml": "",
            "source": "grobid",
            "confidence": 0.0,
        }


class GROBIDException(ExternalServiceError):
    """Exception raised for GROBID service errors."""

    def __init__(self, message: str = "GROBID service call failed.") -> None:
        super().__init__(service="GROBID", message=message)
