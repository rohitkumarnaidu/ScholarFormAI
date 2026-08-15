# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import json
import logging
from typing import List
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.db.session import get_db
from app.utils.dependencies import get_current_user
from app.models.user import User
from app.models.notification import Notification
from app.models.notification_preference import NotificationPreference
from app.realtime.pubsub import RedisPubSub
from app.domain.notifications.service import NotificationService

logger = logging.getLogger(__name__)

router = APIRouter()
_pubsub = RedisPubSub()

@router.get("", response_model=List[dict])
def get_notifications(
    limit: int = 50,
    offset: int = 0,
    unread_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch user's notification history."""
    stmt = select(Notification).where(Notification.user_id == current_user.id)
    if unread_only:
        stmt = stmt.where(Notification.read_at == None)
    
    stmt = stmt.order_by(desc(Notification.created_at)).limit(limit).offset(offset)
    notifications = db.execute(stmt).scalars().all()
    
    return [
        {
            "id": str(n.id),
            "type": n.type,
            "title": n.title,
            "body": n.body,
            "metadata": n.metadata_json,
            "read_at": n.read_at,
            "created_at": n.created_at
        } for n in notifications
    ]

@router.patch("/{notification_id}/read")
def mark_as_read(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a specific notification as read."""
    notif = db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        )
    ).scalar_one_or_none()
    
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
        
    notif.read_at = datetime.utcnow()
    db.commit()
    return {"status": "ok"}

@router.get("/preferences")
def get_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get granular notification preferences."""
    prefs = db.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == current_user.id)
    ).scalar_one_or_none()
    
    if not prefs:
        prefs = NotificationPreference(user_id=current_user.id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
        
    return {
        "channel_preferences": prefs.channel_preferences,
        "dnd_enabled": prefs.dnd_enabled,
        "dnd_start_time": prefs.dnd_start_time,
        "dnd_end_time": prefs.dnd_end_time,
        "timezone": prefs.timezone,
        "digest_mode": prefs.digest_mode
    }

@router.put("/preferences")
def update_preferences(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update granular notification preferences."""
    prefs = db.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == current_user.id)
    ).scalar_one_or_none()
    
    if not prefs:
        prefs = NotificationPreference(user_id=current_user.id)
        db.add(prefs)
        
    if "channel_preferences" in data:
        prefs.channel_preferences = data["channel_preferences"]
    if "dnd_enabled" in data:
        prefs.dnd_enabled = data["dnd_enabled"]
    if "dnd_start_time" in data:
        prefs.dnd_start_time = data["dnd_start_time"]
    if "dnd_end_time" in data:
        prefs.dnd_end_time = data["dnd_end_time"]
    if "digest_mode" in data:
        prefs.digest_mode = data["digest_mode"]
        
    db.commit()
    return {"status": "ok"}

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(None)):
    """
    Dedicated WebSocket endpoint for real-time notifications.
    Uses token query param to identify the user since WS headers can be tricky in browsers.
    """
    await websocket.accept()
    
    # In a real app we'd decode the JWT token here
    # For now, we assume the token is the user_id (UUID)
    if not token:
        await websocket.close(code=1008, reason="Missing token")
        return
        
    channel = f"job:{token}" # Re-using existing Redis pubsub channel structure for now
    
    try:
        async for event in _pubsub.subscribe(channel):
            event_type = event.get("event_type") or "message"
            if event_type == "notification_received":
                await websocket.send_text(json.dumps(event))
    except WebSocketDisconnect:
        logger.info(f"User {token} disconnected from notification websocket")
