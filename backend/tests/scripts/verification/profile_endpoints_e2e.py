# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import argparse
import asyncio
import time
from collections import Counter
from statistics import mean

import httpx

DEFAULT_ENDPOINTS = [
    "/",
    "/health",
    "/ready",
    "/api/v1/health",
    "/api/v1/health/ready",
    "/api/v1/templates",
]


def _percentile(sorted_values: list[float], percentile: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]

    rank = percentile * (len(sorted_values) - 1)
    low = int(rank)
    high = min(low + 1, len(sorted_values) - 1)
    fraction = rank - low
    return sorted_values[low] + (sorted_values[high] - sorted_values[low]) * fraction


async def _sample_endpoint(
    client: httpx.AsyncClient,
    url: str,
    warmup: int,
    samples: int,
) -> dict:
    status_counts: Counter[int | str] = Counter()
    latencies_ms: list[float] = []

    for _ in range(warmup):
        try:
            response = await client.get(url)
            status_counts[response.status_code] += 1
        except Exception:
            status_counts["error"] += 1

    for _ in range(samples):
        started = time.perf_counter()
        try:
            response = await client.get(url)
            elapsed = (time.perf_counter() - started) * 1000.0
            latencies_ms.append(elapsed)
            status_counts[response.status_code] += 1
        except Exception:
            elapsed = (time.perf_counter() - started) * 1000.0
            latencies_ms.append(elapsed)
            status_counts["error"] += 1

    latencies_ms.sort()
    return {
        "url": url,
        "count": len(latencies_ms),
        "status_counts": dict(status_counts),
        "p50_ms": _percentile(latencies_ms, 0.50),
        "p95_ms": _percentile(latencies_ms, 0.95),
        "p99_ms": _percentile(latencies_ms, 0.99),
        "avg_ms": mean(latencies_ms) if latencies_ms else 0.0,
        "min_ms": latencies_ms[0] if latencies_ms else 0.0,
        "max_ms": latencies_ms[-1] if latencies_ms else 0.0,
    }


async def _run(base_url: str, endpoints: list[str], warmup: int, samples: int, timeout: float) -> None:
    normalized_base = base_url.rstrip("/")
    async with httpx.AsyncClient(timeout=timeout) as client:
        results = []
        for endpoint in endpoints:
            path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
            result = await _sample_endpoint(client, f"{normalized_base}{path}", warmup, samples)
            results.append(result)

    print("=" * 88)
    print("Endpoint Latency Profile (ms)")
    print("=" * 88)
    print(f"Base URL: {normalized_base}")
    print(f"Warmup requests per endpoint: {warmup}")
    print(f"Measured requests per endpoint: {samples}")
    print("-" * 88)

    for result in results:
        print(
            f"{result['url']:<48} "
            f"p50={result['p50_ms']:>8.2f}  "
            f"p95={result['p95_ms']:>8.2f}  "
            f"p99={result['p99_ms']:>8.2f}  "
            f"avg={result['avg_ms']:>8.2f}  "
            f"max={result['max_ms']:>8.2f}  "
            f"status={result['status_counts']}"
        )

    print("-" * 88)
    print("Slowest by p95:")
    for index, result in enumerate(sorted(results, key=lambda item: item["p95_ms"], reverse=True)[:3], start=1):
        print(f"{index}. {result['url']} -> p95={result['p95_ms']:.2f} ms")
    print("=" * 88)


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile top backend endpoints end-to-end.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Backend base URL.")
    parser.add_argument("--warmup", type=int, default=3, help="Warmup requests per endpoint.")
    parser.add_argument("--samples", type=int, default=15, help="Measured requests per endpoint.")
    parser.add_argument("--timeout", type=float, default=10.0, help="Request timeout in seconds.")
    parser.add_argument(
        "--endpoints",
        nargs="*",
        default=DEFAULT_ENDPOINTS,
        help="Endpoint paths to profile.",
    )
    args = parser.parse_args()

    asyncio.run(
        _run(
            base_url=args.base_url,
            endpoints=args.endpoints,
            warmup=args.warmup,
            samples=args.samples,
            timeout=args.timeout,
        )
    )


if __name__ == "__main__":
    main()
