# Issue Reporting — Admin Guide

## Admin Dashboard

Access the admin dashboard at `/issues/admin` in the web UI.

### Tabs

#### Overview
- **Stats Cards**: Total, Open, Resolved, Critical issues
- **Issues by Category**: Horizontal bar chart showing distribution
- **Issues by Status**: Status distribution bars
- **SLA Breaches**: Table of issues exceeding response time targets

#### Labels
- View all labels with color swatches
- Create new labels (name, color, description)
- Delete custom labels (built-in labels cannot be deleted)

#### Milestones
- View all milestones
- Create new milestones (title, description, due date)

#### Settings
Configure all issue system settings (see below).

## Configuration

### Issue Settings

Access via API or the admin dashboard settings tab.

| Setting | Default | Description |
|---------|---------|-------------|
| `github_sync_enabled` | `false` | Auto-create GitHub issues on submission |
| `github_repo` | `amf/automated-manuscript-formatter` | GitHub repository for sync |
| `github_token` | `null` | GitHub API token (required for sync) |
| `auto_create_github_issues` | `true` | Create GitHub issue on every report |
| `slack_webhook_url` | `null` | Slack incoming webhook URL |
| `discord_webhook_url` | `null` | Discord webhook URL |
| `email_smtp_server` | `null` | SMTP server for email notifications |
| `email_smtp_port` | `587` | SMTP port |
| `email_from` | `issues@amf.dev` | From address for email notifications |
| `email_notify_reporters` | `true` | Send email to reporters on status change |
| `sla_critical_hours` | `4` | SLA target for critical issues (hours) |
| `sla_high_hours` | `24` | SLA target for high severity |
| `sla_medium_hours` | `72` | SLA target for medium severity |
| `sla_low_hours` | `168` | SLA target for low severity (7 days) |
| `spam_threshold` | `10` | Max reports per IP in spam window |
| `spam_window_minutes` | `60` | Spam detection time window |
| `duplicate_similarity_threshold` | `0.8` | Jaccard similarity threshold for dup detection |
| `ai_enabled` | `false` | Enable AI categorization/summarization |
| `ai_provider` | `openai` | AI provider (openai, anthropic, etc.) |
| `ai_api_key` | `null` | API key for AI provider |
| `ai_model` | `gpt-4` | AI model name |
| `webhook_urls` | `[]` | Generic webhook URLs for issue events |
| `max_attachments_per_issue` | `5` | Max file attachments per issue |
| `max_attachment_size_mb` | `25` | Max attachment size in MB |
| `allow_anonymous_reports` | `true` | Allow submissions without identity |
| `require_email_for_followup` | `false` | Require email for issue follow-up |
| `auto_assign_enabled` | `false` | Auto-assign issues to team members |
| `auto_assign_users` | `[]` | Users for auto-assignment (round-robin) |

### Updating Settings

```bash
# Via API
curl -X PUT http://localhost:8000/api/v1/issues/settings \
  -H "Content-Type: application/json" \
  -d '{"settings": {"slack_webhook_url": "https://hooks.slack.com/...", "sla_critical_hours": 2}}'
```

## SLA Management

SLA targets are configured per severity level:

| Severity | Default SLA | Breach Alert |
|----------|-------------|-------------|
| Critical | 4 hours | Immediate |
| High | 24 hours | Dashboard highlight |
| Medium | 72 hours | Dashboard note |
| Low | 168 hours (7 days) | Dashboard note |

Check SLA breaches:

```bash
curl http://localhost:8000/api/v1/issues/sla
```

## GitHub Integration

### Setup

1. Generate a GitHub personal access token with `public_repo` scope
2. Set the token and enable sync:
```bash
curl -X PUT http://localhost:8000/api/v1/issues/settings \
  -d '{"settings": {"github_sync_enabled": true, "github_token": "ghp_...", "github_repo": "your-org/your-repo"}}'
```

3. Issues submitted via any channel will auto-create GitHub issues

### What Gets Synced

- Issue title and description
- Labels (matched by name)
- Tracking number in the GitHub issue body
- System info formatted as JSON

## Notification Channels

### Discord

1. Create a Discord webhook in your server settings
2. Set the URL:
```json
{"settings": {"discord_webhook_url": "https://discord.com/api/webhooks/..."}}
```

Discord embeds include: title, description, status, severity, category, tracking number.

### Slack

1. Create a Slack webhook in your workspace
2. Set the URL:
```json
{"settings": {"slack_webhook_url": "https://hooks.slack.com/services/..."}}
```

Slack messages use Block Kit with header, fields, and GitHub link.

### Generic Webhooks

Add multiple webhook URLs:
```json
{"settings": {"webhook_urls": ["https://hooks.example.com/issue"]}}
```

Payload format:
```json
{
  "event": "new_issue|issue_updated|new_comment",
  "issue": { "...issue data..." },
  "comment": { "...comment data..." }
}
```

## Labels

### Built-in Labels

| Key | Name | Color | Description |
|-----|------|-------|-------------|
| `bug` | bug | `#d73a4a` | Something isn't working |
| `feature` | enhancement | `#a2eeef` | New feature or request |
| `feedback` | feedback | `#0e8a16` | General user feedback |
| `performance` | performance | `#d4c5f9` | Performance issue |
| `security` | security | `#b60205` | Security vulnerability |
| `crash` | crash | `#e99695` | Application crash |
| `duplicate` | duplicate | `#cfd3d7` | Duplicate issue |
| `wontfix` | wontfix | `#ffffff` | Will not be worked on |
| `high-priority` | high priority | `#b60205` | High priority |
| `needs-info` | needs info | `#fbca04` | Needs more information |

## Backup & Restore

### Automated Backup

Each issue submission is immediately persisted. The storage directory is `~/.amf/issues/`.

### Manual Backup

```bash
# CLI backup
amf issue backup

# Manual backup
cp -r ~/.amf/issues ~/.amf/issues_backup_$(date +%Y%m%d)

# Restore
cp -r ~/.amf/issues_backup_20260725/* ~/.amf/issues/
```

## Spam Protection

The system uses rate-limiting per source:
- **Threshold**: N reports per source in M minutes (configurable)
- **Action**: Issues exceeding the threshold are auto-closed as spam
- **Source tracking**: Each report is tagged with its source (CLI, web, API, etc.)
