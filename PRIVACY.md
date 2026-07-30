# Privacy Policy

## Data Processing

### Manuscript Content

- **Local Mode**: All manuscript content stays on your machine. No data is transmitted externally.
- **API Mode**: Manuscript content is sent to the AMF API server for processing. Content is:
  - Processed in memory only
  - Not permanently stored (except temporary formatted files)
  - Not used for model training
  - Not shared with third parties

### Logging

- Request metadata may be logged (timestamps, endpoint, response status)
- Manuscript content is NOT included in logs
- IP addresses may be logged for rate limiting

## Data Storage

### Temporary Files

- Formatted DOCX files are stored temporarily for download
- Files are automatically cleaned up after a configurable TTL
- Default TTL: 1 hour

### Configuration

- Local configuration files are stored in `~/.config/amf/` or `%APPDATA%/amf/`
- Configuration contains only formatting preferences, not manuscript content

## Third-Party Services

AMF does not integrate with any third-party analytics, advertising, or tracking services.

## Self-Hosting

For maximum privacy, self-host AMF using Docker Compose or manual deployment. See [DEPLOYMENT.md](DEPLOYMENT.md).

## Security

See [SECURITY.md](SECURITY.md) for security practices and vulnerability reporting.
