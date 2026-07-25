import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

from amf.config import AMFConfig

logger = logging.getLogger(__name__)

_API_RETRIES = 2
_API_TIMEOUT = 60
_RETRY_DELAY = 1.0


class BackendError(Exception):
    def __init__(self, message: str, exit_code: int = 1):
        self.message = message
        self.exit_code = exit_code
        super().__init__(message)


class BackendClient:
    def __init__(self, config: AMFConfig | None = None):
        self.config = config or AMFConfig()
        self._requests = None
        self._local_available = False
        self._local_loaded = False

    # ------------------------------------------------------------------
    # Import helpers (lazy — only pay for what you use)
    # ------------------------------------------------------------------

    def _ensure_requests(self):
        if self._requests is None:
            try:
                import requests as req
                self._requests = req
            except ImportError:
                self._requests = False
        return self._requests

    def _ensure_local(self):
        if not self._local_loaded:
            try:
                from app.services.formatter import ManuscriptFormatter as _FmtCls  # noqa: F401
                from app.services.parser import ManuscriptParser as _PCls  # noqa: F401
                from app.services.validator import ManuscriptValidator as _VCls  # noqa: F401
                from app.services.style_registry import StyleRegistry as _SCls  # noqa: F401
                from app.api.models import Manuscript, Paragraph, Section  # noqa: F401

                self._ManuscriptFormatter = _FmtCls
                self._ManuscriptParser = _PCls
                self._ManuscriptValidator = _VCls
                self._StyleRegistry = _SCls
                self._Manuscript = Manuscript
                self._Paragraph = Paragraph
                self._Section = Section
                self._local_available = True
            except ModuleNotFoundError:
                self._local_available = False
            self._local_loaded = True
        return self._local_available

    def _ensure_backend(self):
        if not self._ensure_local():
            raise BackendError(
                "Backend modules not found. Install the backend package or start the API server.\n"
                "  pip install -e backend/",
                exit_code=2,
            )

    # ------------------------------------------------------------------
    # API helpers
    # ------------------------------------------------------------------

    def _api_url(self) -> str:
        return self.config.get("api_endpoint", "http://localhost:8000")

    def _api_post(self, endpoint: str, payload: dict) -> dict:
        req = self._ensure_requests()
        if not req:
            raise BackendError("requests library not available", exit_code=2)

        url = f"{self._api_url()}/api/v1/{endpoint}"
        last_exc: Exception | None = None
        for attempt in range(1 + _API_RETRIES):
            try:
                resp = req.post(url, json=payload, timeout=_API_TIMEOUT)
                resp.raise_for_status()
                return resp.json()
            except req.exceptions.ConnectionError as exc:
                last_exc = exc
                if attempt < _API_RETRIES:
                    time.sleep(_RETRY_DELAY)
            except req.exceptions.Timeout as exc:
                last_exc = exc
                if attempt < _API_RETRIES:
                    time.sleep(_RETRY_DELAY)
            except req.exceptions.HTTPError as exc:
                resp = exc.response
                status = resp.status_code if resp is not None else 0
                detail = ""
                try:
                    detail = resp.json().get("detail", "") if resp is not None else ""
                except Exception:
                    pass
                raise BackendError(
                    f"API error ({status}): {detail or resp.reason if resp else 'unknown'}",
                    exit_code=1,
                )
            except req.exceptions.RequestException as exc:
                last_exc = exc
                if attempt < _API_RETRIES:
                    time.sleep(_RETRY_DELAY)
        raise BackendError(
            f"API server unavailable after {1 + _API_RETRIES} attempts: {last_exc}",
            exit_code=1,
        )

    def _api_get(self, endpoint: str, params: dict | None = None) -> dict | list:
        req = self._ensure_requests()
        if not req:
            raise BackendError("requests library not available", exit_code=2)

        url = f"{self._api_url()}/api/v1/{endpoint}"
        try:
            resp = req.get(url, params=params, timeout=_API_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except req.exceptions.RequestException as exc:
            raise BackendError(f"API error: {exc}", exit_code=1)

    # ------------------------------------------------------------------
    # Build manuscript payload from raw text
    # ------------------------------------------------------------------

    def _build_payload(self, title: str, text: str, style: str, options: dict | None = None) -> dict:
        return {
            "manuscript": {
                "title": title,
                "sections": [{"heading": "Content", "level": 1, "content": [{"text": text}]}],
            },
            "style_id": style,
            "options": options or {},
        }

    def _build_manuscript_model(self, title: str, text: str):
        self._ensure_backend()
        return self._Manuscript(
            title=title,
            sections=[self._Section(heading="Content", level=1, content=[self._Paragraph(text=text)])],
        )

    # ------------------------------------------------------------------
    # Format
    # ------------------------------------------------------------------

    def format(self, input_file: Path, output_file: Path, style: str, options: dict | None = None) -> dict:
        text = input_file.read_text(encoding="utf-8")

        req = self._ensure_requests()
        if req:
            try:
                payload = self._build_payload(input_file.stem, text, style, options)
                result = self._api_post("format", payload)
                if "download_url" in result:
                    self._download_docx(result["download_url"], output_file)
                return result
            except BackendError as exc:
                if exc.exit_code == 1:
                    logger.info("API unavailable, falling back to local formatter: %s", exc.message)
                else:
                    raise

        self._format_local(input_file, output_file, style, text)
        return {"pages": "N/A", "style_applied": style}

    def _download_docx(self, download_url: str, output_file: Path):
        req = self._ensure_requests()
        url = download_url if download_url.startswith("http") else f"{self._api_url()}{download_url}"
        resp = req.get(url, timeout=_API_TIMEOUT)
        resp.raise_for_status()
        output_file.write_bytes(resp.content)

    def _format_local(self, input_file: Path, output_file: Path, style: str, text: str):
        self._ensure_backend()
        formatter = self._ManuscriptFormatter()
        registry = self._StyleRegistry()
        formatting_style = registry.get_style(style)
        if not formatting_style:
            raise BackendError(f"Style '{style}' not found", exit_code=1)
        manuscript = self._build_manuscript_model(input_file.stem, text)
        formatter.format(manuscript, formatting_style, str(output_file))

    # ------------------------------------------------------------------
    # Validate
    # ------------------------------------------------------------------

    def validate(self, input_file: Path, style: str) -> dict:
        text = input_file.read_text(encoding="utf-8")

        req = self._ensure_requests()
        if req:
            try:
                payload = self._build_payload(input_file.stem, text, style)
                return self._api_post("validate", payload)
            except BackendError as exc:
                if exc.exit_code == 1:
                    logger.info("API unavailable, falling back to local validator: %s", exc.message)
                else:
                    raise

        return self._validate_local(text, style)

    def _validate_local(self, text: str, style: str) -> dict:
        self._ensure_backend()
        parser = self._ManuscriptParser()
        validator = self._ManuscriptValidator()
        manuscript = parser.parse(text)
        result = validator.validate(manuscript, style)
        if hasattr(result, "model_dump"):
            return result.model_dump()
        if isinstance(result, dict):
            return result
        return json.loads(json.dumps(result, default=str))

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    def preview(self, input_file: Path, style: str) -> str:
        text = input_file.read_text(encoding="utf-8")

        req = self._ensure_requests()
        if req:
            try:
                payload = self._build_payload(input_file.stem, text, style)
                result = self._api_post("preview", payload)
                return result.get("html", "")
            except BackendError as exc:
                if exc.exit_code == 1:
                    logger.info("API unavailable, falling back to local preview: %s", exc.message)
                else:
                    raise

        return self._preview_local(input_file.stem, text, style)

    def _preview_local(self, title: str, text: str, style: str) -> str:
        self._ensure_backend()
        formatter = self._ManuscriptFormatter()
        registry = self._StyleRegistry()
        formatting_style = registry.get_style(style)
        if not formatting_style:
            raise BackendError(f"Style '{style}' not found", exit_code=1)
        manuscript = self._build_manuscript_model(title, text)
        html = formatter.generate_html_preview(manuscript, formatting_style)
        return html

    # ------------------------------------------------------------------
    # Styles
    # ------------------------------------------------------------------

    def list_styles(self) -> list[dict]:
        req = self._ensure_requests()
        if req:
            try:
                result = self._api_get("styles")
                if isinstance(result, list):
                    return result
                if isinstance(result, dict):
                    return result.get("styles", result.get("data", []))
            except BackendError:
                pass

        self._ensure_backend()
        registry = self._StyleRegistry()
        return registry.list_styles()

    def get_style(self, name: str) -> dict | None:
        req = self._ensure_requests()
        if req:
            try:
                result = self._api_get(f"styles/{name}")
                if isinstance(result, dict):
                    return result
            except BackendError:
                pass

        self._ensure_backend()
        registry = self._StyleRegistry()
        s = registry.get_style(name)
        if s is None:
            return None
        return {
            "id": name,
            "name": getattr(s, "name", name),
            "version": getattr(s, "version", ""),
            "description": getattr(s, "description", ""),
            "citation_format": getattr(s, "citation_format", name),
        }
