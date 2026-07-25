# Issue Reporting — User Guide

## Overview

AMF's issue reporting system lets you submit bugs, feature requests, feedback, crash reports, and security issues from wherever you are — the web UI, CLI, error dialogs, crash screens, or the floating feedback widget.

## Reporting Issues

### From the Web UI

1. **Issue Dashboard**: Navigate to **Issues** in the navigation bar
2. Click **Report Issue** to open the form
3. Fill in the details:
   - **Title** — short description
   - **Category** — bug, feature request, feedback, etc.
   - **Severity** — how critical the issue is
   - **Description** — detailed explanation
   - **Steps to Reproduce** — how to reproduce (for bugs)
   - **Expected vs Actual Behavior**
   - **Reporter Info** — name/email (optional)
4. Click **Submit**

### From the CLI

```bash
# Report a bug
amf issue report -t "Button not working" -d "The submit button does nothing" -c bug -s high

# Report with all options
amf issue report -t "Slow formatting" -d "Formatting takes >30s" -c performance -s medium -n "Jane" -e "jane@test.com" --attach-logs

# Feature request
amf issue report -t "Add dark mode" -d "Would be nice to have dark mode" -c feature-request -s suggestion
```

### From Error Dialogs

When an error occurs, the error dialog shows:
- **Dismiss** — close the dialog
- **Copy Error** — copies the error details to clipboard
- **Report Issue** — opens a pre-filled issue form

### From Crash Screens

If the application crashes, the crash screen shows:
- Error message with collapsible stack trace
- **Report Crash** — submits system info, logs, and stack trace
- **Reload Page** — refresh the application
- **Go Home** — return to the landing page

### From the Feedback Widget

A floating feedback button (bottom-left) lets you submit quick feedback:
1. Click the feedback button
2. Rate your experience (1–5 stars)
3. Select a category
4. Write your message
5. Optionally include your name/email
6. Toggle anonymous mode
7. Submit

## Managing Issues

### Viewing Issues

```bash
# List all issues
amf issue list

# Filter by status
amf issue list --status new

# Filter by category
amf issue list --category bug

# Filter by severity
amf issue list --severity critical

# Search
amf issue search "crash"
amf issue search "dark mode"

# Limit results
amf issue list --limit 50
```

### Viewing Details

```bash
# Show issue by ID or tracking number
amf issue show AMF-260725-0001

# Shows: title, description, category, severity, status,
#        timeline, comments, stack trace, AI summary
```

### Adding Comments

```bash
amf issue comment AMF-260725-0001 -b "I found the root cause"
```

### Updating Issues (for triagers)

```bash
# Change status
amf issue update AMF-260725-0001 --status resolved

# Change severity
amf issue update AMF-260725-0001 --severity critical

# Assign to someone
amf issue update AMF-260725-0001 --assign dev-team

# Set milestone
amf issue update AMF-260725-0001 --milestone "v1.1.0"
```

## Tracking Numbers

Every issue gets a unique tracking number: `AMF-YYMMDDHHMMSS-XXXX`

You can use the tracking number anywhere the issue ID is required.

## Statistics

```bash
# View issue statistics
amf issue stats
# Shows: total, open, resolved, critical, SLA breaches, comments
```

## Labels

```bash
# View all labels
amf issue labels
```

## Backup

```bash
# Backup all issue data
amf issue backup
# Creates: ~/.amf/issues_backup_YYYYMMDD_HHMMSS/
```

## Privacy

- **Anonymous reports**: Toggle anonymous mode to submit without personal info
- **Data collected**: System info (OS, Python version) for crash reports
- **Logs**: Only attached if `--attach-logs` flag is used in CLI

## Release Channels for Issues

Issues can be associated with milestones (e.g., "v1.1.0", "v2.0.0", "Backlog") to track which release they are targeted for.
