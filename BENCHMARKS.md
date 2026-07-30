# Benchmarks

## Methodology

Benchmarks are performed on a standardized test environment:

- **CPU**: 4 cores @ 3.4GHz
- **RAM**: 8GB DDR4
- **Storage**: NVMe SSD
- **OS**: Ubuntu 22.04 LTS
- **Docker**: 24.0

## Formatter Performance

### Single Manuscript

| Style | 10 pages | 50 pages | 100 pages | 300 pages |
|-------|:--------:|:--------:|:---------:|:---------:|
| APA | 0.8s | 2.1s | 3.8s | 8.5s |
| MLA | 0.7s | 1.9s | 3.5s | 7.9s |
| Chicago | 0.9s | 2.3s | 4.1s | 9.2s |
| IEEE | 0.6s | 1.7s | 3.2s | 7.1s |
| Harvard | 0.7s | 1.8s | 3.4s | 7.5s |
| Vancouver | 0.8s | 2.0s | 3.7s | 8.1s |

### Throughput (concurrent requests)

| Concurrent Users | Avg Response | Throughput |
|:----------------:|:------------:|:----------:|
| 1 | 2.1s | 28 req/min |
| 5 | 3.4s | 88 req/min |
| 10 | 5.2s | 115 req/min |
| 25 | 11.8s | 127 req/min |

## API Response Times

### Format Endpoint (50-page manuscript)

| Percentile | Time |
|:----------:|:----:|
| p50 | 2.1s |
| p75 | 2.8s |
| p95 | 3.4s |
| p99 | 4.5s |

### Validation Endpoint

| Percentile | Time |
|:----------:|:----:|
| p50 | 120ms |
| p75 | 180ms |
| p95 | 250ms |
| p99 | 400ms |

## Docker Performance

| Metric | Native | Docker |
|--------|:------:|:------:|
| Format time (50p) | 1.9s | 2.1s |
| Memory (idle) | 85MB | 95MB |
| Memory (formatting) | 180MB | 195MB |
| Image size | — | 280MB |

## Test Your Own

```bash
# Benchmark formatting a test manuscript
time amf format -i test-manuscript.md -s apa

# API benchmark
ab -n 100 -c 10 -p payload.json -T application/json http://localhost:8000/api/v1/format
```
