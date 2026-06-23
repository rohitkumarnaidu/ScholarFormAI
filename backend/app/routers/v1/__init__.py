# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from fastapi import APIRouter

from . import (
    auth,
    billing,
    documents,
    feedback,
    generator,
    health,
    metrics,
    stream,
    synthesis,
    templates,
)

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(health.router, prefix="/health", tags=["Health v1"])
v1_router.include_router(auth.router, prefix="/auth", tags=["Auth v1"])
v1_router.include_router(documents.router, prefix="/documents", tags=["Documents v1"])
v1_router.include_router(templates.router, prefix="/templates", tags=["Templates v1"])
v1_router.include_router(generator.router, prefix="/generator", tags=["Generator v1"])
v1_router.include_router(synthesis.router, prefix="/synthesis", tags=["Synthesis v1"])
v1_router.include_router(feedback.router, prefix="/feedback", tags=["Feedback v1"])
v1_router.include_router(metrics.router, prefix="/metrics", tags=["Metrics v1"])
v1_router.include_router(stream.router, prefix="/stream", tags=["Streaming v1"])
v1_router.include_router(billing.router)
