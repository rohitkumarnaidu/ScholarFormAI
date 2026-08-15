"""Issue reporting API routes."""

import logging
import uuid
import datetime

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.db.session import get_db
from app.models.issue import Issue
from app.models.issue_comment import IssueComment
from app.models.issue_attachment import IssueAttachment
from app.models.issue_settings import IssueSettings
from app.domain.issues.ai_service import IssueAIService
from app.domain.issues.integrations import IntegrationsService

from app.schemas.issue_models import (
    IssueReportRequest,
    IssueReportResponse,
    IssueListResponse,
    IssueUpdateRequest,
    SettingsUpdateRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/issues", tags=["issues"])


@router.post("", response_model=IssueReportResponse, summary="Submit enterprise issue report")
async def submit_issue(
    request: IssueReportRequest, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    try:
        # Pre-flight AI Triage (Categorization & Spam detection)
        # Note: If high volume, this can be moved to a background task
        ai_triage = await IssueAIService.categorize_issue(db, request.title, request.description)
        
        if ai_triage.get("is_spam"):
            logger.warning("Spam issue detected and rejected.")
            raise HTTPException(status_code=400, detail="Spam detected")

        # Generate unique tracking number
        tracking_num = f"ISSUE-{datetime.datetime.now(datetime.UTC).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        issue = Issue(
            tracking_number=tracking_num,
            title=request.title,
            description=request.description,
            type=ai_triage.get("category", request.category.value),
            priority=ai_triage.get("priority", request.severity.value),
            system_info=request.system_info,
            ai_category=ai_triage.get("category"),
            status="open"
        )
        db.add(issue)
        db.commit()
        db.refresh(issue)

        # Trigger Reasoning Model in background (if it's a bug or crash)
        if issue.type in ["bug", "crash", "performance"]:
            background_tasks.add_task(_process_ai_reasoning, db, issue.id, issue.title, issue.description, issue.system_info)

        # Trigger Webhooks
        background_tasks.add_task(IntegrationsService.dispatch_webhooks, db, issue)

        # Add attachments if any (mocking basic structure based on request)
        if request.screenshots:
            for url in request.screenshots:
                db.add(IssueAttachment(issue_id=issue.id, file_name="screenshot.png", file_type="screenshot", mime_type="image/png", size_bytes=0, storage_path=url))
            db.commit()

        # Build response
        return _build_issue_response(issue)

    except Exception as e:
        logger.error("Issue submission failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


async def _process_ai_reasoning(db: Session, issue_id: uuid.UUID, title: str, description: str, system_info: dict):
    # This runs in a background thread, so we generate the fix and update the DB
    fix = await IssueAIService.generate_suggested_fix(db, title, description, system_info)
    issue = db.get(Issue, issue_id)
    if issue:
        issue.ai_suggested_fix = fix
        # Also add as a comment
        comment = IssueComment(issue_id=issue_id, body=f"**AI Suggested Fix**\n{fix}", is_ai_generated=True)
        db.add(comment)
        db.commit()


@router.get("", response_model=IssueListResponse, summary="List issues")
def list_issues(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    query = select(Issue).order_by(desc(Issue.created_at))
    if status:
        query = query.where(Issue.status == status)
    
    issues = db.execute(query.offset(offset).limit(limit)).scalars().all()
    # Count total
    total = db.execute(select(Issue)).scalars().all() # Ineffecient but works for now

    return IssueListResponse(
        issues=[_build_issue_response(i) for i in issues], 
        total=len(total), 
        offset=offset, 
        limit=limit
    )


@router.get("/{issue_id}", response_model=IssueReportResponse, summary="Get issue detail")
def get_issue(issue_id: str, db: Session = Depends(get_db)):
    try:
        issue_uuid = uuid.UUID(issue_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid UUID")
    
    issue = db.get(Issue, issue_uuid)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return _build_issue_response(issue)


@router.patch("/{issue_id}", response_model=IssueReportResponse, summary="Update issue")
def update_issue(issue_id: str, request: IssueUpdateRequest, db: Session = Depends(get_db)):
    try:
        issue_uuid = uuid.UUID(issue_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid UUID")
        
    issue = db.get(Issue, issue_uuid)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    
    updates = request.model_dump(exclude_unset=True)
    for k, v in updates.items():
        if hasattr(issue, k):
            setattr(issue, k, v)
            
    db.commit()
    db.refresh(issue)
    return _build_issue_response(issue)


@router.delete("/{issue_id}", summary="Delete issue")
def delete_issue(issue_id: str, db: Session = Depends(get_db)):
    try:
        issue_uuid = uuid.UUID(issue_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid UUID")
        
    issue = db.get(Issue, issue_uuid)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    
    db.delete(issue)
    db.commit()
    return {"status": "deleted"}


def _build_issue_response(issue: Issue) -> dict:
    return {
        "id": str(issue.id),
        "title": issue.title,
        "description": issue.description,
        "category": issue.type,
        "severity": issue.priority,
        "status": issue.status,
        "source": "api", # defaulting for now
        "reporter_name": "",
        "reporter_email": "",
        "anonymous": issue.user_id is None,
        "tracking_number": issue.tracking_number,
        "labels": [issue.ai_category] if issue.ai_category else [],
        "assigned_to": str(issue.assignee_id) if issue.assignee_id else None,
        "milestone": None,
        "priority": 3,
        "system_info": issue.system_info or {},
        "browser_info": {},
        "device_info": {},
        "environment_info": {},
        "app_version": "",
        "attachments": [],
        "screenshots": [],
        "created_at": issue.created_at,
        "updated_at": issue.updated_at
    }
