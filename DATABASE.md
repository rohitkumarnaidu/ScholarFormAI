# Database Guide

## Current Status

AMF v1.0 is **stateless** — no database is required. Manuscripts are processed in memory and formatted documents are stored temporarily as files on disk.

## Future Database Integration

### Planned Architecture (v2.0+)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  PostgreSQL │     │    Redis    │     |  Object Store│
│  (Primary)  │     │  (Cache)    │     |  (S3/Swift)  │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                    ┌──────▼──────┐
                    │  AMF API    │
                    └─────────────┘
```

### PostgreSQL Schema (Planned)

```sql
-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Projects
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    title VARCHAR(500) NOT NULL,
    style_id VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Manuscript Versions
CREATE TABLE versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    content JSONB NOT NULL,
    formatted_path TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- API Keys
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    key_hash VARCHAR(64) NOT NULL,
    name VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);
```

### Redis Caching (Planned)

```python
# Cache formatted documents
cache.set(f"format:{hash}", docx_bytes, ex=3600)

# Cache style definitions
cache.set(f"style:{style_id}", style_json, ex=86400)

# Rate limiting
cache.incr(f"ratelimit:{ip}:{endpoint}")
```

## Migration Path

v1.0 → v2.0 migration:

1. Set up PostgreSQL
2. Set up Redis
3. Run migrations
4. Enable features incrementally
5. Keep backward compatibility with stateless mode

## Connection Configuration

```bash
# PostgreSQL
AMF_DATABASE_URL=postgresql://user:pass@localhost:5432/amf

# Redis
AMF_REDIS_URL=redis://localhost:6379/0
```
