# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Path, Query, Request

from app import __version__
from app.schemas.update import (
    ChannelSchema,
    ReleaseNotesSchema,
    UpdateCheckRequest,
    UpdateCheckResponse,
    UpdateDownloadRequest,
    UpdateDownloadResponse,
    UpdateHistoryResponse,
    UpdateInstallRequest,
    UpdateInstallResponse,
    UpdateOfflineInstallRequest,
    UpdateRollbackRequest,
    UpdateRollbackResponse,
    UpdateSettingsSchema,
    UpdateSettingsUpdateSchema,
    UpdateVerifyRequest,
    UpdateVerifyResponse,
    VersionInfoSchema,
)
from app.services.update_service import UpdateCheckMode, UpdateService
from app.utils.logging_context import bind_request_context

from ._helpers import run_enveloped

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(bind_request_context)])

_update_service = UpdateService(current_version=__version__)


def get_update_service() -> UpdateService:
    return _update_service


@router.get("/check", summary="Check for updates (GET)")
async def check_updates_get(
    request: Request,
    channel: Optional[str] = Query(None, description="Release channel to check (stable, beta, nightly, pre-release)"),
    mode: str = Query("manual", description="Check mode (auto, manual, scheduled, startup)"),
    service: UpdateService = Depends(get_update_service),
) -> Dict[str, Any]:
    """Check for software updates using GET parameters."""
    async def operation():
        try:
            check_mode = UpdateCheckMode(mode)
        except ValueError:
            check_mode = UpdateCheckMode.MANUAL

        result = service.check_for_updates(channel=channel, mode=check_mode)
        return result

    return await run_enveloped(
        request,
        operation,
        logger=logger,
        operation_name="updates.check_get",
    )


@router.post("/check", summary="Check for updates (POST)")
async def check_updates_post(
    request: Request,
    body: UpdateCheckRequest,
    service: UpdateService = Depends(get_update_service),
) -> Dict[str, Any]:
    """Check for software updates using a POST payload."""
    async def operation():
        try:
            check_mode = UpdateCheckMode(body.mode or "manual")
        except ValueError:
            check_mode = UpdateCheckMode.MANUAL

        result = service.check_for_updates(
            channel=body.channel,
            mode=check_mode,
            current_version_override=body.current_version,
        )
        return result

    return await run_enveloped(
        request,
        operation,
        logger=logger,
        operation_name="updates.check_post",
    )


@router.get("/version", summary="Get application version and update system info")
async def get_version_info(
    request: Request,
    service: UpdateService = Depends(get_update_service),
) -> Dict[str, Any]:
    """Return version and update engine configuration information."""
    async def operation():
        return service.get_version_info()

    return await run_enveloped(
        request,
        operation,
        logger=logger,
        operation_name="updates.version",
    )


@router.post("/download", summary="Download update package")
async def download_update(
    request: Request,
    body: Optional[UpdateDownloadRequest] = None,
    service: UpdateService = Depends(get_update_service),
) -> Dict[str, Any]:
    """Download update release asset."""
    async def operation():
        req_version = body.version if body else None
        return service.download_update(version=req_version)

    return await run_enveloped(
        request,
        operation,
        logger=logger,
        operation_name="updates.download",
    )


@router.post("/install", summary="Install pending or downloaded update")
async def install_update(
    request: Request,
    body: Optional[UpdateInstallRequest] = None,
    service: UpdateService = Depends(get_update_service),
) -> Dict[str, Any]:
    """Execute installation of software update."""
    async def operation():
        req_version = body.version if body else None
        req_source = body.source_path if body else None
        return service.install_update(version=req_version, source_path=req_source)

    return await run_enveloped(
        request,
        operation,
        logger=logger,
        operation_name="updates.install",
    )


@router.post("/verify", summary="Verify asset integrity and digital signature")
async def verify_update_asset(
    request: Request,
    body: UpdateVerifyRequest,
    service: UpdateService = Depends(get_update_service),
) -> Dict[str, Any]:
    """Perform cryptographic SHA-256 digest and digital signature verification."""
    async def operation():
        if not body.file_path:
            return {
                "valid": False,
                "exists": False,
                "error": "file_path parameter is required",
                "checksum_valid": False,
                "signature_valid": False,
            }
        return service.verify_asset_integrity(
            file_path=body.file_path,
            expected_checksum=body.expected_checksum,
            checksum_algo=body.checksum_algo or "sha256",
            signature=body.signature,
            public_key=body.public_key,
        )

    return await run_enveloped(
        request,
        operation,
        logger=logger,
        operation_name="updates.verify",
    )


@router.post("/rollback", summary="Roll back application to previous backup version")
async def rollback_update(
    request: Request,
    body: Optional[UpdateRollbackRequest] = None,
    service: UpdateService = Depends(get_update_service),
) -> Dict[str, Any]:
    """Execute application version rollback."""
    async def operation():
        target_v = body.target_version if body else None
        return service.rollback(target_version=target_v)

    return await run_enveloped(
        request,
        operation,
        logger=logger,
        operation_name="updates.rollback",
    )


@router.get("/history", summary="Get update installation history audit log")
async def get_update_history(
    request: Request,
    limit: int = Query(50, ge=1, le=500, description="Max history items to return"),
    service: UpdateService = Depends(get_update_service),
) -> Dict[str, Any]:
    """Retrieve audit history log of update attempts."""
    async def operation():
        history = service.get_history(limit=limit)
        return {"history": history}

    return await run_enveloped(
        request,
        operation,
        logger=logger,
        operation_name="updates.history",
    )


@router.get("/channels", summary="List available release channels")
async def get_channels(
    request: Request,
    service: UpdateService = Depends(get_update_service),
) -> Dict[str, Any]:
    """List release distribution channels (stable, beta, nightly, pre-release)."""
    async def operation():
        channels = service.get_channels()
        return {"channels": channels}

    return await run_enveloped(
        request,
        operation,
        logger=logger,
        operation_name="updates.channels",
    )


@router.get("/settings", summary="Get current update management settings")
async def get_update_settings(
    request: Request,
    service: UpdateService = Depends(get_update_service),
) -> Dict[str, Any]:
    """Get active update configuration settings."""
    async def operation():
        return service.get_settings()

    return await run_enveloped(
        request,
        operation,
        logger=logger,
        operation_name="updates.get_settings",
    )


@router.put("/settings", summary="Update update management settings")
async def update_settings(
    request: Request,
    body: UpdateSettingsUpdateSchema,
    service: UpdateService = Depends(get_update_service),
) -> Dict[str, Any]:
    """Update active update configuration settings."""
    async def operation():
        return service.update_settings(body.settings)

    return await run_enveloped(
        request,
        operation,
        logger=logger,
        operation_name="updates.put_settings",
    )



@router.post("/install-offline", summary="Install offline update package")
async def install_offline_update(
    request: Request,
    body: UpdateOfflineInstallRequest,
    service: UpdateService = Depends(get_update_service),
) -> Dict[str, Any]:
    """Execute installation of offline archive update package (.zip or .tar.gz)."""
    async def operation():
        return service.install_offline_update(
            archive_path=body.archive_path,
            signature=body.signature,
            public_key=body.public_key,
        )

    return await run_enveloped(
        request,
        operation,
        logger=logger,
        operation_name="updates.install_offline",
    )


@router.get("/release-notes", summary="Get release notes (query parameter)")
async def get_release_notes_query(
    request: Request,
    version: Optional[str] = Query(None, description="Release version tag"),
    service: UpdateService = Depends(get_update_service),
) -> Dict[str, Any]:
    """Fetch release notes for a specified version tag via query parameter."""
    async def operation():
        target_v = version
        if not target_v:
            v_info = service.get_version_info()
            target_v = v_info.get("current_version", "1.0.0")
        return service.get_release_notes(version=target_v)

    return await run_enveloped(
        request,
        operation,
        logger=logger,
        operation_name="updates.release_notes_query",
    )


@router.get("/release-notes/{version}", summary="Get release notes for specific version (path parameter)")
async def get_release_notes_path(
    request: Request,
    version: str = Path(..., description="Release version tag"),
    service: UpdateService = Depends(get_update_service),
) -> Dict[str, Any]:
    """Fetch release notes for a specified version tag via path parameter."""
    async def operation():
        return service.get_release_notes(version=version)

    return await run_enveloped(
        request,
        operation,
        logger=logger,
        operation_name="updates.release_notes_path",
    )
