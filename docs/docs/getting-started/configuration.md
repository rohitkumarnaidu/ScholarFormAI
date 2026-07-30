# Configuration

## Environment Variables

| Variable | Default | Description |
| ---------- | --------- | ------------- |
| `AMF_ENVIRONMENT` | `development` | Runtime environment |
| `AMF_DEBUG` | `true` | Debug mode |
| `AMF_LOG_LEVEL` | `info` | Logging level |
| `AMF_MAX_UPLOAD_SIZE` | `10485760` | Max upload (bytes) |
| `AMF_DEFAULT_STYLE` | `apa` | Default citation style |
| `AMF_API_HOST` | `0.0.0.0` | Bind address |
| `AMF_API_PORT` | `8000` | API port |
| `AMF_ALLOWED_ORIGINS` | `*` | CORS origins |

## CLI Config

```json
{
  "style": "apa",
  "api_endpoint": "http://localhost:8000",
  "output_dir": ".",
  "page_size": "A4",
  "font_family": "Times New Roman",
  "font_size": 12,
  "line_spacing": 2.0
}
```

## Project Config

Create `amf.config.json` in your project root:

```json
{
  "style": "apa",
  "output_dir": "./output",
  "page_size": "A4",
  "include_toc": false,
  "include_page_numbers": true
}
```
