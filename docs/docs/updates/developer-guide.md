# Update Management — Developer Guide

## Architecture Overview

The AMF update management system follows a **service-oriented architecture** with three layers:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Frontend     │     │   CLI           │     │   GitHub API    │
│  (Next.js UI)   │     │  (Click CLI)    │     │  (Releases)     │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                      │                       │
         └──────────┬───────────┴───────────────────────┘
                    │
         ┌──────────▼───────────┐
         │   Backend API        │
         │  (FastAPI /update/*) │
         └──────────┬───────────┘
                    │
         ┌──────────▼───────────┐
         │   UpdateService      │
         │  (business logic)    │
         └──────────────────────┘
```

### Key Components

| Component | File | Purpose |
|-----------|------|---------|
| `UpdateService` | `backend/app/services/update_service.py` | Core logic: check, download, install, rollback, settings, history |
| `update_routes.py` | `backend/app/api/update_routes.py` | REST API endpoints for update management |
| `update_models.py` | `backend/app/api/update_models.py` | Pydantic request/response models |
| `update.py` (CLI) | `cli/amf/commands/update.py` | CLI commands for update management |
| `update-api.ts` | `frontend/src/lib/update-api.ts` | Frontend API client for update operations |
| `UpdateBanner.tsx` | `frontend/src/components/UpdateBanner.tsx` | Toast notification for available updates |
| `DashboardWidget.tsx` | `frontend/src/components/DashboardWidget.tsx` | Dashboard update status widget |
| `settings/page.tsx` | `frontend/src/app/settings/page.tsx` | Full settings page with update management |

## Data Flow

### Update Check Flow

```
User/System triggers check
        │
        ▼
  UpdateService.check_for_updates()
        │
        ├─► Fetch releases from GitHub API
        │   GET https://api.github.com/repos/{owner}/{repo}/releases
        │
        ├─► Parse GitHub releases into UpdateInfo objects
        │   - Filter by channel (stable/beta/nightly/pre-release)
        │   - Parse semver from tag names
        │   - Extract changelog from release body
        │
        ├─► Compare versions with semver
        │   - Sort candidates by version descending
        │   - Compare latest vs current_version
        │
        └─► Return result
            - "up-to-date": current is latest
            - "update-available": newer version exists
            - "error": GitHub API unreachable
```

### Download & Install Flow

```
User triggers download
        │
        ▼
  UpdateService.download_update()
        │
        ├─► Stream download from GitHub release asset
        │   - Progress callback for UI updates
        │   - Retry on network failure (2 retries)
        │   - SHA256 checksum verification
        │
        ├─► Verify checksum
        │   - Compare expected vs actual SHA256
        │   - Log mismatch (don't block install by default)
        │
        ├─► User triggers install
        │
        ▼
  UpdateService.install_update()
        │
        ├─► Backup current application files
        │   - Copy to ~/.amf/updates/backups/v{version}/
        │
        ├─► Record history entry
        │   - Version, channel, timestamp, checksum, success flag
        │
        └─► Update current_version
```

### Rollback Flow

```
User triggers rollback
        │
        ▼
  UpdateService.rollback()
        │
        ├─► Find last successful install from history
        │
        ├─► Restore files from backup directory
        │   - ~/.amf/updates/backups/v{previous_version}/
        │
        ├─► Mark current version as rolled back in history
        │
        └─► Add rollback history entry
```

## GitHub Releases Integration

The `UpdateService` interacts with the [GitHub Releases API](https://docs.github.com/en/rest/releases/releases) to fetch available updates.

### API Format

```python
GET https://api.github.com/repos/{owner}/{repo}/releases?per_page=20
Headers:
  Accept: application/vnd.github+json
  Authorization: Bearer {token}  # optional, for higher rate limits
```

### Release Parsing Rules

| Tag Pattern | Channel | Example |
|-------------|---------|---------|
| `v1.2.3` | `stable` | `v1.0.0` |
| `v1.2.3-beta.N` | `beta` | `v1.1.0-beta.1` |
| `v1.2.3-nightly.YYYYMMDD` | `nightly` | `v1.2.0-nightly.20260725` |
| Any prerelease tag | `pre-release` | `v1.0.0-rc.1` |

### Rate Limits

- **Unauthenticated**: 60 requests/hour
- **Authenticated** (with `github_token`): 5,000 requests/hour
- Set token in update settings: `amf update settings --github-token YOUR_TOKEN`

## Settings

Settings are stored at `~/.amf/update-settings.json` (cross-platform).

### Default Settings

```json
{
  "channel": "stable",
  "auto_check": true,
  "auto_download": false,
  "auto_install": false,
  "auto_restart": true,
  "check_frequency_hours": 24,
  "notify_on_optional": true,
  "notify_on_security": true,
  "check_at_startup": true,
  "background_download": false,
  "proxy_url": null,
  "github_token": null,
  "verify_signature": true,
  "verify_checksum": true
}
```

## History

Update history is stored at `~/.amf/update-history.json` as an array of entries:

```json
[
  {
    "version": "1.0.0",
    "channel": "stable",
    "installed_at": "2026-07-25T10:00:00+00:00",
    "checksum": "abc123...",
    "checksum_type": "sha256",
    "success": true,
    "error_message": null,
    "rolled_back": false,
    "rollback_version": null
  }
]
```

## API Endpoints

### Update Routes

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/updates/check` | Check for updates |
| `POST` | `/api/v1/updates/check` | Check for updates (with body) |
| `GET` | `/api/v1/updates/version` | Current version info |
| `POST` | `/api/v1/updates/download` | Download an update |
| `POST` | `/api/v1/updates/install` | Install downloaded update |
| `POST` | `/api/v1/updates/rollback` | Rollback to previous version |
| `GET` | `/api/v1/updates/history` | Get update history |
| `GET` | `/api/v1/updates/release-notes` | Get release notes |
| `GET` | `/api/v1/updates/channels` | List release channels |
| `GET` | `/api/v1/updates/settings` | Get update settings |
| `PUT` | `/api/v1/updates/settings` | Update settings |

## Extending the Update System

### Adding a New Release Channel

1. Add the channel to `ReleaseChannel` enum in `update_service.py`
2. Add channel filtering logic in `_parse_github_release()`
3. Add channel metadata in `get_channels()`
4. Add channel to settings validation in `UpdateSettings` model

### Adding Custom Update Sources

The `UpdateService` currently supports GitHub Releases. To add another source (e.g., S3, self-hosted):

1. Create a new fetch method (e.g., `_fetch_s3_releases()`)
2. Add source selection to settings
3. Modify `check_for_updates()` to use the configured source
4. Implement the `UpdateInfo` parsing for the new source format

## Security

### Checksum Verification

SHA256 checksums are verified for all downloaded packages when `verify_checksum` is enabled:

```python
def _verify_checksum(self, file_path: Path, expected: str, algo: str = "sha256") -> bool:
    h = hashlib.new(algo)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest() == expected.lower()
```

### Digital Signature Verification

GPG signature verification is supported when `verify_signature` is enabled and a signature URL is provided in the release asset.

## Testing

Run the update-specific tests:

```bash
# Backend tests
pytest backend/tests/ -k "update"

# CLI tests
cd cli && pytest tests/test_update.py -v

# Frontend (build check)
cd frontend && npm run build
```
