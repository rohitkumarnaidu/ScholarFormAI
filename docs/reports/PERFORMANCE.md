# Performance Guide

## Benchmarks

### Formatting Speed

| Manuscript Size | APA | MLA | Chicago | IEEE |
| ---------------- | :---: | :---: | :-------: | :----: |
| 10 pages (2,500 words) | 0.8s | 0.7s | 0.9s | 0.6s |
| 50 pages (12,500 words) | 2.1s | 1.9s | 2.3s | 1.7s |
| 100 pages (25,000 words) | 3.8s | 3.5s | 4.1s | 3.2s |
| 300 pages (75,000 words) | 8.5s | 7.9s | 9.2s | 7.1s |

*Tested on: 4-core CPU, 8GB RAM, SSD*

### API Response Times

| Endpoint | p50 | p95 | p99 |
| ---------- | :---: | :---: | :---: |
| `POST /format` (50 pages) | 2.1s | 3.4s | 4.5s |
| `POST /validate` | 120ms | 250ms | 400ms |
| `POST /preview` | 150ms | 300ms | 500ms |
| `GET /styles` | 15ms | 25ms | 50ms |

## Optimization Tips

### For Large Manuscripts

1. Format sections independently and combine
2. Use the CLI with batch scripts for multiple manuscripts
3. Increase memory allocation for Docker containers

### For Production Deployments

1. Enable response caching for `GET /styles`
2. Use a CDN for frontend assets
3. Configure appropriate timeout values for large manuscripts
4. Use connection pooling (Docker's built-in or Nginx)

### For Concurrent Usage

1. Scale horizontally: `docker compose up -d --scale backend=3`
2. Use a load balancer (Nginx, HAProxy, or cloud LB)
3. Monitor memory usage under load
4. Set appropriate rate limits

## Profiling

```bash
# Profile a single request
pip install pyinstrument
pyinstrument -r html -o profile.html -m uvicorn app.main:app
```
