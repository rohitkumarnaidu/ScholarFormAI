# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from fastapi import APIRouter

from app.routers.v2 import documents, webhooks

v2_router = APIRouter()
v2_router.include_router(documents.router, prefix="/documents", tags=["Documents v2"])
v2_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks v2"])
