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
    updates,
    webhooks,
)

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(health.router, prefix="/health", tags=["Health v1"])
v1_router.include_router(auth.router, prefix="/auth", tags=["Auth v1"])
v1_router.include_router(config.router, prefix="/config", tags=["Config v1"])
v1_router.include_router(documents.router, prefix="/documents", tags=["Documents v1"])
v1_router.include_router(templates.router, prefix="/templates", tags=["Templates v1"])
v1_router.include_router(generator.router, prefix="/generator", tags=["Generator v1"])
v1_router.include_router(synthesis.router, prefix="/synthesis", tags=["Synthesis v1"])
v1_router.include_router(feedback.router, prefix="/feedback", tags=["Feedback v1"])
v1_router.include_router(metrics.router, prefix="/metrics", tags=["Metrics v1"])
v1_router.include_router(providers.router, prefix="/providers")
v1_router.include_router(api_keys.router, prefix="/keys")
v1_router.include_router(stream.router, prefix="/stream", tags=["Streaming v1"])
v1_router.include_router(billing.router)
v1_router.include_router(activity.router, prefix="/activity", tags=["Activity v1"])
v1_router.include_router(suggestions.router, prefix="/suggestions", tags=["Suggestions v1"])
v1_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks v1"])
v1_router.include_router(updates.router, prefix="/updates", tags=["Updates v1"])
