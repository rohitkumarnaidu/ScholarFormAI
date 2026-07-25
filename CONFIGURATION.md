# Configuration

## Environment Variables

Configuration is managed via environment variables prefixed with `AMF_`:

| Variable | Default | Description |
|----------|---------|-------------|
| `AMF_ENVIRONMENT` | `development` | Runtime environment |
| `AMF_DEBUG` | `true` | Enable debug mode |
| `AMF_LOG_LEVEL` | `info` | Logging level |
| `AMF_MAX_UPLOAD_SIZE` | `10485760` | Max upload size (bytes) |
| `AMF_DEFAULT_STYLE` | `apa` | Default citation style |
| `AMF_API_PREFIX` | `/api/v1` | API path prefix |
| `AMF_API_HOST` | `0.0.0.0` | API bind address |
| `AMF_API_PORT` | `8000` | API port |
| `AMF_UPLOAD_DIR` | `./uploads` | Upload directory |
| `AMF_ALLOWED_ORIGINS` | `*` | CORS allowed origins |
| `AMF_SECRET_KEY` | — | API secret key |
| `AMF_DATABASE_URL` | — | Database connection string |
| `AMF_REDIS_URL` | — | Redis connection string |

## .env File

Create a `.env` file in the `backend/` directory:

```env
AMF_ENVIRONMENT=production
AMF_DEBUG=false
AMF_LOG_LEVEL=warning
AMF_MAX_UPLOAD_SIZE=20971520
AMF_DEFAULT_STYLE=apa
AMF_ALLOWED_ORIGINS=https://amf.example.com
AMF_SECRET_KEY=your-secret-key-here
```

## CLI Configuration

Global config file:
- Linux/macOS: `~/.config/amf/config.json`
- Windows: `%APPDATA%/amf/config.json`

Project-level config: `amf.config.json` in project root.

```json
{
  "style": "apa",
  "api_endpoint": "http://localhost:8000",
  "output_dir": ".",
  "page_size": "A4",
  "font_family": "Times New Roman",
  "font_size": 12,
  "line_spacing": 2.0,
  "include_toc": false,
  "include_page_numbers": true,
  "include_running_header": true,
  "verbose": false
}
```

## Docker Configuration

Override via environment variables in `docker-compose.yml` or `.env` file:

```yaml
services:
  backend:
    environment:
      - AMF_ENVIRONMENT=production
      - AMF_DEBUG=false
```

## Frontend Configuration

Frontend uses `NEXT_PUBLIC_API_URL` to point to the backend:

```bash
# Development
NEXT_PUBLIC_API_URL=http://localhost:8000

# Production
NEXT_PUBLIC_API_URL=https://api.amf.example.com
```

## SDK Configuration

```python
from amf_sdk import AMFClient

# Custom endpoint
client = AMFClient(base_url="https://api.amf.example.com")

# With API key
client = AMFClient(base_url="https://api.amf.example.com", api_key="sk-...")
```
