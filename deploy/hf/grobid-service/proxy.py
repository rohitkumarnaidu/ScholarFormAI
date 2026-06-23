# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import os
from typing import Dict

import requests
from fastapi import FastAPI, Request, Response

TARGET_BASE = os.getenv("GROBID_INTERNAL_URL", "http://127.0.0.1:8070").rstrip("/")

app = FastAPI(title="Scholarform GROBID Proxy", version="1.0.0")


def _filtered_headers(headers: Dict[str, str]) -> Dict[str, str]:
    return {
        k: v
        for k, v in headers.items()
        if k.lower() not in {"host", "connection", "content-length"}
    }


def _response_headers(headers: Dict[str, str]) -> Dict[str, str]:
    return {
        k: v
        for k, v in headers.items()
        if k.lower() not in {"content-encoding", "transfer-encoding", "connection"}
    }


@app.get("/")
def root() -> Dict[str, str]:
    return {"status": "ok", "service": "grobid-proxy", "target": TARGET_BASE}


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy(path: str, request: Request) -> Response:
    upstream_url = f"{TARGET_BASE}/{path}"
    body = await request.body()

    upstream_resp = requests.request(
        method=request.method,
        url=upstream_url,
        params=dict(request.query_params),
        headers=_filtered_headers(dict(request.headers)),
        data=body,
        timeout=(10, 180),
    )

    return Response(
        content=upstream_resp.content,
        status_code=upstream_resp.status_code,
        headers=_response_headers(dict(upstream_resp.headers)),
    )

