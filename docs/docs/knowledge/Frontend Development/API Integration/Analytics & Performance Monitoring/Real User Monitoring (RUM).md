<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

# Real User Monitoring (RUM)

<cite>
**Referenced Files in This Document**
- [rum.js](../../../../../../frontend/src/lib/rum.js)
- [analytics.js](../../../../../../frontend/src/lib/analytics.js)
- [LatencyObserver.jsx](../../../../../../frontend/src/components/monitoring/LatencyObserver.jsx)
- [route.js](../../../../../../frontend/app/api/internal/metrics/record/route.js)
- [metrics.js](../../../../../../frontend/src/lib/metrics.js)
- [prometheus_metrics.py](../../../../../../backend/app/middleware/prometheus_metrics.py)
- [monitoring.py](../../../../../../backend/app/middleware/monitoring.py)
- [route.js](../../../../../../frontend/app/api/metrics/route.js)
</cite>

## Table of Contents

1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)

## Introduction

This document describes the Real User Monitoring (RUM) implementation in the automated academic manuscript formatter. The system captures frontend performance metrics and user interactions to provide insights into real-world usage patterns and performance characteristics. The implementation consists of three primary layers:

- Frontend instrumentation: collects page load timings and user interaction events
- Backend ingestion: receives and aggregates metrics via lightweight endpoints
- Observability stack: exposes Prometheus-compatible metrics for monitoring dashboards and alerting

The current implementation uses the browser's Performance Navigation Timing API for page load measurements. It also includes a placeholder RUM module designed for future expansion.

## Project Structure

The RUM system spans both frontend and backend components:

- Frontend: instrumentation libraries, latency observer, and API routes for metric ingestion
- Backend: Prometheus metrics middleware and monitoring middleware for request telemetry

```mermaid
graph TB
subgraph "Frontend"
LO["LatencyObserver.jsx<br/>Collects page load timings"]
AN["analytics.js<br/>Event tracking wrapper"]
APIR["/api/internal/metrics/record<br/>POST handler"]
APIM["/api/metrics<br/>GET handler"]
MET["metrics.js<br/>Frontend metrics registry"]
end
subgraph "Backend"
PMW["prometheus_metrics.py<br/>Metrics definitions & helpers"]
MMW["monitoring.py<br/>Request logging & tracing"]
end
LO --> APIR
AN --> APIM
MET --> APIM
PMW --> APIM
MMW --> APIM
```

**Diagram sources**

- [LatencyObserver.jsx:1-38](../../../../../../frontend/src/components/monitoring/LatencyObserver.jsx#L1-L38)
- [analytics.js:1-20](../../../../../../frontend/src/lib/analytics.js#L1-L20)
- [route.js:1-22](../../../../../../frontend/app/api/internal/metrics/record/route.js#L1-L22)
- [route.js:1-20](../../../../../../frontend/app/api/metrics/route.js#L1-L20)
- [metrics.js:1-19](../../../../../../frontend/src/lib/metrics.js#L1-L19)
- [prometheus_metrics.py:1-300](../../../../../../backend/app/middleware/prometheus_metrics.py#L1-L300)
- [monitoring.py:1-51](../../../../../../backend/app/middleware/monitoring.py#L1-L51)

**Section sources**

- [rum.js:1-27](../../../../../../frontend/src/lib/rum.js#L1-L27)
- [posthog.js:1-140](file://frontend/src/lib/posthog.js#L1-L140) (legacy - no longer active)
- [analytics.js:1-20](../../../../../../frontend/src/lib/analytics.js#L1-L20)
- [LatencyObserver.jsx:1-38](../../../../../../frontend/src/components/monitoring/LatencyObserver.jsx#L1-L38)
- [route.js:1-22](../../../../../../frontend/app/api/internal/metrics/record/route.js#L1-L22)
- [metrics.js:1-19](../../../../../../frontend/src/lib/metrics.js#L1-L19)
- [prometheus_metrics.py:1-300](../../../../../../backend/app/middleware/prometheus_metrics.py#L1-L300)
- [monitoring.py:1-51](../../../../../../backend/app/middleware/monitoring.py#L1-L51)

## Core Components

- RUM initialization and event tracking (placeholder): Provides initialization and event tracking functions for future RUM providers.
- Analytics wrapper: Offers a non-blocking event tracking interface.
- Latency observer: Captures page load durations using the Performance Navigation Timing API and reports them to the backend.
- Frontend metrics registry: Defines a Prometheus-compatible histogram for HTTP request durations and registers default metrics.
- Internal metrics recording endpoint: Receives latency observations and updates the frontend metrics registry.
- Backend Prometheus metrics middleware: Defines comprehensive metrics for pipeline operations, agent usage, LLM performance, and system health.
- Backend monitoring middleware: Adds request ID generation, timing, and logging for observability.

**Section sources**

- [rum.js:1-27](../../../../../../frontend/src/lib/rum.js#L1-L27)
- [analytics.js:1-20](../../../../../../frontend/src/lib/analytics.js#L1-L20)
- [LatencyObserver.jsx:1-38](../../../../../../frontend/src/components/monitoring/LatencyObserver.jsx#L1-L38)
- [metrics.js:1-19](../../../../../../frontend/src/lib/metrics.js#L1-L19)
- [route.js:1-22](../../../../../../frontend/app/api/internal/metrics/record/route.js#L1-L22)
- [prometheus_metrics.py:1-300](../../../../../../backend/app/middleware/prometheus_metrics.py#L1-L300)
- [monitoring.py:1-51](../../../../../../backend/app/middleware/monitoring.py#L1-L51)

## Architecture Overview

The RUM architecture combines frontend instrumentation with backend ingestion and metrics exposure:

```mermaid
sequenceDiagram
participant Browser as "Browser"
participant LO as "LatencyObserver.jsx"
participant APIR as "Internal Metrics Record Route"
participant MET as "Frontend Metrics Registry"
participant APIM as "Metrics Endpoint"
Browser->>LO : "Navigation complete"
LO->>LO : "Read performance.navigation.duration"
LO->>APIR : "POST /api/internal/metrics/record {method, route, status, duration}"
APIR->>MET : "Observe duration in histogram"
Browser->>APIM : "GET /api/metrics"
APIM-->>Browser : "Prometheus metrics payload"
```

**Diagram sources**

- [LatencyObserver.jsx:1-38](../../../../../../frontend/src/components/monitoring/LatencyObserver.jsx#L1-L38)
- [route.js:1-22](../../../../../../frontend/app/api/internal/metrics/record/route.js#L1-L22)
- [metrics.js:1-19](../../../../../../frontend/src/lib/metrics.js#L1-L19)
- [route.js:1-20](../../../../../../frontend/app/api/metrics/route.js#L1-L20)

## Detailed Component Analysis

### Frontend RUM and Analytics

- RUM module: Provides stubbed functions for initialization and event tracking, intended for future expansion.
- Analytics wrapper: Non-blocking event tracking interface.

```mermaid
flowchart TD
Capture --> End["Complete"]
Flush --> End
```

**Section sources**

- [rum.js:1-27](../../../../../../frontend/src/lib/rum.js#L1-L27)
- [analytics.js:1-20](../../../../../../frontend/src/lib/analytics.js#L1-L20)

### Latency Observation and Ingestion

- Latency observer: Uses the Performance Navigation Timing API to measure page load duration and sends the data to the internal metrics recording endpoint.
- Internal metrics recording endpoint: Parses incoming metrics and records them in the frontend metrics registry as a histogram observation.
- Frontend metrics registry: Exposes a Prometheus-compatible histogram for HTTP request durations and registers default metrics.

```mermaid
sequenceDiagram
participant LO as "LatencyObserver.jsx"
participant APIR as "Internal Metrics Record Route"
participant REG as "Frontend Metrics Registry"
LO->>APIR : "POST {method, route, status, duration}"
APIR->>REG : "Observe duration with labels"
REG-->>APIR : "OK"
```

**Diagram sources**

- [LatencyObserver.jsx:8-26](../../../../../../frontend/src/components/monitoring/LatencyObserver.jsx#L8-L26)
- [route.js:6-15](../../../../../../frontend/app/api/internal/metrics/record/route.js#L6-L15)
- [metrics.js:8-15](../../../../../../frontend/src/lib/metrics.js#L8-L15)

**Section sources**

- [LatencyObserver.jsx:1-38](../../../../../../frontend/src/components/monitoring/LatencyObserver.jsx#L1-L38)
- [route.js:1-22](../../../../../../frontend/app/api/internal/metrics/record/route.js#L1-L22)
- [metrics.js:1-19](../../../../../../frontend/src/lib/metrics.js#L1-L19)

### Backend Metrics Exposure

- Backend Prometheus metrics middleware: Defines counters, histograms, and gauges for pipeline operations, agent tool usage, LLM performance, and system health.
- Backend monitoring middleware: Adds request ID generation, timing, and logging for improved observability.

```mermaid
classDiagram
class MetricsManager {
+record_pipeline_start()
+record_pipeline_completion(duration, success)
+record_step_duration(step_name, duration)
+record_pipeline_stage_duration(stage_name, duration_seconds)
+record_upload_ack_duration(duration_seconds, route)
+record_tool_usage(tool_name, success)
+record_llm_usage(provider, model, input_tokens, output_tokens)
+record_llm_failure(provider)
+record_llm_duration(provider, model, duration_seconds)
+record_llm_request(provider, model, success)
+record_llm_ttft(provider, model, duration_seconds)
+record_llm_cache_hit(provider, model)
+record_llm_cache_miss(provider, model)
+set_celery_queue_depth(queue, depth)
+sse_connection_open()
+sse_connection_closed()
+ws_connection_open()
+ws_connection_closed()
+record_clamav_scan_duration(duration_seconds)
+record_user_activity(user_id)
+record_retry()
+record_persona_event(persona, event, outcome)
+record_persona_latency(persona, operation, duration_seconds)
}
```

**Diagram sources**

- [prometheus_metrics.py:184-300](../../../../../../backend/app/middleware/prometheus_metrics.py#L184-L300)

**Section sources**

- [prometheus_metrics.py:1-300](../../../../../../backend/app/middleware/prometheus_metrics.py#L1-L300)
- [monitoring.py:1-51](../../../../../../backend/app/middleware/monitoring.py#L1-L51)

## Dependency Analysis

The RUM system exhibits clear separation of concerns:

- Frontend instrumentation depends on the internal metrics endpoint for latency reporting.
- Backend metrics exposure depends on Prometheus client definitions and middleware registration.
- The internal metrics recording endpoint bridges frontend latency observations with the frontend metrics registry.

```mermaid
graph TB
LO["LatencyObserver.jsx"] --> APIR["/api/internal/metrics/record"]
AN["analytics.js"] --> APIM["/api/metrics"]
MET["metrics.js"] --> APIM
PMW["prometheus_metrics.py"] --> APIM
MMW["monitoring.py"] --> APIM
```

**Diagram sources**

- [LatencyObserver.jsx:1-38](../../../../../../frontend/src/components/monitoring/LatencyObserver.jsx#L1-L38)
- [route.js:1-22](../../../../../../frontend/app/api/internal/metrics/record/route.js#L1-L22)
- [analytics.js:1-20](../../../../../../frontend/src/lib/analytics.js#L1-L20)
- [route.js:1-20](../../../../../../frontend/app/api/metrics/route.js#L1-L20)
- [metrics.js:1-19](../../../../../../frontend/src/lib/metrics.js#L1-L19)
- [prometheus_metrics.py:1-300](../../../../../../backend/app/middleware/prometheus_metrics.py#L1-L300)
- [monitoring.py:1-51](../../../../../../backend/app/middleware/monitoring.py#L1-L51)

**Section sources**

- [route.js:1-22](../../../../../../frontend/app/api/internal/metrics/record/route.js#L1-L22)
- [route.js:1-20](../../../../../../frontend/app/api/metrics/route.js#L1-L20)
- [prometheus_metrics.py:1-300](../../../../../../backend/app/middleware/prometheus_metrics.py#L1-L300)
- [monitoring.py:1-51](../../../../../../backend/app/middleware/monitoring.py#L1-L51)

## Performance Considerations

- Frontend metrics overhead: The internal metrics recording endpoint performs minimal work and uses a histogram with carefully chosen buckets for efficient aggregation.
- Backend metrics granularity: The backend Prometheus middleware defines numerous metrics with appropriate bucket configurations to balance accuracy and cardinality.

## Troubleshooting Guide

- Latency metrics missing: Confirm that the internal metrics recording endpoint is reachable and that the frontend metrics registry is properly registered.
- Backend metrics not exposed: Ensure the metrics endpoint is accessible and that the Prometheus middleware is registered in the backend application.

**Section sources**

- [analytics.js:7-19](../../../../../../frontend/src/lib/analytics.js#L7-L19)
- [route.js:6-15](../../../../../../frontend/app/api/internal/metrics/record/route.js#L6-L15)
- [route.js:6-15](../../../../../../frontend/app/api/metrics/route.js#L6-L15)

## Conclusion

The RUM implementation provides a solid foundation for collecting real user performance and engagement signals. The frontend instrumentation leverages the Performance Navigation Timing API and integrates, while the backend offers comprehensive metrics exposure via Prometheus. The modular design allows for easy extension to additional RUM providers and enhanced monitoring capabilities.
