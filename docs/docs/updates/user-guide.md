# Update Management — User Guide

## Overview

AMF's update system keeps your installation up to date with the latest features, bug fixes, and security patches. You can check for updates, download and install them, or roll back if needed — all from the CLI, web UI, or API.

## Checking for Updates

### Using the CLI

```bash
# Quick check
amf update check

# Check a specific channel
amf update check --channel beta

# Check for nightly builds
amf update check --channel nightly
```

### Using the Web UI

1. Navigate to **Settings → Check Updates**
2. Click **Check Now**
3. If an update is available, you'll see version details and a changelog

### Automatic Updates

By default, AMF checks for updates every 24 hours. You can configure this:

```bash
# Check every 12 hours
amf update settings --check-frequency-hours 12

# Disable auto-check
amf update settings --no-auto-check
```

## Installing Updates

### Via CLI

```bash
# Check + download + install in one flow
amf update check
amf update download
amf update install

# Or specify a version directly
amf update download --version 1.2.0
amf update install
```

### Via Web UI

1. Go to **Settings → Check Updates**
2. Click **Check Now**
3. If available, click **Download & Install**
4. Restart the application when prompted

### Auto-Install

Enable auto-install to skip manual steps:

```bash
amf update settings --auto-download --auto-install
```

## Release Channels

AMF offers four release channels:

| Channel | Stability | Use Case |
|---------|-----------|----------|
| **Stable** | Production-ready | Recommended for all users |
| **Beta** | Mostly stable | Try new features before stable release |
| **Nightly** | May be unstable | Latest development builds |
| **Pre-release** | Release candidates | Testing before stable launch |

Change channels:

```bash
amf update settings --channel beta
amf update channels   # List available channels
```

## Rollback

If an update causes issues, roll back to the previous version:

```bash
# Rollback to previous version
amf update rollback

# Rollback to a specific version
amf update rollback --version 1.0.0
```

Rollback restores files from automatic backups created during installation. Each update creates a backup at `~/.amf/updates/backups/v{version}/`.

## Update History

View your update history:

```bash
# Show last 20 entries
amf update history

# Show last 50 entries
amf update history --limit 50
```

The history shows:
- Version number
- Channel
- Installation date
- Success/failure status
- Rollback information
- Error messages (if any)

## Release Notes

View release notes for any version:

```bash
# Show release notes for a specific version
amf update release-notes 1.2.0
```

## Update Settings

### CLI Settings

```bash
# View all settings
amf update settings

# Change settings
amf update settings --channel beta
amf update settings --auto-download
amf update settings --no-auto-check
amf update settings --check-frequency-hours 48
```

### Web UI Settings

Navigate to **Settings → Update Settings** to configure:

- **Release Channel**: Which channel to receive updates from
- **Auto Check**: Automatically check for updates
- **Auto Download**: Automatically download updates
- **Auto Install**: Automatically install downloaded updates
- **Auto Restart**: Automatically restart after update
- **Check Frequency**: How often to check (1–720 hours)
- **Notifications**: Toggle optional/security update alerts
- **Proxy**: HTTP proxy for downloads
- **Verify Checksum**: Verify file integrity before installing

### Security Updates

Security updates are prominently marked with a red banner in the web UI and a `[SECURITY]` tag in the CLI. They are always recommended for immediate installation.

## Troubleshooting

### Update Check Fails

```bash
# Check GitHub API access
curl https://api.github.com/repos/amf/automated-manuscript-formatter/releases

# Set a GitHub token for higher rate limits
amf update settings --github-token YOUR_TOKEN

# Configure proxy if behind firewall
amf update settings --proxy-url http://proxy:8080
```

### Download Fails

- Check your internet connection
- Verify the release exists on GitHub
- Try again — downloads automatically retry on failure

### Install Fails

- Ensure write permissions to the installation directory
- Check disk space
- Try rolling back and reinstalling

### Rollback Fails

- Verify backup exists at `~/.amf/updates/backups/`
- Manually restore from backup if needed
