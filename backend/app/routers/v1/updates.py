"""Update management API routes."""

import logging

from fastapi import APIRouter, HTTPException

from app import __version__
from app.schemas.update_models import (
    ChannelsResponse,
    ReleaseNotesResponse,
    UpdateCheckRequest,
    UpdateCheckResponse,
    UpdateDownloadRequest,
    UpdateDownloadResponse,
    UpdateHistoryResponse,
    UpdateInstallResponse,
    UpdateRollbackResponse,
    UpdateSettings,
    UpdateSettingsUpdate,
    VersionInfoResponse,
)
from app.services.update_service import UpdateCheckMode, UpdateService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/updates", tags=["updates"])

_update_service = UpdateService(current_version=__version__)


def _get_service() -> UpdateService:
    return _update_service


@router.get("/check", response_model=UpdateCheckResponse, summary="Check for updates")
async def check_for_updates(
    channel: str | None = None,
    mode: str = "manual",
):
    service = _get_service()
    try:
        result = service.check_for_updates(
            channel=channel,
            mode=UpdateCheckMode(mode),
        )
        return UpdateCheckResponse(**result)
    except Exception as e:
        logger.error("Update check failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Update check failed: {e}")


@router.post("/check", response_model=UpdateCheckResponse, summary="Check for updates (POST)")
async def check_for_updates_post(
    request: UpdateCheckRequest,
):
    service = _get_service()
    try:
        result = service.check_for_updates(
            channel=request.channel,
            mode=UpdateCheckMode(request.mode or "manual"),
        )
        return UpdateCheckResponse(**result)
    except Exception as e:
        logger.error("Update check failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Update check failed: {e}")


@router.get("/version", response_model=VersionInfoResponse, summary="Get current version info")
async def get_version_info():
    service = _get_service()
    return VersionInfoResponse(**service.get_version_info())


@router.post("/download", response_model=UpdateDownloadResponse, summary="Download update")
async def download_update(
    request: UpdateDownloadRequest,
):
    service = _get_service()
    result = service.download_update(version=request.version)
    return UpdateDownloadResponse(**result)


@router.post("/install", response_model=UpdateInstallResponse, summary="Install update")
async def install_update():
    service = _get_service()
    result = service.install_update()
    return UpdateInstallResponse(**result)


@router.post("/rollback", response_model=UpdateRollbackResponse, summary="Rollback update")
async def rollback_update(
    version: str | None = None,
):
    service = _get_service()
    result = service.rollback(target_version=version)
    return UpdateRollbackResponse(**result)


@router.get("/history", response_model=UpdateHistoryResponse, summary="Get update history")
async def get_update_history(
    limit: int = 50,
):
    service = _get_service()
    history = service.get_history(limit=limit)
    return UpdateHistoryResponse(history=history)


@router.get("/release-notes", response_model=ReleaseNotesResponse, summary="Get release notes")
async def get_release_notes(
    version: str,
):
    service = _get_service()
    result = service.get_release_notes(version=version)
    return ReleaseNotesResponse(**result)


@router.get("/channels", response_model=ChannelsResponse, summary="List release channels")
async def get_channels():
    service = _get_service()
    channels = service.get_channels()
    return ChannelsResponse(channels=channels)


@router.get("/settings", response_model=UpdateSettings, summary="Get update settings")
async def get_update_settings():
    service = _get_service()
    return UpdateSettings(**service.get_settings())


@router.put("/settings", response_model=UpdateSettings, summary="Update update settings")
async def update_update_settings(
    request: UpdateSettingsUpdate,
):
    service = _get_service()
    updated = service.update_settings(request.settings)
    return UpdateSettings(**updated)
