"""Update management API routes for clients to check and download updates."""

import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.db.session import get_db

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
from app.models.update import UpdateRelease, UpdateChannel, UpdateApplication, UpdateArtifact

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/updates", tags=["updates"])

def get_update_service(db: Session = Depends(get_db)) -> UpdateService:
    return UpdateService(db=db, current_version=__version__)

@router.get("/check", response_model=UpdateCheckResponse, summary="Check for updates")
async def check_for_updates(
    app_name: str = "ScholarFormAI CLI",
    channel: str | None = None,
    mode: str = "manual",
    os: str = "windows",
    arch: str = "x64",
    current_version: str = "1.0.0",
    db: Session = Depends(get_db)
):
    service = get_update_service(db)
    try:
        result = service.check_for_updates(
            app_name=app_name,
            channel_name=channel,
            os_name=os,
            arch_name=arch,
            client_version=current_version,
            mode=UpdateCheckMode(mode),
        )
        return UpdateCheckResponse(**result)
    except Exception as e:
        logger.error("Update check failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Update check failed: {e}")

@router.post("/check", response_model=UpdateCheckResponse, summary="Check for updates (POST)")
async def check_for_updates_post(
    request: UpdateCheckRequest,
    db: Session = Depends(get_db)
):
    service = get_update_service(db)
    try:
        result = service.check_for_updates(
            app_name="ScholarFormAI CLI",
            channel_name=request.channel,
            os_name="windows",
            arch_name="x64",
            client_version=__version__,
            mode=UpdateCheckMode(request.mode or "manual"),
        )
        return UpdateCheckResponse(**result)
    except Exception as e:
        logger.error("Update check failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Update check failed: {e}")

@router.get("/version", response_model=VersionInfoResponse, summary="Get current version info")
async def get_version_info(service: UpdateService = Depends(get_update_service)):
    return VersionInfoResponse(**service.get_version_info())

@router.post("/download", response_model=UpdateDownloadResponse, summary="Download update")
async def download_update(
    request: UpdateDownloadRequest,
    service: UpdateService = Depends(get_update_service)
):
    result = service.download_update(version=request.version)
    return UpdateDownloadResponse(**result)

@router.post("/install", response_model=UpdateInstallResponse, summary="Install update")
async def install_update(service: UpdateService = Depends(get_update_service)):
    result = service.install_update()
    return UpdateInstallResponse(**result)

@router.post("/rollback", response_model=UpdateRollbackResponse, summary="Rollback update")
async def rollback_update(
    version: str | None = None,
    service: UpdateService = Depends(get_update_service)
):
    result = service.rollback(target_version=version)
    return UpdateRollbackResponse(**result)

@router.get("/history", response_model=UpdateHistoryResponse, summary="Get update history")
async def get_update_history(
    limit: int = 50,
    service: UpdateService = Depends(get_update_service)
):
    history = service.get_history(limit=limit)
    return UpdateHistoryResponse(history=history)

@router.get("/release-notes", response_model=ReleaseNotesResponse, summary="Get release notes")
async def get_release_notes(
    version: str,
    service: UpdateService = Depends(get_update_service)
):
    result = service.get_release_notes(version=version)
    return ReleaseNotesResponse(**result)

@router.get("/channels", response_model=ChannelsResponse, summary="List release channels")
async def get_channels(service: UpdateService = Depends(get_update_service)):
    channels = service.get_channels()
    return ChannelsResponse(channels=channels)

@router.get("/settings", response_model=UpdateSettings, summary="Get update settings")
async def get_update_settings(service: UpdateService = Depends(get_update_service)):
    return UpdateSettings(**service.get_settings())

@router.put("/settings", response_model=UpdateSettings, summary="Update update settings")
async def update_update_settings(
    request: UpdateSettingsUpdate,
    service: UpdateService = Depends(get_update_service)
):
    updated = service.update_settings(request.settings)
    return UpdateSettings(**updated)
