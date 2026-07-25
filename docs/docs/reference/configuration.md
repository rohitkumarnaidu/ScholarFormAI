# Configuration Reference

## Environment Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AMF_ENVIRONMENT` | string | `development` | Runtime environment |
| `AMF_DEBUG` | bool | `true` | Debug mode |
| `AMF_LOG_LEVEL` | string | `info` | Logging level |
| `AMF_MAX_UPLOAD_SIZE` | int | `10485760` | Max upload (bytes) |
| `AMF_DEFAULT_STYLE` | string | `apa` | Default citation style |
| `AMF_API_PREFIX` | string | `/api/v1` | API path prefix |
| `AMF_API_HOST` | string | `0.0.0.0` | Bind address |
| `AMF_API_PORT` | int | `8000` | API port |
| `AMF_UPLOAD_DIR` | string | `./uploads` | Upload directory |
| `AMF_ALLOWED_ORIGINS` | list | `["*"]` | CORS allowed origins |
| `AMF_SECRET_KEY` | string | — | API secret key |
| `AMF_DATABASE_URL` | string | — | Database connection |
| `AMF_REDIS_URL` | string | — | Redis connection |

## CLI Config File

Location: `~/.config/amf/config.json`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `style` | string | `apa` | Default style |
| `api_endpoint` | string | `http://localhost:8000` | API URL |
| `output_dir` | string | `.` | Output directory |
| `page_size` | string | `A4` | Page size |
| `font_family` | string | `Times New Roman` | Font family |
| `font_size` | int | `12` | Font size (pt) |
| `line_spacing` | float | `2.0` | Line spacing |
| `include_toc` | bool | `false` | Include table of contents |
| `include_page_numbers` | bool | `true` | Include page numbers |
| `include_running_header` | bool | `true` | Include running header |
| `verbose` | bool | `false` | Verbose output |

## Project Config

File: `amf.config.json` in project root.

Same schema as CLI config, but scoped to the project.
