# Memory Guide

## Overview

AMF can maintain context across sessions using memory features, enabling personalized formatting experiences.

## Session Memory

### Request Context

Each API request carries context via headers:

```bash
X-Request-ID: unique-request-id
X-Session-ID: user-session-id (optional)
```

### User Preferences (Planned)

User preferences stored in memory:

```json
{
  "preferred_style": "apa",
  "default_font": "Times New Roman",
  "default_font_size": 12,
  "default_line_spacing": 2.0,
  "recent_manuscripts": [],
  "custom_styles": []
}
```

## Cache Memory

### In-Memory Cache

- Style definitions (TTL: 24 hours)
- Recent formatting results (TTL: 1 hour)
- Validation rules (TTL: 24 hours)

### Redis Cache (Planned)

```python
# Cache format results
cache.set(f"format:{doc_hash}", result, ex=3600)

# Cache user preferences
cache.set(f"user:{user_id}:prefs", prefs_json, ex=86400)

# Cache style definitions
cache.set(f"style:{style_id}", style_json, ex=86400)
```

## File System Memory

- Temporary formatted documents (stored in `uploads/`)
- User configuration files (`~/.config/amf/`)
- Project configuration (per-project `amf.config.json`)

## Memory Management

### Cleanup

```bash
# Clear temporary formatted files
rm -rf ./uploads/*

# Clear cached styles
# (restart clears in-memory cache)
```

### Configuration

```bash
# Control temp file retention
AMF_TEMP_FILE_TTL=3600  # seconds (default: 1 hour)
AMF_MAX_CACHE_SIZE=100  # MB (default)
```

## Stateless Mode

By default, AMF is stateless — no session memory. Each request is independent. This simplifies deployment and scaling.
