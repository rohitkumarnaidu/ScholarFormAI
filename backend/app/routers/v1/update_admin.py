"""Admin API routes for managing updates."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.update import (
    UpdateApplication,
    UpdateChannel,
    UpdateRelease,
    UpdateArtifact,
)
from app.schemas.update_admin import (
    UpdateApplicationCreate,
    UpdateApplicationResponse,
    UpdateChannelCreate,
    UpdateChannelResponse,
    UpdateReleaseCreate,
    UpdateReleaseResponse,
    UpdateArtifactCreate,
    UpdateArtifactResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/updates", tags=["admin-updates"])


# --- Applications ---


@router.get("/applications", response_model=list[UpdateApplicationResponse])
def list_applications(db: Session = Depends(get_db)):
    apps = db.query(UpdateApplication).all()
    return apps


@router.post("/applications", response_model=UpdateApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_application(app_in: UpdateApplicationCreate, db: Session = Depends(get_db)):
    db_app = db.query(UpdateApplication).filter(UpdateApplication.name == app_in.name).first()
    if db_app:
        raise HTTPException(status_code=400, detail="Application with this name already exists")

    app_obj = UpdateApplication(**app_in.model_dump())
    db.add(app_obj)
    db.commit()
    db.refresh(app_obj)
    return app_obj


# --- Channels ---


@router.get("/channels", response_model=list[UpdateChannelResponse])
def list_channels(app_id: UUID | None = None, db: Session = Depends(get_db)):
    query = db.query(UpdateChannel)
    if app_id:
        query = query.filter(UpdateChannel.app_id == app_id)
    return query.all()


@router.post("/channels", response_model=UpdateChannelResponse, status_code=status.HTTP_201_CREATED)
def create_channel(channel_in: UpdateChannelCreate, db: Session = Depends(get_db)):
    db_app = db.query(UpdateApplication).filter(UpdateApplication.id == channel_in.app_id).first()
    if not db_app:
        raise HTTPException(status_code=404, detail="Application not found")

    db_channel = (
        db.query(UpdateChannel)
        .filter(UpdateChannel.app_id == channel_in.app_id, UpdateChannel.name == channel_in.name)
        .first()
    )
    if db_channel:
        raise HTTPException(status_code=400, detail="Channel with this name already exists for this app")

    channel_obj = UpdateChannel(**channel_in.model_dump())
    db.add(channel_obj)
    db.commit()
    db.refresh(channel_obj)
    return channel_obj


# --- Releases ---


@router.get("/releases", response_model=list[UpdateReleaseResponse])
def list_releases(app_id: UUID | None = None, channel_id: UUID | None = None, db: Session = Depends(get_db)):
    query = db.query(UpdateRelease)
    if app_id:
        query = query.filter(UpdateRelease.app_id == app_id)
    if channel_id:
        query = query.filter(UpdateRelease.channel_id == channel_id)
    return query.all()


@router.post("/releases", response_model=UpdateReleaseResponse, status_code=status.HTTP_201_CREATED)
def create_release(release_in: UpdateReleaseCreate, db: Session = Depends(get_db)):
    db_app = db.query(UpdateApplication).filter(UpdateApplication.id == release_in.app_id).first()
    if not db_app:
        raise HTTPException(status_code=404, detail="Application not found")

    db_channel = db.query(UpdateChannel).filter(UpdateChannel.id == release_in.channel_id).first()
    if not db_channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    release_obj = UpdateRelease(**release_in.model_dump())
    db.add(release_obj)
    db.commit()
    db.refresh(release_obj)
    return release_obj


# --- Artifacts ---


@router.get("/artifacts", response_model=list[UpdateArtifactResponse])
def list_artifacts(release_id: UUID | None = None, db: Session = Depends(get_db)):
    query = db.query(UpdateArtifact)
    if release_id:
        query = query.filter(UpdateArtifact.release_id == release_id)
    return query.all()


@router.post("/artifacts", response_model=UpdateArtifactResponse, status_code=status.HTTP_201_CREATED)
def create_artifact(artifact_in: UpdateArtifactCreate, db: Session = Depends(get_db)):
    db_release = db.query(UpdateRelease).filter(UpdateRelease.id == artifact_in.release_id).first()
    if not db_release:
        raise HTTPException(status_code=404, detail="Release not found")

    artifact_obj = UpdateArtifact(**artifact_in.model_dump())
    db.add(artifact_obj)
    db.commit()
    db.refresh(artifact_obj)
    return artifact_obj
