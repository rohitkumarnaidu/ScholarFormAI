# Benchmarks

Continuous benchmarking is critical to ensure the ScholarForm AI platform scales efficiently under load.

## Benchmark Methodology

We use a combination of tools for benchmarking:

- **k6 / Locust**: For load testing HTTP endpoints and WebSocket connections.
- **pytest-benchmark**: For micro-benchmarks on critical Python functions (e.g., PyMuPDF extraction speed).

## Key Performance Indicators (KPIs)

Our baseline targets for the system are:

| Metric | Target | Description |
| -------- | -------- | ------------- |
| API Latency | < 200ms | P95 latency for non-AI standard API endpoints. |
| Formatting Speed | < 5s / page | Time taken to format an uploaded DOCX into IEEE template. |
| Generation TTFB | < 2s | Time to First Byte for streaming AI generation. |
| DB Query Latency | < 50ms | P99 latency for read queries. |

## Running Benchmarks

### HTTP Load Testing (k6)

To run the standard k6 test suite against a local deployment:

```bash
cd ops/benchmarks
k6 run api_load_test.js
```

### AI Generation Load

Simulating LLM load is challenging due to API cost and rate limits. We use a mock LLM service during load testing to evaluate system overhead (FastAPI, Redis, Celery) independent of the Groq/NVIDIA APIs.

## Historical Benchmarks

*Results from v1.0.0 stress test (AWS t3.large, 4 Celery workers)*

- Max concurrent users: 500
- Sustained throughput: 250 requests/sec
- Average Formatting Queue Time: 1.2s

## Cross-References

- [Performance Tuning](PERFORMANCE.md)
- [Testing Guide](../guides/TESTING.md)
