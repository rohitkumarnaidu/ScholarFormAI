# Issue Reporting — Developer Guide

## Architecture Overview

The issue reporting ecosystem spans four layers:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Entry Points                                 │
│  Web UI  │  CLI  │  Error Dialog  │  Crash Screen  │  Feedback Wgt │
└────┬──────┴──┬───┴──────┬─────────┴────────┬───────┴───────────────┘
     │         │          │                  │
     ▼         ▼          ▼                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       Backend API (/api/v1/issues/*)                 │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│                          IssueService                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────────┐  │
│  │   CRUD   │  │  GitHub  │  │    AI    │  │  Notifications     │  │
│  │  Issues  │  │   Sync   │  │  Categor │  │ Discord/Slack/Web  │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│                      File-Based Storage                              │
│            ~/.amf/issues/{issues,feedback,crash-reports}.json        │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Components

| Component | File | Purpose |
|-----------|------|---------|
| `IssueService` | `backend/app/services/issue_service.py` | Core business logic — CRUD, duplicate/spam detection, AI, GitHub sync, notifications |
| `IssueReport` | `backend/app/services/issue_service.py` | Data class for a single issue report with all fields |
| `issue_routes.py` | `backend/app/api/issue_routes.py` | 19 REST API endpoints |
| `issue_models.py` | `backend/app/api/issue_models.py` | Pydantic request/response models |
| `issues.py` (CLI) | `cli/amf/commands/issues.py` | 10 Click subcommands |
| `issue-api.ts` | `frontend/src/lib/issue-api.ts` | TypeScript API client (22 functions) |
| `issues/page.tsx` | `frontend/src/app/issues/page.tsx` | Issue dashboard page |
| `issues/admin/page.tsx` | `frontend/src/app/issues/admin/page.tsx` | Admin dashboard page |
| `FeedbackWidget.tsx` | `frontend/src/components/FeedbackWidget.tsx` | Floating feedback button |
| `CrashScreen.tsx` | `frontend/src/components/CrashScreen.tsx` | Full-screen error boundary |
| `ErrorDialog.tsx` | `frontend/src/components/ErrorDialog.tsx` | Reusable error dialog |

## Data Flow

### Issue Submission

```
User fills form → IssueService.submit_issue()
                    │
                    ├─► Spam detection
                    │   (rate limit: N reports in M minutes)
                    │
                    ├─► Duplicate detection
                    │   (Jaccard similarity on title+description)
                    │
                    ├─► AI categorization (if enabled)
                    │   - Keyword-based category matching
                    │   - AI summarization (stub for OpenAI/etc.)
                    │   - AI suggested fix (for bug reports)
                    │
                    ├─► Generate tracking number
                    │   (AMF-YYMMDDHHMMSS-XXXX)
                    │
                    ├─► Persist to ~/.amf/issues/issues.json
                    │
                    ├─► GitHub sync (if enabled)
                    │   POST /repos/{owner}/{repo}/issues
                    │
                    └─► Dispatch notifications
                        - Discord webhook (embed)
                        - Slack webhook (blocks)
                        - Generic webhooks
```

### Duplicate Detection

Uses Jaccard similarity on word sets:

```python
def _text_similarity(self, a: str, b: str) -> float:
    words_a = set(re.findall(r"\w+", a.lower()))
    words_b = set(re.findall(r"\w+", b.lower()))
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union) if union else 0.0
```

Threshold is configurable via settings (`duplicate_similarity_threshold`, default 0.8).

## API Endpoints

### Issue Routes (prefix: `/api/v1/issues`)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/issues` | Submit new issue |
| `GET` | `/issues` | List issues (with filters) |
| `GET` | `/issues/stats` | Issue statistics |
| `GET` | `/issues/sla` | SLA breach checks |
| `GET` | `/issues/{issue_id}` | Issue detail |
| `PATCH` | `/issues/{issue_id}` | Update issue |
| `DELETE` | `/issues/{issue_id}` | Delete issue |
| `POST` | `/issues/{issue_id}/comments` | Add comment |
| `GET` | `/issues/{issue_id}/comments` | Get comments |
| `GET` | `/issues/{issue_id}/timeline` | Get timeline |
| `GET` | `/issues/{issue_id}/tracking` | Get tracking number |
| `POST` | `/issues/crash` | Submit crash report |
| `POST` | `/issues/feedback` | Submit feedback |
| `GET` | `/issues/labels` | List labels |
| `POST` | `/issues/labels` | Create label |
| `DELETE` | `/issues/labels/{key}` | Delete label |
| `GET` | `/issues/milestones` | List milestones |
| `POST` | `/issues/milestones` | Create milestone |
| `GET` | `/issues/settings` | Get settings |
| `PUT` | `/issues/settings` | Update settings |

## Storage Schema

File-based JSON at `~/.amf/issues/`:

### issues.json
```json
[{
  "id": "uuid",
  "title": "string",
  "description": "string",
  "category": "bug|feature-request|...",
  "severity": "critical|high|medium|low|suggestion",
  "status": "new|triaged|in-progress|resolved|closed|...",
  "source": "cli|web-ui|error-dialog|...",
  "tracking_number": "AMF-260725-0001",
  "labels": ["bug"],
  "assigned_to": "user",
  "milestone": "v1.1.0",
  "priority": 2,
  "system_info": { "os": "Windows", ... },
  "browser_info": { "userAgent": "...", ... },
  "app_version": "1.0.0",
  "comments": [{"id": "uuid", "body": "...", "author": "User", "timestamp": "..."}],
  "timeline": [{"action": "created", "timestamp": "...", "actor": "User"}],
  "created_at": "ISO8601",
  "updated_at": "ISO8601",
  "github_issue_url": "https://github.com/...",
  "duplicate_of": "parent-id"
}]
```

## Extending

### Adding a New Issue Category

1. Add to `IssueCategory` enum in `issue_service.py`
2. Add to Pydantic `IssueCategoryEnum` in `issue_models.py`
3. Add to CLI `type=click.Choice([...])` in `main.py`
4. Add category icon/color in frontend

### Integrating AI

Configure the AI provider in settings:
```json
{ "ai_enabled": true, "ai_provider": "openai", "ai_api_key": "sk-...", "ai_model": "gpt-4" }
```

Override `_ai_categorize`, `_ai_summarize`, `_ai_suggest_fix` methods in `IssueService` for custom AI logic.

### Adding a Notification Channel

1. Add webhook URL to settings (e.g., `msteams_webhook_url`)
2. Add dispatch logic in `_dispatch_notifications()`
3. Add formatter method (e.g., `_build_msteams_card()`)
