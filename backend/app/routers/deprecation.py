# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from typing import Mapping, Optional

from fastapi import HTTPException, Request
from fastapi.routing import APIRoute

DEPRECATION_DATE = "2026-05-01"


def build_deprecation_headers(successor_path: Optional[str]) -> dict[str, str]:
    headers = {
        "Deprecation": "true",
        "Sunset": DEPRECATION_DATE,
    }
    if successor_path:
        headers["Link"] = f'<{successor_path}>; rel="successor-version"'
    return headers


def normalize_path(path: str) -> str:
    if path != "/" and path.endswith("/"):
        return path.rstrip("/")
    return path


class DeprecatedRoute(APIRoute):
    successor_map: Mapping[str, str] = {}

    def _successor_path(self) -> Optional[str]:
        path_format = getattr(self, "path_format", self.path)
        normalized = normalize_path(path_format)
        return self.successor_map.get(path_format) or self.successor_map.get(normalized)

    def get_route_handler(self):
        original_route_handler = super().get_route_handler()
        headers = build_deprecation_headers(self._successor_path())

        async def custom_route_handler(request: Request):
            try:
                response = await original_route_handler(request)
            except HTTPException as exc:
                raise HTTPException(
                    status_code=exc.status_code,
                    detail=exc.detail,
                    headers={**(exc.headers or {}), **headers},
                ) from exc

            response.headers.update(headers)
            return response

        return custom_route_handler
