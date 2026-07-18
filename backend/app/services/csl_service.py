# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
CSL Service Facade — routes citation style operations through the service layer.

Routers MUST use this facade instead of importing csl_fetcher directly.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.exceptions import NotFoundError, ExternalServiceError, ValidationError

logger = logging.getLogger(__name__)


class CslService:
    """
    Facade for CSL (Citation Style Language) operations.

    Encapsulates all direct csl_fetcher pipeline imports behind a stable interface.
    """

    async def resolve_citation(self, citation_key: str) -> dict[str, Any]:
        """
        Resolve a citation key to its full bibliographic data.

        Args:
            citation_key: The citation key (e.g., DOI, ISBN, or raw key).

        Returns:
            A dict with bibliographic fields.

        Raises:
            NotFoundError: If the citation cannot be resolved.
            ExternalServiceError: If the external resolution service fails.
        """
        if not citation_key or not citation_key.strip():
            raise ValidationError(
                message="Citation key is required.",
                details={"citation_key": citation_key},
            )

        try:
            from app.pipeline.services.csl_fetcher import fetch_style

            result = await fetch_style(citation_key.strip())
            if not result:
                raise NotFoundError(
                    message=f"Citation '{citation_key}' could not be resolved.",
                    details={"citation_key": citation_key},
                )
            return {"citation_key": citation_key, "data": result}
        except NotFoundError:
            raise
        except ValueError as exc:
            raise ValidationError(
                message=str(exc),
                details={"citation_key": citation_key},
            ) from exc
        except Exception as exc:
            logger.error("Citation resolution failed for '%s': %s", citation_key, exc)
            raise ExternalServiceError(
                service="csl_fetcher",
                message=f"Failed to resolve citation '{citation_key}'.",
                details={"citation_key": citation_key, "error": str(exc)},
            ) from exc

    async def fetch_csl_style(self, style_name: str) -> dict[str, Any]:
        """
        Fetch a CSL style definition by name.

        Args:
            style_name: The style name or slug (e.g., 'apa', 'ieee').

        Returns:
            A dict with the CSL style XML and metadata.

        Raises:
            NotFoundError: If the style is not found.
            ExternalServiceError: If the fetch fails.
        """
        slug = (style_name or "").strip()
        if not slug:
            raise ValidationError(
                message="Style name/slug is required.",
                details={"style_name": style_name},
            )

        try:
            from app.pipeline.services.csl_fetcher import fetch_style

            style = await fetch_style(slug)
            if not style:
                raise NotFoundError(
                    message=f"CSL style '{slug}' not found.",
                    details={"style_name": slug},
                )
            return {"style": style, "slug": slug}
        except NotFoundError:
            raise
        except ValueError as exc:
            raise ValidationError(
                message=str(exc),
                details={"style_name": slug},
            ) from exc
        except Exception as exc:
            logger.error("CSL style fetch failed for '%s': %s", slug, exc)
            raise ExternalServiceError(
                service="csl_fetcher",
                message=f"Failed to fetch CSL style '{slug}'.",
                details={"style_name": slug, "error": str(exc)},
            ) from exc

    async def search_csl_styles(
        self,
        query: str,
    ) -> dict[str, Any]:
        """
        Search for CSL styles by keyword.

        Args:
            query: The search query string.

        Returns:
            A dict with query and results list.

        Raises:
            ValidationError: If the query is empty.
            ExternalServiceError: If the search fails.
        """
        search_query = (query or "").strip()
        if not search_query:
            raise ValidationError(
                message="Search query is required.",
                details={"query": query},
            )

        try:
            from app.pipeline.services.csl_fetcher import search_styles

            results = await search_styles(search_query)
            return {"query": search_query, "results": results}
        except Exception as exc:
            logger.error("CSL style search failed for '%s': %s", search_query, exc)
            raise ExternalServiceError(
                service="csl_fetcher",
                message="CSL style search failed.",
                details={"query": search_query, "error": str(exc)},
            ) from exc


# Singleton for dependency injection
csl_service = CslService()
