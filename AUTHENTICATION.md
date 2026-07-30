# Authentication

## Overview

AMF supports optional API key authentication. By default, the API is open (no authentication required).

## API Key Authentication

### Configuration

Set the API key on the backend:

```bash
AMF_SECRET_KEY=your-secret-key-here
```

### Usage

```bash
# Using API key in requests
curl -H "Authorization: Bearer your-secret-key-here" http://localhost:8000/api/v1/styles
```

```python
from amf_sdk import AMFClient

client = AMFClient(api_key="your-secret-key-here")
```

### Key Management

- Generate strong, random API keys
- Rotate keys regularly
- Use different keys for different environments

## Future Authentication Methods

### JWT Tokens (Planned)

- Token-based authentication via login endpoint
- Configurable token expiry
- Refresh token support

### OAuth 2.0 (Planned)

- Support for Google, ORCID, GitHub OAuth
- SSO for enterprise deployments
- Scoped access tokens

### API Key Management UI (Planned)

- Create and revoke keys via web interface
- Key usage monitoring
- Per-key rate limits

## Security Best Practices

1. Enable authentication in production
2. Use environment variables for secrets
3. Rotate keys at least every 90 days
4. Use unique keys per deployment
5. Monitor for unauthorized access attempts
