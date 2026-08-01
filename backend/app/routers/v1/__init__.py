# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from fastapi import APIRouter

from . import (
    activity,
    api_keys,
    auth,
    billing,
    config,
    documents,
    feedback,
    generator,
    health,
    metrics,
    providers,
    stream,
    suggestions,
    synthesis,
    templates,
    webhooks,
)

v1_router = APIRouter(prefix="/api/v1")

for router_module, prefix, tags in [
    (health.router, "/health", ["Health v1"]),
    (auth.router, "/auth", ["Auth v1"]),
    (config.router, "/config", ["Config v1"]),
    (documents.router, "/documents", ["Documents v1"]),
    (templates.router, "/templates", ["Templates v1"]),
    (generator.router, "/generator", ["Generator v1"]),
    (synthesis.router, "/synthesis", ["Synthesis v1"]),
    (feedback.router, "/feedback", ["Feedback v1"]),
    (metrics.router, "/metrics", ["Metrics v1"]),
    (providers.router, "/providers", []),
    (api_keys.router, "/keys", []),
    (stream.router, "/stream", ["Streaming v1"]),
    (billing.router, "", []),
    (activity.router, "/activity", ["Activity v1"]),
    (suggestions.router, "/suggestions", ["Suggestions v1"]),
    (webhooks.router, "/webhooks", ["Webhooks v1"]),
]:
    try:
        if tags:
            v1_router.include_router(router_module, prefix=prefix, tags=tags)
        elif prefix:
            v1_router.include_router(router_module, prefix=prefix)
        else:
            v1_router.include_router(router_module)
    except AssertionError as e:
        if "already includes" not in str(e):
            raise

