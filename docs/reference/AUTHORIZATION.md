# Authorization

## Current Status

AMF v1.0 has **no authorization system**. All API endpoints are publicly accessible (rate-limited only).

## Planned Authorization (v2.0+)

### Role-Based Access Control (RBAC)

| Role | Permissions |
| ------ | ------------- |
| `admin` | Full access, user management, configuration |
| `editor` | Format, validate, preview, create styles |
| `user` | Format, validate, preview |
| `api` | API-only access with rate limit overrides |

### Implementation

```python
# Middleware (planned)
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def get_current_user(token: str = Depends(security)):
    # Verify token, return user with roles
    pass

async def require_role(role: str):
    async def dependency(user = Depends(get_current_user)):
        if role not in user.roles:
            raise HTTPException(status_code=403)
    return dependency

# Usage
@router.post("/format")
async def format(
    request: FormatRequest,
    user = Depends(require_role("user")),
):
    ...
```

### API Key Scopes

```
# Scope-based API keys
api_key = "sk_...{scopes: ['format', 'validate']}"
```

## OAuth 2.0 (Planned)

Supported providers:

- Google Scholar
- ORCID
- GitHub
- Institutional SSO (SAML)

## Resource Ownership

- Users own their manuscripts and projects
- Shared projects via invitations
- Public/private visibility settings
