import logging
from pathlib import Path
from typing import Any

import httpx

from .exceptions import (
    AMFAuthenticationError,
    AMFConnectionError,
    AMFError,
    AMFFormattingError,
    AMFNotFoundError,
    AMFRateLimitError,
    AMFTimeoutError,
    AMFValidationError,
)
from .models import (
    FormattingStyle,
    Manuscript,
    ManuscriptResult,
    ValidationResult,
)

logger = logging.getLogger(__name__)


class AMFClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float = 30.0,
    ):
        self.base_url = (base_url or "http://localhost:8000").rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            headers=self._build_headers(),
        )

    def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _handle_response(self, response: httpx.Response):
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

    def format_manuscript(
        self,
        manuscript: Manuscript | dict[str, Any],
        style: str = "apa",
        options: dict[str, Any] | None = None,
    ) -> ManuscriptResult:
        if isinstance(manuscript, Manuscript):
            manuscript = manuscript.model_dump()

        payload = {"manuscript": manuscript, "style_id": style}
        if options:
            payload["options"] = options

        response = self._client.post("/api/v1/format", json=payload)
        data = self._handle_response(response)
        return ManuscriptResult(**data)

    def format_from_file(
        self,
        file_path: str | Path,
        style: str = "apa",
        options: dict[str, Any] | None = None,
    ) -> ManuscriptResult:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        text = path.read_text(encoding="utf-8")
        manuscript = Manuscript(
            title=path.stem,
            sections=[{"heading": "Content", "level": 1, "content": [{"text": text}]}],
        )
        return self.format_manuscript(manuscript, style, options)

    def validate_manuscript(
        self,
        manuscript: Manuscript | dict[str, Any],
        style: str = "apa",
    ) -> ValidationResult:
        if isinstance(manuscript, Manuscript):
            manuscript = manuscript.model_dump()

        response = self._client.post("/api/v1/validate", json={"manuscript": manuscript, "style_id": style})
        data = self._handle_response(response)
        return ValidationResult(**data)

    def get_styles(self) -> list[FormattingStyle]:
        response = self._client.get("/api/v1/styles")
        data = self._handle_response(response)
        return [FormattingStyle(**s) for s in data]

    def get_style(self, style_id: str) -> FormattingStyle:
        response = self._client.get(f"/api/v1/styles/{style_id}")
        data = self._handle_response(response)
        return FormattingStyle(**data)

    def get_preview(
        self,
        manuscript: Manuscript | dict[str, Any],
        style: str = "apa",
    ) -> str:
        if isinstance(manuscript, Manuscript):
            manuscript = manuscript.model_dump()

        response = self._client.post("/api/v1/preview", json={"manuscript": manuscript, "style_id": style})
        data = self._handle_response(response)
        return data.get("html", "")

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
