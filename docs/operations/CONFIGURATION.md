# Configuration Management

ScholarForm AI uses a combination of environment variables, configuration files, and secret managers for deployment configuration.

## Environment Variables

The primary configuration mechanism is `.env` files. In production, these are injected securely via Kubernetes Secrets or Docker Compose environments.

### Backend (`backend/.env`)

| Variable | Description | Example |
|----------|-------------|---------|
| `ENVIRONMENT` | Deployment environment | `production`, `staging`, `development` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://user:pass@db:5432/scholarform` |
| `REDIS_URL` | Redis connection string | `redis://redis:6379/0` |
| `CELERY_BROKER_URL` | Message broker url | `redis://redis:6379/1` |
| `GROQ_API_KEY` | Key for Groq LLM | `gsk_...` |
| `NVIDIA_API_KEY` | Key for NVIDIA API | `nvapi-...` |
| `SECRET_KEY` | JWT signing key | `supersecret...` |

### Frontend (`frontend/.env.local`)

| Variable | Description | Example |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API base URL | `https://api.scholarform.ai` |
| `NEXT_PUBLIC_WS_URL` | Backend WebSocket URL | `wss://api.scholarform.ai` |

## Secret Management

Never commit API keys or `SECRET_KEY` to source control.
- **Local**: Use `.env` files (excluded via `.gitignore`).
- **CI/CD**: Use GitHub Actions Secrets.
- **Production**: Use AWS Secrets Manager, HashiCorp Vault, or Kubernetes Secrets.

## Feature Flags

We use Redis-backed feature flags to enable or disable beta features (like the Synthesis Agent) dynamically without redeploying.

## Cross-References
- [Deployment Guide](DEPLOYMENT.md)
- [Operations Overview](OPERATIONS.md)
