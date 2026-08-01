import logging
from typing import Any, Dict, List, Optional, Union

import httpx

from .exceptions import (
    AMFAuthenticationError,
    AMFConnectionError,
    AMFFormattingError,
    AMFNotFoundError,
    AMFRateLimitError,
    AMFTimeoutError,
    AMFValidationError,
    AMFError,
)
from .models import (
    FormattingStyle,
    Manuscript,
    ManuscriptResult,
    ValidationResult,
)

logger = logging.getLogger(__name__)


class AsyncAMFClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.base_url = (base_url or "http://localhost:8000").rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers=self._build_headers(),
        )

    def _build_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def _handle_response(self, response: httpx.Response):
        if response.is_success:
            return response.json()

        error_map = {
            400: AMFValidationError,
            401: AMFAuthenticationError,
            404: AMFNotFoundError,
            422: AMFFormattingError,
            429: AMFRateLimitError,
            503: AMFConnectionError,
            504: AMFTimeoutError,
        }

        error_class = error_map.get(response.status_code, AMFError)
        try:
            detail = response.json()
            msg = detail.get("message", detail.get("detail", str(response.text)))
        except Exception:
            msg = response.text

        raise error_class(msg)

    async def format_manuscript(
        self,
        manuscript: Union[Manuscript, Dict[str, Any]],
        style: str = "apa",
        options: Optional[Dict[str, Any]] = None,
    ) -> ManuscriptResult:
        if isinstance(manuscript, Manuscript):
            manuscript = manuscript.model_dump()

        payload = {"manuscript": manuscript, "style_id": style}
        if options:
            payload["options"] = options

        response = await self._client.post("/api/v1/format", json=payload)
        data = await self._handle_response(response)
        return ManuscriptResult(**data)

    async def validate_manuscript(
        self,
        manuscript: Union[Manuscript, Dict[str, Any]],
        style: str = "apa",
    ) -> ValidationResult:
        if isinstance(manuscript, Manuscript):
            manuscript = manuscript.model_dump()

        response = await self._client.post("/api/v1/validate", json={"manuscript": manuscript, "style_id": style})
        data = await self._handle_response(response)
        return ValidationResult(**data)

    async def get_styles(self) -> List[FormattingStyle]:
        response = await self._client.get("/api/v1/styles")
        data = await self._handle_response(response)
        return [FormattingStyle(**s) for s in data]

    async def get_style(self, style_id: str) -> FormattingStyle:
        response = await self._client.get(f"/api/v1/styles/{style_id}")
        data = await self._handle_response(response)
        return FormattingStyle(**data)

    async def get_preview(
        self,
        manuscript: Union[Manuscript, Dict[str, Any]],
        style: str = "apa",
    ) -> str:
        if isinstance(manuscript, Manuscript):
            manuscript = manuscript.model_dump()

        response = await self._client.post("/api/v1/preview", json={"manuscript": manuscript, "style_id": style})
        data = await self._handle_response(response)
        return data.get("html", "")

    async def close(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
