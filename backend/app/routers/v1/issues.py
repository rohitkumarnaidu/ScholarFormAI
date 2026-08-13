"""Issue reporting API routes."""

import logging

from fastapi import APIRouter, HTTPException

from app.core.exceptions import IssueReportError
from app.schemas.issue_models import (
    CommentRequest,
    CrashReportRequest,
    FeedbackRequest,
    IssueListResponse,
    IssueReportRequest,
    IssueReportResponse,
    IssueStatsResponse,
    IssueUpdateRequest,
    LabelCreateRequest,
    MilestoneCreateRequest,
    SettingsUpdateRequest,
    SLABreachResponse,
)
from app.services.issue_service import IssueReport, IssueService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/issues", tags=["issues"])

_issue_service = IssueService()


def _get_service() -> IssueService:
    return _issue_service


@router.post("", response_model=IssueReportResponse, summary="Submit issue report")
async def submit_issue(request: IssueReportRequest):
    service = _get_service()
    try:
        report = IssueReport(
            title=request.title,
            description=request.description,
            category=request.category.value,
            severity=request.severity.value,
            source=request.source.value,
            reporter_name=request.reporter_name,
            reporter_email=request.reporter_email,
            anonymous=request.anonymous,
            system_info=request.system_info,
            browser_info=request.browser_info,
            device_info=request.device_info,
            environment_info=request.environment_info,
            app_version=request.app_version,
            screenshots=request.screenshots,
            logs=request.logs,
            steps_to_reproduce=request.steps_to_reproduce,
            expected_behavior=request.expected_behavior,
            actual_behavior=request.actual_behavior,
            stack_trace=request.stack_trace,
            email_notifications=request.email_notifications,
            discord_notifications=request.discord_notifications,
            slack_notifications=request.slack_notifications,
        )
        result = service.submit_issue(report)
        logger.info("Issue submitted: %s", result.get("tracking_number"))
        return IssueReportResponse(**result)
    except Exception as e:
        logger.error("Issue submission failed: %s", e)
        raise IssueReportError(message=str(e))


@router.get("", response_model=IssueListResponse, summary="List issues")
async def list_issues(
    status: str | None = None,
    category: str | None = None,
    severity: str | None = None,
    assigned_to: str | None = None,
    label: str | None = None,
    milestone: str | None = None,
    search: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    limit: int = 50,
    offset: int = 0,
):
    service = _get_service()
    try:
        issues = service.list_issues(
            status=status,
            category=category,
            severity=severity,
            assigned_to=assigned_to,
            label=label,
            milestone=milestone,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            offset=offset,
        )
        return IssueListResponse(issues=issues, total=len(issues), offset=offset, limit=limit)
    except Exception as e:
        logger.error("Failed to list issues: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to list issues: {e}")


@router.get("/stats", response_model=IssueStatsResponse, summary="Get issue statistics")
async def get_issue_stats():
    service = _get_service()
    try:
        stats = service.get_stats()
        return IssueStatsResponse(**stats)
    except Exception as e:
        logger.error("Failed to get stats: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {e}")


@router.get("/sla", response_model=list[SLABreachResponse], summary="Check SLA breaches")
async def check_sla_breaches():
    service = _get_service()
    try:
        breaches = service.check_sla()
        return [SLABreachResponse(**b) for b in breaches]
    except Exception as e:
        logger.error("Failed to check SLA: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to check SLA: {e}")


@router.get("/{issue_id}", response_model=IssueReportResponse, summary="Get issue detail")
async def get_issue(issue_id: str):
    service = _get_service()
    issue = service.get_issue(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail=f"Issue '{issue_id}' not found")
    return IssueReportResponse(**issue)


@router.patch("/{issue_id}", response_model=IssueReportResponse, summary="Update issue")
async def update_issue(issue_id: str, request: IssueUpdateRequest):
    service = _get_service()
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if "_actor" in updates:
        del updates["_actor"]
    result = service.update_issue(issue_id, updates)
    if not result:
        raise HTTPException(status_code=404, detail=f"Issue '{issue_id}' not found")
    return IssueReportResponse(**result)


@router.delete("/{issue_id}", summary="Delete issue")
async def delete_issue(issue_id: str):
    service = _get_service()
    if not service.delete_issue(issue_id):
        raise HTTPException(status_code=404, detail=f"Issue '{issue_id}' not found")
    return {"message": f"Issue '{issue_id}' deleted", "id": issue_id}


@router.post("/{issue_id}/comments", response_model=IssueReportResponse, summary="Add comment")
async def add_comment(issue_id: str, request: CommentRequest):
    service = _get_service()
    comment = {"body": request.body, "author": request.author or "Anonymous"}
    result = service.add_comment(issue_id, comment)
    if not result:
        raise HTTPException(status_code=404, detail=f"Issue '{issue_id}' not found")
    return IssueReportResponse(**result)


@router.get("/{issue_id}/comments", summary="Get comments")
async def get_comments(issue_id: str):
    service = _get_service()
    issue = service.get_issue(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail=f"Issue '{issue_id}' not found")
    return service.get_comments(issue_id)


@router.get("/{issue_id}/timeline", summary="Get timeline")
async def get_timeline(issue_id: str):
    service = _get_service()
    issue = service.get_issue(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail=f"Issue '{issue_id}' not found")
    return service.get_timeline(issue_id)


@router.get("/{issue_id}/tracking", summary="Get tracking number")
async def get_tracking_number(issue_id: str):
    service = _get_service()
    tn = service.get_tracking_number(issue_id)
    if not tn:
        raise HTTPException(status_code=404, detail=f"Issue '{issue_id}' not found")
    return {"tracking_number": tn, "issue_id": issue_id}


@router.post("/crash", response_model=IssueReportResponse, summary="Submit crash report")
async def submit_crash_report(request: CrashReportRequest):
    service = _get_service()
    try:
        crash_data = {
            "error_message": request.error_message,
            "stack_trace": request.stack_trace,
            "system_info": request.system_info,
            "app_version": request.app_version,
            "logs": request.logs,
        }
        result = service.submit_crash_report(crash_data)
        logger.info("Crash report submitted: %s", result.get("tracking_number"))
        return IssueReportResponse(**result.get("issue", result))
    except Exception as e:
        logger.error("Crash report submission failed: %s", e)
        raise IssueReportError(message=str(e))


@router.post("/feedback", response_model=IssueReportResponse, summary="Submit feedback")
async def submit_feedback(request: FeedbackRequest):
    service = _get_service()
    try:
        feedback_data = {
            "title": request.title,
            "message": request.message,
            "category": request.category,
            "rating": request.rating,
            "reporter_name": request.reporter_name,
            "reporter_email": request.reporter_email,
            "create_issue": request.create_issue,
        }
        result = service.submit_feedback(feedback_data)
        logger.info("Feedback submitted: %s", result.get("title"))
        return IssueReportResponse(**result)
    except Exception as e:
        logger.error("Feedback submission failed: %s", e)
        raise IssueReportError(message=str(e))


@router.get("/labels", summary="List labels")
async def list_labels():
    service = _get_service()
    return service.list_labels()


@router.post("/labels", summary="Create label")
async def create_label(request: LabelCreateRequest):
    service = _get_service()
    try:
        label = service.create_label(name=request.name, color=request.color, description=request.description)
        logger.info("Label created: %s", request.name)
        return label
    except Exception as e:
        logger.error("Label creation failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Label creation failed: {e}")


@router.delete("/labels/{key}", summary="Delete label")
async def delete_label(key: str):
    service = _get_service()
    if not service.delete_label(key):
        raise HTTPException(status_code=404, detail=f"Label '{key}' not found or is a default label")
    return {"message": f"Label '{key}' deleted", "key": key}


@router.get("/milestones", summary="List milestones")
async def list_milestones():
    service = _get_service()
    return service.list_milestones()


@router.post("/milestones", summary="Create milestone")
async def create_milestone(request: MilestoneCreateRequest):
    service = _get_service()
    try:
        milestone = service.create_milestone(
            title=request.title, description=request.description, due_date=request.due_date
        )
        logger.info("Milestone created: %s", request.title)
        return milestone
    except Exception as e:
        logger.error("Milestone creation failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Milestone creation failed: {e}")


@router.get("/settings", summary="Get settings")
async def get_settings():
    service = _get_service()
    return service.get_settings()


@router.put("/settings", summary="Update settings")
async def update_settings(request: SettingsUpdateRequest):
    service = _get_service()
    try:
        updated = service.update_settings(request.settings)
        logger.info("Settings updated")
        return updated
    except Exception as e:
        logger.error("Settings update failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Settings update failed: {e}")
