# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Prometheus metrics definition and middleware for the application.
"""

import logging
import threading
import time
from collections.abc import Callable

from fastapi import Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

logger = logging.getLogger(__name__)

# --- Metrics Definitions ---

# Pipeline Metrics
PIPELINE_REQUESTS_TOTAL = Counter(
    "pipeline_requests_total",
    "Total number of pipeline requests",
    ["status"],  # active, completed, failed
)

PIPELINE_DURATION_SECONDS = Histogram(
    "pipeline_duration_seconds",
    "Time spent processing a pipeline request",
    ["status"],  # success, error
    buckets=(1, 5, 10, 30, 60, 120, 300, 600, 1800),
)

PIPELINE_STEPS_DURATION_SECONDS = Histogram(
    "pipeline_step_duration_seconds",
    "Time spent in specific pipeline steps",
    ["step"],
    buckets=(0.1, 0.5, 1, 2, 5, 10, 30, 60),
)

PIPELINE_STAGE_DURATION_MS = Histogram(
    "pipeline_stage_duration_ms",
    "Time spent in document pipeline stages",
    ["stage"],
    buckets=(10, 25, 50, 100, 250, 500, 1_000, 2_500, 5_000, 10_000, 30_000, 60_000),
)

UPLOAD_ACK_DURATION_MS = Histogram(
    "upload_ack_duration_ms",
    "Time from upload request start to acknowledgement response",
    ["route"],
    buckets=(5, 10, 25, 50, 100, 250, 500, 1_000, 2_500, 5_000, 10_000),
)

# Agent Metrics
AGENT_TOOLS_USAGE_TOTAL = Counter(
    "agent_tools_usage_total",
    "Total usage of agent tools",
    ["tool_name", "status"],  # success, error
)

AGENT_LLM_TOKENS_TOTAL = Counter(
    "agent_llm_tokens_total",
    "Total LLM tokens consumed",
    ["provider", "model", "type"],  # input, output
)

AGENT_RETRIES_TOTAL = Counter("agent_retries_total", "Total number of agent retries triggered")

# System Metrics
ACTIVE_PROCESSING_JOBS = Gauge("active_processing_jobs", "Number of currently active processing jobs")

LLM_FAILURES_TOTAL = Counter("llm_failures_total", "Total number of LLM API failures", ["provider"])

LLM_TTFT_SECONDS = Histogram(
    "llm_ttft_seconds",
    "Time to first token for LLM responses (approximated for non-streaming calls).",
    ["provider", "model"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 20),
)

LLM_CACHE_HITS_TOTAL = Counter(
    "llm_cache_hits_total",
    "Total LLM cache hits",
    ["provider", "model"],
)

LLM_CACHE_MISSES_TOTAL = Counter(
    "llm_cache_misses_total",
    "Total LLM cache misses",
    ["provider", "model"],
)

LLM_REQUEST_DURATION_SECONDS = Histogram(
    "llm_request_duration_seconds",
    "Duration of LLM requests",
    ["provider", "model"],
    buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10, 20, 30, 60),
)

LLM_REQUESTS_TOTAL = Counter(
    "llm_requests_total",
    "Total number of LLM requests executed",
    ["provider", "model", "status"],
)

LLM_DURATION_MS = Histogram(
    "llm_duration_ms",
    "Duration of LLM requests in milliseconds",
    ["provider", "model"],
    buckets=(25, 50, 100, 250, 500, 1_000, 2_500, 5_000, 10_000, 30_000, 60_000),
)

CELERY_QUEUE_DEPTH = Gauge(
    "celery_queue_depth",
    "Depth of Celery queues",
    ["queue"],
)

SSE_ACTIVE_CONNECTIONS = Gauge(
    "sse_active_connections",
    "Active SSE connections",
)

SSE_CONNECTIONS_TOTAL = Counter(
    "sse_connections_total",
    "Total SSE connections opened",
)

WS_ACTIVE_CONNECTIONS = Gauge(
    "ws_active_connections",
    "Active WebSocket connections",
)

WS_CONNECTIONS_TOTAL = Counter(
    "ws_connections_total",
    "Total WebSocket connections opened",
)

CLAMAV_SCAN_DURATION_SECONDS = Histogram(
    "clamav_scan_duration_seconds",
    "Duration of ClamAV scans",
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
)

ACTIVE_USERS = Gauge(
    "active_users",
    "Active authenticated users in the last 5 minutes",
)

PROVIDER_OPERATIONS_TOTAL = Counter(
    "provider_operations_total",
    "Custom provider CRUD operations",
    ["action", "status"],
)

PERSONA_EVENTS_TOTAL = Counter(
    "persona_events_total",
    "Persona-level KPI events by operation outcome",
    ["persona", "event", "outcome"],
)

PERSONA_OPERATION_DURATION_SECONDS = Histogram(
    "persona_operation_duration_seconds",
    "Latency of persona operations",
    ["persona", "operation"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 20, 30, 60),
)

_ACTIVE_USERS_WINDOW_SECONDS = 300
_active_user_last_seen: dict[str, float] = {}
_active_user_lock = threading.Lock()

# --- Middleware ---


async def prometheus_metrics_middleware(request: Request, call_next: Callable) -> Response:
    """
    Middleware to handle /metrics endpoint and track basic request metrics.
    """
    if request.url.path == "/metrics":
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return await call_next(request)


class MetricsManager:
    """Helper class to record metrics from anywhere in the app."""

    @staticmethod
    def record_pipeline_start():
        PIPELINE_REQUESTS_TOTAL.labels(status="active").inc()
        ACTIVE_PROCESSING_JOBS.inc()

    @staticmethod
    def record_pipeline_completion(duration: float, success: bool):
        status = "success" if success else "error"
        PIPELINE_REQUESTS_TOTAL.labels(status="completed" if success else "failed").inc()
        PIPELINE_DURATION_SECONDS.labels(status=status).observe(duration)
        ACTIVE_PROCESSING_JOBS.dec()

    @staticmethod
    def record_step_duration(step_name: str, duration: float):
        PIPELINE_STEPS_DURATION_SECONDS.labels(step=step_name).observe(duration)

    @staticmethod
    def record_pipeline_stage_duration(stage_name: str, duration_seconds: float):
        PIPELINE_STAGE_DURATION_MS.labels(stage=stage_name).observe(max(duration_seconds, 0.0) * 1000.0)

    @staticmethod
    def record_upload_ack_duration(duration_seconds: float, route: str = "documents"):
        UPLOAD_ACK_DURATION_MS.labels(route=route).observe(max(duration_seconds, 0.0) * 1000.0)

    @staticmethod
    def record_tool_usage(tool_name: str, success: bool):
        status = "success" if success else "error"
        AGENT_TOOLS_USAGE_TOTAL.labels(tool_name=tool_name, status=status).inc()

    @staticmethod
    def record_llm_usage(provider: str, model: str, input_tokens: int, output_tokens: int):
        AGENT_LLM_TOKENS_TOTAL.labels(provider=provider, model=model, type="input").inc(input_tokens)
        AGENT_LLM_TOKENS_TOTAL.labels(provider=provider, model=model, type="output").inc(output_tokens)

    @staticmethod
    def record_llm_failure(provider: str):
        LLM_FAILURES_TOTAL.labels(provider=provider).inc()

    @staticmethod
    def record_llm_duration(provider: str, model: str, duration_seconds: float):
        LLM_REQUEST_DURATION_SECONDS.labels(provider=provider, model=model).observe(duration_seconds)
        LLM_DURATION_MS.labels(provider=provider, model=model).observe(max(duration_seconds, 0.0) * 1000.0)

    @staticmethod
    def record_llm_request(provider: str, model: str, success: bool):
        status = "success" if success else "error"
        LLM_REQUESTS_TOTAL.labels(provider=provider, model=model, status=status).inc()

    @staticmethod
    def record_llm_ttft(provider: str, model: str, duration_seconds: float):
        LLM_TTFT_SECONDS.labels(provider=provider, model=model).observe(duration_seconds)

    @staticmethod
    def record_llm_cache_hit(provider: str, model: str):
        LLM_CACHE_HITS_TOTAL.labels(provider=provider, model=model).inc()

    @staticmethod
    def record_llm_cache_miss(provider: str, model: str):
        LLM_CACHE_MISSES_TOTAL.labels(provider=provider, model=model).inc()

    @staticmethod
    def set_celery_queue_depth(queue: str, depth: int):
        CELERY_QUEUE_DEPTH.labels(queue=queue).set(depth)

    @staticmethod
    def sse_connection_open():
        SSE_ACTIVE_CONNECTIONS.inc()
        SSE_CONNECTIONS_TOTAL.inc()

    @staticmethod
    def sse_connection_closed():
        SSE_ACTIVE_CONNECTIONS.dec()

    @staticmethod
    def ws_connection_open():
        WS_ACTIVE_CONNECTIONS.inc()
        WS_CONNECTIONS_TOTAL.inc()

    @staticmethod
    def ws_connection_closed():
        WS_ACTIVE_CONNECTIONS.dec()

    @staticmethod
    def record_clamav_scan_duration(duration_seconds: float):
        CLAMAV_SCAN_DURATION_SECONDS.observe(duration_seconds)

    @staticmethod
    def record_user_activity(user_id: str):
        if not user_id:
            return
        now = time.time()
        with _active_user_lock:
            _active_user_last_seen[user_id] = now
            cutoff = now - _ACTIVE_USERS_WINDOW_SECONDS
            expired = [uid for uid, ts in _active_user_last_seen.items() if ts < cutoff]
            for uid in expired:
                _active_user_last_seen.pop(uid, None)
            ACTIVE_USERS.set(len(_active_user_last_seen))

    @staticmethod
    def record_retry():
        AGENT_RETRIES_TOTAL.inc()

    @staticmethod
    def record_provider_operation(action: str, status: str = "success"):
        PROVIDER_OPERATIONS_TOTAL.labels(action=action, status=status).inc()

    @staticmethod
    def record_persona_event(persona: str, event: str, outcome: str):
        PERSONA_EVENTS_TOTAL.labels(persona=persona, event=event, outcome=outcome).inc()

    @staticmethod
    def record_persona_latency(persona: str, operation: str, duration_seconds: float):
        PERSONA_OPERATION_DURATION_SECONDS.labels(
            persona=persona,
            operation=operation,
        ).observe(max(duration_seconds, 0.0))
