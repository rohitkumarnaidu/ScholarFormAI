"""Incoming GitHub Webhook for Update Management."""

import logging
from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.update import UpdateApplication, UpdateChannel, UpdateRelease, UpdateArtifact
from app.services.update_service import UpdateService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/github", tags=["admin-updates"])

@router.post("/release")
async def github_release_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Listens for GitHub release events and inserts them into our DB.
    Requires configuring a GitHub Webhook with Content-Type: application/json.
    """
    event_type = request.headers.get("X-GitHub-Event")
    if event_type != "release":
        return {"status": "ignored", "reason": f"Event type {event_type} not supported"}
        
    payload = await request.json()
    action = payload.get("action")
    if action not in ["published", "released"]:
        return {"status": "ignored", "reason": f"Action {action} ignored"}
        
    release_data = payload.get("release", {})
    repo_data = payload.get("repository", {})
    
    # 1. Match repository to our UpdateApplication
    repo_name = repo_data.get("name")
    app = db.query(UpdateApplication).filter(UpdateApplication.name.ilike(f"%{repo_name}%")).first()
    
    if not app:
        # Auto-create app if missing (optional based on enterprise policy)
        app = UpdateApplication(name=repo_name, description=f"Auto-created for {repo_name}")
        db.add(app)
        db.commit()
        db.refresh(app)
        
    # 2. Determine Channel (Stable vs Beta/Pre-release)
    is_prerelease = release_data.get("prerelease", False)
    channel_name = "beta" if is_prerelease else "stable"
    
    channel = db.query(UpdateChannel).filter(
        UpdateChannel.app_id == app.id,
        UpdateChannel.name == channel_name
    ).first()
    
    if not channel:
        channel = UpdateChannel(app_id=app.id, name=channel_name, is_active=True)
        db.add(channel)
        db.commit()
        db.refresh(channel)
        
    # 3. Create the Release record
    tag_name = release_data.get("tag_name", "").lstrip("v")
    body = release_data.get("body", "")
    
    existing_release = db.query(UpdateRelease).filter(
        UpdateRelease.app_id == app.id,
        UpdateRelease.version == tag_name
    ).first()
    
    if existing_release:
        return {"status": "ignored", "reason": "Release already exists"}
        
    is_mandatory = "mandatory" in body.lower() or "critical" in body.lower()
    is_security = "security" in body.lower() or "cve" in body.lower()
    
    release = UpdateRelease(
        app_id=app.id,
        channel_id=channel.id,
        version=tag_name,
        release_notes=body,
        is_mandatory=is_mandatory,
        is_security_update=is_security,
        github_release_id=str(release_data.get("id"))
    )
    db.add(release)
    db.commit()
    db.refresh(release)
    
    # 4. Create Artifact records for each asset
    assets = release_data.get("assets", [])
    for asset in assets:
        name = asset.get("name", "").lower()
        
        # Simple OS/Arch inference from filename
        os_name = "windows"
        if "mac" in name or "darwin" in name:
            os_name = "macos"
        elif "linux" in name:
            os_name = "linux"
            
        arch = "x64"
        if "arm" in name or "aarch64" in name:
            arch = "arm64"
            
        artifact = UpdateArtifact(
            release_id=release.id,
            os=os_name,
            arch=arch,
            download_url=asset.get("browser_download_url"),
            size_bytes=asset.get("size", 0),
            sha256_checksum="",  # Need a mechanism to extract checksums (e.g. from a shasums.txt asset)
            digital_signature=None
        )
        db.add(artifact)
        
    db.commit()
    return {"status": "success", "version": tag_name, "assets_imported": len(assets)}
