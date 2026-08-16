# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def get_webhooks():
    return {"message": "Not implemented"}
