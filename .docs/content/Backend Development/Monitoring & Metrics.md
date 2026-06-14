# Monitoring & Metrics

<cite>
**Referenced Files in This Document**
- [main.py](file://backend/app/main.py)
- [prometheus_metrics.py](file://backend/app/middleware/prometheus_metrics.py)
- [monitoring.py](file://backend/app/middleware/monitoring.py)
- [metrics.py](file://backend/app/routers/v1/metrics.py)
- [settings.py](file://backend/app/config/settings.py)
- [health_checks.py](file://backend/app/services/health_checks.py)
- [model_metrics.py](file://backend/app/services/model_metrics.py)
- [metrics.py](file://backend/app/pipeline/agents/metrics.py)
- [_helpers.py](file://backend/app/routers/v1/_helpers.py)
- [pipeline.json](file://backend/docker/grafana/dashboards/pipeline.json)
- [scholarform-overview.json](file://backend/ops/grafana/dashboards/scholarform-overview.json)
- [scholarform-persona-kpis.json](file://backend/ops/grafana/dashboards/scholarform-persona-kpis.json)
- [prometheus.yml](file://backend/docker/prometheus/prometheus.yml)
- [prometheus.yml](file://backend/ops/prometheus/prometheus.yml)
- [docker-compose.yml](file://backend/docker/docker-compose.yml)
- [sentry.client.config.js](file://frontend/sentry.client.config.js)
- [sentry.server.config.js](file://frontend/sentry.server.config.js)
- [sentry.edge.config.js](file://frontend/sentry.edge.config.js)
- [test_database.py](file://backend/tests/test_database.py)
- [llm_validator.py](file://backend/app/pipeline/safety/llm_validator.py)
- [test_persona_kpi_dashboard.py](file://backend/tests/test_persona_kpi_dashboard.py)
</cite>

## Update Summary
**Changes Made**
- Enhanced monitoring system with new Grafana dashboards (scholarform-persona-kpis.json)
- Added persona-based KPI tracking with dedicated metrics (persona_events_total, persona_operation_duration_seconds)
- Consolidated metrics functionality into new v1 metrics router (/api/v1/metrics)
- Implemented automatic persona KPI recording for all API operations
- Added vLLM adoption readiness monitoring
- Updated metrics exposure endpoints to use v1 router structure

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
10. [Appendices](#appendices)

## Introduction
This document describes the monitoring and metrics system for the Automated Academic Docx Manuscript Formatter. It covers Prometheus instrumentation, custom metrics collection, Grafana dashboards, health and readiness checks, alerting strategies, log aggregation, distributed tracing integration, and enhanced error filtering with Sentry. The system now includes persona-based KPI tracking, consolidated v1 metrics router, and enhanced real-time metrics capabilities. The monitoring architecture has been significantly enhanced with new Grafana dashboards for persona analytics and improved metrics collection infrastructure.

## Project Structure
The monitoring stack integrates:
- Prometheus scraping of the FastAPI application's /metrics endpoint
- Grafana dashboards for pipeline, LLM, business KPIs, and persona analytics
- Health and readiness endpoints for platform observability
- Custom metrics for pipeline performance, queue depths, processing times, error rates, and persona-based KPIs
- Enhanced Sentry error filtering that removes cancellation events and keyboard interrupts
- Graceful degradation when Sentry SDK is unavailable
- Optional persistence of model metrics to Supabase
- Comprehensive frontend Sentry integration for client, server, and edge environments
- **New**: Persona-based KPI tracking with automatic operation monitoring
- **New**: Consolidated v1 metrics router for unified metrics access

```mermaid
graph TB
subgraph "Backend"
A["FastAPI App<br/>/metrics exposed"]
B["Monitoring Middleware<br/>request logs, timing"]
C["Prometheus Metrics Middleware<br/>custom metrics + persona KPIs"]
D["Health/Readiness Services"]
E["Model Metrics Persistence"]
F["Sentry Error Filtering<br/>_sentry_before_send"]
G["Graceful Degradation<br/>SENTRY_AVAILABLE check"]
H["V1 Metrics Router<br/>/api/v1/metrics"]
I["Persona KPI Recording<br/>automatic operation tracking"]
end
subgraph "Frontend"
J["Sentry Client Config<br/>Browser Errors"]
K["Sentry Server Config<br/>Server-side Errors"]
L["Sentry Edge Config<br/>Edge Functions"]
end
subgraph "Observability"
P["Prometheus Scrape Config"]
G["Grafana Dashboards<br/>Pipeline + Persona KPIs"]
S["Sentry Error Tracking"]
end
subgraph "External Systems"
R["Redis/Celery Broker"]
M["LLM Providers"]
N["vLLM Adoption Metrics"]
END
A --> B
A --> C
A --> D
A --> E
A --> F
A --> G
A --> H
H --> I
C --> P
P --> G
F --> S
G --> S
A --> R
A --> M
A --> N
J --> S
K --> S
L --> S
```

**Diagram sources**
- [main.py:45-106](file://backend/app/main.py#L45-L106)
- [prometheus_metrics.py:15-167](file://backend/app/middleware/prometheus_metrics.py#L15-L167)
- [monitoring.py:13-51](file://backend/app/middleware/monitoring.py#L13-L51)
- [health_checks.py:85-127](file://backend/app/services/health_checks.py#L85-L127)
- [model_metrics.py:101-137](file://backend/app/services/model_metrics.py#L101-L137)
- [metrics.py:24-248](file://backend/app/routers/v1/metrics.py#L24-L248)
- [_helpers.py:32-68](file://backend/app/routers/v1/_helpers.py#L32-L68)
- [main.py:47-66](file://backend/app/main.py#L47-L66)
- [prometheus.yml:5-16](file://backend/docker/prometheus/prometheus.yml#L5-L16)
- [scholarform-overview.json:1-239](file://backend/ops/grafana/dashboards/scholarform-overview.json#L1-L239)
- [scholarform-persona-kpis.json:1-142](file://backend/ops/grafana/dashboards/scholarform-persona-kpis.json#L1-L142)
- [sentry.client.config.js:1-20](file://frontend/sentry.client.config.js#L1-L20)
- [sentry.server.config.js:1-12](file://frontend/sentry.server.config.js#L1-L12)
- [sentry.edge.config.js:1-11](file://frontend/sentry.edge.config.js#L1-L11)

**Section sources**
- [main.py:45-106](file://backend/app/main.py#L45-L106)
- [prometheus_metrics.py:15-167](file://backend/app/middleware/prometheus_metrics.py#L15-L167)
- [monitoring.py:13-51](file://backend/app/middleware/monitoring.py#L13-L51)
- [health_checks.py:85-127](file://backend/app/services/health_checks.py#L85-L127)
- [model_metrics.py:101-137](file://backend/app/services/model_metrics.py#L101-L137)
- [metrics.py:24-248](file://backend/app/routers/v1/metrics.py#L24-L248)
- [_helpers.py:32-68](file://backend/app/routers/v1/_helpers.py#L32-L68)
- [main.py:47-66](file://backend/app/main.py#L47-L66)
- [prometheus.yml:5-16](file://backend/docker/prometheus/prometheus.yml#L5-L16)
- [scholarform-overview.json:1-239](file://backend/ops/grafana/dashboards/scholarform-overview.json#L1-L239)
- [scholarform-persona-kpis.json:1-142](file://backend/ops/grafana/dashboards/scholarform-persona-kpis.json#L1-L142)
- [sentry.client.config.js:1-20](file://frontend/sentry.client.config.js#L1-L20)
- [sentry.server.config.js:1-12](file://frontend/sentry.server.config.js#L1-L12)
- [sentry.edge.config.js:1-11](file://frontend/sentry.edge.config.js#L1-L11)

## Core Components
- Prometheus instrumentation and custom metrics:
  - Pipeline request volume, durations, and step durations
  - Agent tool usage, LLM token consumption, TTFT, cache hits/misses, failures
  - Queue depths (Celery), real-time connections (SSE/WebSocket)
  - Active users and ClamAV scan durations
  - **New**: Persona-based KPIs (persona_events_total, persona_operation_duration_seconds) with automatic operation tracking
- Enhanced Sentry error filtering:
  - Automatic filtering of asyncio.CancelledError and KeyboardInterrupt exceptions
  - Prevention of noise in monitoring system from intentional cancellations
  - Improved accuracy of error reporting for genuine issues
  - Graceful degradation when Sentry SDK is unavailable
- **Enhanced**: Consolidated metrics exposure:
  - V1 metrics router at /api/v1/metrics with unified endpoint structure
  - Database health, dashboard summaries, enhancements, and vLLM readiness monitoring
  - Frontend error logging with automatic tool usage tracking
- Health and readiness:
  - Health endpoint aggregates DB, LLM providers, and AI models
  - Readiness endpoint validates DB, external services, and model availability
- **Enhanced**: Grafana dashboards:
  - Pipeline dashboard for throughput, latency, and step breakdown
  - Overview dashboard for RPS, error rate, latency, pipeline, LLM, real-time, and business KPIs
  - **New**: Persona KPI dashboard for persona-based analytics (throughput, latency, success rates)
- Persistence and summaries:
  - Model metrics recorded and persisted asynchronously to Supabase
  - Agent vs legacy performance tracking stored locally and summarized
- Frontend Sentry integration:
  - Client-side error tracking with replay capabilities
  - Server-side error tracking for API endpoints
  - Edge function error tracking for serverless components

**Section sources**
- [prometheus_metrics.py:15-167](file://backend/app/middleware/prometheus_metrics.py#L15-L167)
- [prometheus_metrics.py:144-235](file://backend/app/middleware/prometheus_metrics.py#L144-L235)
- [metrics.py:24-248](file://backend/app/routers/v1/metrics.py#L24-L248)
- [main.py:360-380](file://backend/app/main.py#L360-L380)
- [health_checks.py:130-192](file://backend/app/services/health_checks.py#L130-L192)
- [model_metrics.py:23-181](file://backend/app/services/model_metrics.py#L23-L181)
- [metrics.py:48-260](file://backend/app/pipeline/agents/metrics.py#L48-L260)
- [scholarform-persona-kpis.json:1-142](file://backend/ops/grafana/dashboards/scholarform-persona-kpis.json#L1-L142)
- [pipeline.json:1-448](file://backend/docker/grafana/dashboards/pipeline.json#L1-L448)
- [scholarform-overview.json:1-239](file://backend/ops/grafana/dashboards/scholarform-overview.json#L1-L239)
- [main.py:47-66](file://backend/app/main.py#L47-L66)
- [sentry.client.config.js:1-20](file://frontend/sentry.client.config.js#L1-L20)
- [sentry.server.config.js:1-12](file://frontend/sentry.server.config.js#L1-L12)
- [sentry.edge.config.js:1-11](file://frontend/sentry.edge.config.js#L1-L11)

## Architecture Overview
The monitoring architecture integrates Prometheus scraping, custom metrics recording, and Grafana visualization. Enhanced Sentry error filtering prevents cancellation events from cluttering error reports. Graceful degradation ensures the system continues operating even when Sentry SDK is unavailable. Health and readiness endpoints provide operational signals. Optional Supabase persistence captures model performance for long-term analysis. The frontend includes comprehensive Sentry integration for client, server, and edge environments. **New persona-based KPI tracking automatically monitors all API operations with persona categorization.**

```mermaid
sequenceDiagram
participant Client as "Client"
participant V1Router as "V1 Metrics Router"
participant App as "FastAPI App"
participant PromMW as "Prometheus Metrics Middleware"
participant Inst as "FastAPI Instrumentator"
participant Sentry as "Sentry Error Filter"
participant SentryInit as "Sentry Initialization"
participant PersonaKPI as "Persona KPI Recorder"
participant Prom as "Prometheus"
participant Graf as "Grafana"
Client->>V1Router : HTTP request to /api/v1/metrics/*
V1Router->>App : Dispatch request
App->>PromMW : Dispatch request
PromMW-->>App : Continue chain
App->>Inst : Instrument route metrics
App->>PersonaKPI : Record persona KPIs
PersonaKPI-->>Prom : Update persona metrics
App->>SentryInit : Initialize Sentry
SentryInit-->>App : Check SENTRY_AVAILABLE
App->>Sentry : Process exceptions
Sentry-->>App : Filter cancellation events
App-->>Client : Response
App->>Prom : Expose /metrics
Prom->>Prom : Scrape targets
Graf->>Prom : Query dashboards
Graf-->>Client : Render panels (including Persona KPIs)
```

**Diagram sources**
- [main.py:273-274](file://backend/app/main.py#L273-L274)
- [prometheus_metrics.py:135-142](file://backend/app/middleware/prometheus_metrics.py#L135-L142)
- [metrics.py:24-248](file://backend/app/routers/v1/metrics.py#L24-L248)
- [_helpers.py:54-68](file://backend/app/routers/v1/_helpers.py#L54-L68)
- [main.py:47-66](file://backend/app/main.py#L47-L66)
- [prometheus.yml:5-16](file://backend/docker/prometheus/prometheus.yml#L5-L16)
- [scholarform-persona-kpis.json:1-142](file://backend/ops/grafana/dashboards/scholarform-persona-kpis.json#L1-L142)

## Detailed Component Analysis

### Enhanced Prometheus Metrics Middleware with Persona KPIs
Defines and records custom metrics for:
- Pipeline: total requests, duration histograms, per-step durations
- Agents: tool usage, retries, LLM token consumption, TTFT, cache stats, failures
- System: active processing jobs, queue depths, real-time connections, ClamAV scans, active users
- **New**: Persona KPIs: automatic operation tracking by persona category (formatter, authoring, synthesis, billing, templates, platform)

```mermaid
classDiagram
class MetricsManager {
+record_pipeline_start()
+record_pipeline_completion(duration, success)
+record_step_duration(step_name, duration)
+record_tool_usage(tool_name, success)
+record_llm_usage(provider, model, input_tokens, output_tokens)
+record_llm_failure(provider)
+record_llm_duration(provider, model, duration_seconds)
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
- [prometheus_metrics.py:144-300](file://backend/app/middleware/prometheus_metrics.py#L144-L300)

**Section sources**
- [prometheus_metrics.py:15-167](file://backend/app/middleware/prometheus_metrics.py#L15-L167)
- [prometheus_metrics.py:144-300](file://backend/app/middleware/prometheus_metrics.py#L144-L300)

### Persona-Based KPI Tracking System
**New**: Automatic persona KPI recording for all API operations with intelligent persona categorization:
- Automatic persona resolution from URL paths (formatter, authoring, synthesis, billing, templates, platform)
- Operation name sanitization for metric labels
- Outcome tracking (success/error) with automatic latency recording
- Integration with v1 router helper functions for seamless operation

```mermaid
flowchart TD
Path["API Request Path"] --> Resolve["Resolve Persona from Path"]
Resolve --> Formatter["/api/v1/documents → formatter"]
Resolve --> Authoring["/api/v1/generator → authoring"]
Resolve --> Synthesis["/api/v1/synthesis → synthesis"]
Resolve --> Billing["/api/v1/billing → billing"]
Resolve --> Templates["/api/v1/templates → templates"]
Resolve --> Platform["Other paths → platform"]
Operation["Operation Name"] --> Sanitize["Sanitize to Metric Label"]
Outcome["Operation Result"] --> Track["Track KPIs"]
Latency["Duration Seconds"] --> Track
Track --> Metrics["Update persona_events_total<br/>and persona_operation_duration_seconds"]
```

**Diagram sources**
- [_helpers.py:32-68](file://backend/app/routers/v1/_helpers.py#L32-L68)
- [prometheus_metrics.py:291-299](file://backend/app/middleware/prometheus_metrics.py#L291-L299)

**Section sources**
- [_helpers.py:32-68](file://backend/app/routers/v1/_helpers.py#L32-L68)
- [prometheus_metrics.py:291-299](file://backend/app/middleware/prometheus_metrics.py#L291-L299)

### Enhanced V1 Metrics Router
**New**: Consolidated metrics functionality in unified v1 router:
- Database health monitoring with authentication requirements
- Frontend error logging with automatic tool usage tracking
- Health checks with LLM provider status
- Dashboard summaries with model metrics, A/B testing, and database counts
- Enhancement capability profiles with queue status
- **New**: vLLM adoption readiness monitoring

```mermaid
sequenceDiagram
participant Client as "Client"
participant V1Router as "V1 Metrics Router"
participant DB as "Supabase Client"
participant LLM as "LLM Service"
participant MM as "ModelMetrics"
participant EM as "EnhancementManager"
Client->>V1Router : GET /api/v1/metrics/db
V1Router->>DB : Count documents
DB-->>V1Router : Count
V1Router-->>Client : {status, backend, document_count}
Client->>V1Router : POST /api/v1/metrics/log-error
V1Router->>V1Router : Log error + increment frontend tool usage
V1Router-->>Client : {status : "logged"}
Client->>V1Router : GET /api/v1/metrics/health
V1Router->>LLM : check_health()
V1Router->>DB : Health check
V1Router-->>Client : {status, components}
Client->>V1Router : GET /api/v1/metrics/dashboard
V1Router->>MM : get_summary(), get_model_comparison()
V1Router->>DB : Count model_metrics, ab_test_results
DB-->>V1Router : Counts
V1Router-->>Client : {persistent_db_status, database_records, live_*}
```

**Diagram sources**
- [metrics.py:24-248](file://backend/app/routers/v1/metrics.py#L24-L248)
- [health_checks.py:85-127](file://backend/app/services/health_checks.py#L85-L127)
- [model_metrics.py:148-181](file://backend/app/services/model_metrics.py#L148-L181)

**Section sources**
- [metrics.py:24-248](file://backend/app/routers/v1/metrics.py#L24-L248)
- [health_checks.py:85-127](file://backend/app/services/health_checks.py#L85-L127)
- [model_metrics.py:148-181](file://backend/app/services/model_metrics.py#L148-L181)

### Enhanced Sentry Error Filtering and Graceful Degradation
The backend now includes sophisticated error filtering that prevents cancellation events and keyboard interrupts from appearing in Sentry error reports. The system implements graceful degradation when the Sentry SDK is unavailable, ensuring the application continues operating normally without error reporting functionality.

**Updated** Enhanced error filtering with comprehensive _sentry_before_send function and graceful degradation for production stability

```mermaid
flowchart TD
Start(["Exception Occurs"]) --> CheckHint["Check exception hint"]
CheckHint --> TypeCheck{"Is instance of<br/>CancelledError or<br/>KeyboardInterrupt?"}
TypeCheck --> |Yes| FilterOut["Filter out event<br/>(return None)"]
TypeCheck --> |No| CheckTypes["Check exception types<br/>in event.values"]
CheckTypes --> TypeFilter{"Type contains<br/>cancellederror or<br/>keyboardinterrupt?"}
TypeFilter --> |Yes| FilterOut
TypeFilter --> |No| AllowThrough["Allow event<br/>through"]
FilterOut --> End(["Event filtered"])
AllowThrough --> End
subgraph "Graceful Degradation"
InitStart(["Initialize Sentry"]) --> CheckSDK{"SENTRY_AVAILABLE?"}
CheckSDK --> |No| SkipInit["Skip initialization<br/>with info log"]
CheckSDK --> |Yes| CheckDSN{"Has SENTRY_DSN?"}
CheckDSN --> |No| SkipInit
CheckDSN --> |Yes| InitSuccess["Initialize Sentry<br/>with before_send filter"]
SkipInit --> End2(["Continue without<br/>error reporting"])
InitSuccess --> End2
End2 --> End
```

**Diagram sources**
- [main.py:45-106](file://backend/app/main.py#L45-L106)

**Section sources**
- [main.py:45-106](file://backend/app/main.py#L45-L106)

### Frontend Sentry Integration
The frontend includes comprehensive Sentry integration across three environments:
- Client-side configuration with replay capabilities for user interaction analysis
- Server-side configuration for API error tracking
- Edge configuration for serverless function monitoring

**Updated** Added comprehensive frontend Sentry configuration for client, server, and edge environments

```mermaid
flowchart TD
ClientConfig["Client Config<br/>Browser Errors<br/>Replays"] --> SentryClient["Sentry Client"]
ServerConfig["Server Config<br/>Server-side Errors"] --> SentryServer["Sentry Server"]
EdgeConfig["Edge Config<br/>Edge Functions"] --> SentryEdge["Sentry Edge"]
SentryClient --> CentralHub["Central Sentry Hub"]
SentryServer --> CentralHub
SentryEdge --> CentralHub
CentralHub --> Analytics["Analytics & Reporting"]
CentralHub --> Alerts["Alerts & Notifications"]
```

**Diagram sources**
- [sentry.client.config.js:1-20](file://frontend/sentry.client.config.js#L1-L20)
- [sentry.server.config.js:1-12](file://frontend/sentry.server.config.js#L1-L12)
- [sentry.edge.config.js:1-11](file://frontend/sentry.edge.config.js#L1-L11)

**Section sources**
- [sentry.client.config.js:1-20](file://frontend/sentry.client.config.js#L1-L20)
- [sentry.server.config.js:1-12](file://frontend/sentry.server.config.js#L1-L12)
- [sentry.edge.config.js:1-11](file://frontend/sentry.edge.config.js#L1-L11)

### Metrics Exposure and Endpoints
**Enhanced**: Unified v1 metrics router structure:
- /api/v1/metrics/db: Database health and document count (admin-only)
- /api/v1/metrics/log-error: Frontend error logging with automatic tool usage tracking
- /api/v1/metrics/health: Aggregated health across DB, LLM providers, and AI models
- /api/v1/metrics/dashboard: Live summaries of model metrics, A/B testing, and DB record counts
- /api/v1/metrics/enhancements: Capability profile and queue status
- /api/v1/metrics/vllm-readiness: vLLM adoption readiness monitoring
- /metrics: Prometheus scrape endpoint handled by middleware

```mermaid
sequenceDiagram
participant Client as "Client"
participant V1Router as "V1 Metrics Router"
participant DB as "Supabase Client"
participant LLM as "LLM Service"
participant MM as "ModelMetrics"
participant EM as "EnhancementManager"
Client->>V1Router : GET /api/v1/metrics/db
V1Router->>DB : Count documents
DB-->>V1Router : Count
V1Router-->>Client : {status, backend, document_count}
Client->>V1Router : GET /api/v1/metrics/health
V1Router->>DB : Health check
V1Router->>LLM : check_health()
V1Router-->>Client : {status, components}
Client->>V1Router : GET /api/v1/metrics/dashboard
V1Router->>MM : get_summary(), get_model_comparison()
V1Router->>DB : Count model_metrics, ab_test_results
DB-->>V1Router : Counts
V1Router-->>Client : {persistent_db_status, database_records, live_*}
```

**Diagram sources**
- [metrics.py:24-248](file://backend/app/routers/v1/metrics.py#L24-L248)
- [health_checks.py:85-127](file://backend/app/services/health_checks.py#L85-L127)
- [model_metrics.py:148-181](file://backend/app/services/model_metrics.py#L148-L181)

**Section sources**
- [metrics.py:24-248](file://backend/app/routers/v1/metrics.py#L24-L248)
- [health_checks.py:85-127](file://backend/app/services/health_checks.py#L85-L127)
- [model_metrics.py:148-181](file://backend/app/services/model_metrics.py#L148-L181)

### Health and Readiness
- Health endpoint aggregates DB, LLM providers, and AI models; returns 200 healthy or 503 degraded
- Readiness endpoint validates DB, external services, and model loading; used by orchestrators for startup gating

```mermaid
flowchart TD
Start(["Call /health or /ready"]) --> CheckDB["Check Supabase health"]
CheckDB --> DBOK{"DB healthy?"}
DBOK --> |No| Degraded["Set status degraded"]
DBOK --> |Yes| CheckLLM["Check LLM providers"]
CheckLLM --> LLMOK{"Any LLM healthy?"}
LLMOK --> |No| Degraded
LLMOK --> |Yes| CheckModels["Check AI models"]
CheckModels --> ModelsOK{"Models loaded?"}
ModelsOK --> |No| Degraded
ModelsOK --> |Yes| Healthy["Set status healthy"]
Healthy --> End(["Return payload"])
Degraded --> End
```

**Diagram sources**
- [health_checks.py:85-127](file://backend/app/services/health_checks.py#L85-L127)
- [health_checks.py:130-192](file://backend/app/services/health_checks.py#L130-L192)

**Section sources**
- [health_checks.py:85-127](file://backend/app/services/health_checks.py#L85-L127)
- [health_checks.py:130-192](file://backend/app/services/health_checks.py#L130-L192)

### Enhanced Grafana Dashboards
**Enhanced**: Multiple dashboard configurations:
- Pipeline dashboard: request rate by status, active jobs gauge, P95 pipeline duration, tool usage distribution, average step duration
- Overview dashboard: RPS, error rate, latency; pipeline completed/failed rates and queue depth; LLM TTFT, tokens/sec, cache hit rate; SSE/WS connections; active users and generation jobs
- **New**: Persona KPI dashboard: persona-based throughput, latency (p95), and success rates with automatic persona categorization

```mermaid
graph LR
P["Pipeline Dashboard Panels"]
O["Overview Dashboard Panels"]
PK["Persona KPI Dashboard Panels"]
P --> P1["Rate: pipeline_requests_total"]
P --> P2["Gauge: active_processing_jobs"]
P --> P3["Quantile: pipeline_duration_seconds p95"]
P --> P4["Pie: agent_tools_usage_total"]
P --> P5["Avg: pipeline_step_duration_seconds"]
O --> O1["RPS/Error/Latency"]
O --> O2["Pipeline Rates & Queue Depth"]
O --> O3["LLM TTFT/Tokens/Cache"]
O --> O4["SSE/WS Connections"]
O --> O5["Active Users & Generation Jobs"]
PK --> PK1["Timeseries: Persona Throughput"]
PK --> PK2["Timeseries: Persona Latency (p95)"]
PK --> PK3["Timeseries: Persona Success Rate"]
```

**Diagram sources**
- [pipeline.json:101-426](file://backend/docker/grafana/dashboards/pipeline.json#L101-L426)
- [scholarform-overview.json:39-202](file://backend/ops/grafana/dashboards/scholarform-overview.json#L39-L202)
- [scholarform-persona-kpis.json:20-105](file://backend/ops/grafana/dashboards/scholarform-persona-kpis.json#L20-L105)

**Section sources**
- [pipeline.json:1-448](file://backend/docker/grafana/dashboards/pipeline.json#L1-L448)
- [scholarform-overview.json:1-239](file://backend/ops/grafana/dashboards/scholarform-overview.json#L1-L239)
- [scholarform-persona-kpis.json:1-142](file://backend/ops/grafana/dashboards/scholarform-persona-kpis.json#L1-L142)

### Model Metrics Persistence and Summaries
- Records model usage, latency, success/failure, and optional quality scores
- Asynchronously persists to Supabase; disables persistence if table not found
- Provides summaries and comparisons for model performance and fallback rates

```mermaid
flowchart TD
Call(["record_call(model, success, latency, quality)"]) --> Inc["Increment counters"]
Inc --> Lat["Update total/avg latency"]
Lat --> QS{"Quality score present?"}
QS --> |Yes| AddQS["Append to quality_scores"]
QS --> |No| SkipQS["Skip"]
AddQS --> Persist["Async persist to Supabase"]
SkipQS --> Persist
Persist --> Done(["Done"])
```

**Diagram sources**
- [model_metrics.py:60-137](file://backend/app/services/model_metrics.py#L60-L137)

**Section sources**
- [model_metrics.py:23-181](file://backend/app/services/model_metrics.py#L23-L181)

### Agent vs Legacy Performance Tracking
- Tracks processing runs, tool usage, retries, and quality metrics
- Stores metrics in JSONL and maintains a summary with speed, quality, and reliability comparisons

**Section sources**
- [metrics.py:15-260](file://backend/app/pipeline/agents/metrics.py#L15-L260)

### Queue Depth Metrics and Periodic Updates
- Periodically reads Redis queue lengths and updates Celery queue depth metrics
- Runs on a background task during app lifespan

**Section sources**
- [main.py:117-147](file://backend/app/main.py#L117-L147)

## Dependency Analysis
Key dependencies and relationships:
- FastAPI instrumentation exposes /metrics
- Prometheus scrapes the backend target defined in prometheus.yml
- Grafana queries Prometheus for dashboards (including new persona KPI dashboard)
- Enhanced Sentry error filtering prevents cancellation events from reaching monitoring
- Graceful degradation ensures system continues without Sentry when SDK unavailable
- **New**: V1 metrics router consolidates all metrics endpoints with unified structure
- **New**: Persona KPI recording integrates with v1 router helper functions
- Metrics router depends on Supabase client for DB health and counts
- Health/Readiness services depend on external systems (DB, LLM providers, AI models)
- Model metrics persistence depends on Supabase client and runs in background threads
- Frontend Sentry configurations provide comprehensive error tracking across environments

```mermaid
graph TB
M["main.py<br/>Instrumentator /metrics<br/>_sentry_before_send<br/>Graceful Degradation"] --> PMW["prometheus_metrics.py<br/>MetricsManager + Persona KPIs"]
M --> HR["health_checks.py<br/>/health & /ready"]
M --> V1R["v1/metrics.py<br/>Unified Metrics Router"]
M --> SF["Sentry Filtering<br/>Cancellation Events"]
M --> GD["Graceful Degradation<br/>SENTRY_AVAILABLE"]
PMW --> PR["Prometheus"]
V1R --> DB["Supabase Client"]
HR --> EXT["External Services"]
PMW --> SYS["System Metrics"]
PMW --> PK["Persona KPIs"]
SF --> MON["Monitoring Accuracy"]
GD --> RES["System Resilience"]
FC["Frontend Sentry<br/>Client/Server/Edge"] --> MON
PK --> GDASH["Grafana Persona KPI Dashboard"]
```

**Diagram sources**
- [main.py:273-274](file://backend/app/main.py#L273-L274)
- [prometheus_metrics.py:144-300](file://backend/app/middleware/prometheus_metrics.py#L144-L300)
- [metrics.py:24-248](file://backend/app/routers/v1/metrics.py#L24-L248)
- [health_checks.py:85-127](file://backend/app/services/health_checks.py#L85-L127)
- [main.py:45-106](file://backend/app/main.py#L45-L106)
- [sentry.client.config.js:1-20](file://frontend/sentry.client.config.js#L1-L20)
- [sentry.server.config.js:1-12](file://frontend/sentry.server.config.js#L1-L12)
- [sentry.edge.config.js:1-11](file://frontend/sentry.edge.config.js#L1-L11)
- [scholarform-persona-kpis.json:1-142](file://backend/ops/grafana/dashboards/scholarform-persona-kpis.json#L1-L142)

**Section sources**
- [main.py:273-274](file://backend/app/main.py#L273-L274)
- [prometheus_metrics.py:144-300](file://backend/app/middleware/prometheus_metrics.py#L144-L300)
- [metrics.py:24-248](file://backend/app/routers/v1/metrics.py#L24-L248)
- [health_checks.py:85-127](file://backend/app/services/health_checks.py#L85-L127)
- [main.py:45-106](file://backend/app/main.py#L45-L106)
- [sentry.client.config.js:1-20](file://frontend/sentry.client.config.js#L1-L20)
- [sentry.server.config.js:1-12](file://frontend/sentry.server.config.js#L1-L12)
- [sentry.edge.config.js:1-11](file://frontend/sentry.edge.config.js#L1-L11)
- [scholarform-persona-kpis.json:1-142](file://backend/ops/grafana/dashboards/scholarform-persona-kpis.json#L1-L142)

## Performance Considerations
- Scraping cadence and intervals:
  - Prometheus scrape interval configured to 5s for the backend job
  - Global evaluation interval at 15s
- Metric cardinality:
  - Use label selectors and bucket configurations judiciously to avoid excessive series
  - **New**: Persona KPIs add persona and operation dimensions but use sanitized labels to control cardinality
- Background persistence:
  - Model metrics persistence runs in a background thread to avoid blocking the pipeline
- Queue depth updates:
  - Periodic updates reduce overhead while keeping queue metrics fresh
- Caching:
  - Health and readiness payloads are cached with TTLs to reduce repeated checks
- Error filtering efficiency:
  - Sentry filtering reduces processing overhead by preventing cancellation events from being logged
- Graceful degradation performance:
  - Sentry SDK availability checks add minimal overhead during initialization
  - Frontend Sentry configurations are conditional to avoid unnecessary initialization
- **New**: Persona KPI recording overhead:
  - Minimal performance impact with try/except blocks around persona KPI recording
  - Automatic persona resolution uses simple string matching for efficiency

**Section sources**
- [prometheus.yml:5-16](file://backend/docker/prometheus/prometheus.yml#L5-L16)
- [model_metrics.py:101-137](file://backend/app/services/model_metrics.py#L101-L137)
- [main.py:138-147](file://backend/app/main.py#L138-L147)
- [health_checks.py:195-226](file://backend/app/services/health_checks.py#L195-L226)
- [main.py:45-106](file://backend/app/main.py#L45-L106)
- [_helpers.py:54-68](file://backend/app/routers/v1/_helpers.py#L54-L68)

## Troubleshooting Guide
Common issues and resolutions:
- No metrics in Grafana:
  - Verify Prometheus scrape job target matches backend address and port
  - Confirm /metrics endpoint is reachable and returns text/plain
  - **New**: Check persona KPI dashboard exists and references persona_events_total and persona_operation_duration_seconds metrics
- Missing Supabase table for model metrics:
  - Persistence disables itself after detecting missing table; ensure table exists or adjust expectations
- Health/Readiness degraded:
  - Check DB connectivity, LLM provider availability, and AI model loading status
- High error rate or latency spikes:
  - Inspect pipeline P95 duration and step averages; correlate with queue depths and LLM cache hit rates
- Real-time connection churn:
  - Monitor SSE/WS reconnect rates and active connections to detect client-side instability
- **Sentry error filtering issues**:
  - **Updated** Verify that cancellation events (asyncio.CancelledError, KeyboardInterrupt) are properly filtered out
  - Check _sentry_before_send function configuration in main.py
  - Ensure legitimate errors are still being reported while cancellations are suppressed
  - Review Sentry dashboard to confirm reduced noise from intentional cancellations
- **Sentry SDK availability issues**:
  - **Updated** Check SENTRY_AVAILABLE flag during application startup
  - Verify sentry_sdk import succeeds without ImportError
  - Ensure graceful degradation logs indicate "Sentry SDK not installed. Skipping Sentry initialization."
  - Confirm application continues operating normally without error reporting
- **Frontend Sentry configuration issues**:
  - **Updated** Verify NEXT_PUBLIC_SENTRY_DSN environment variable is set
  - Check client/server/edge configurations initialize successfully
  - Ensure replay integration is properly configured for client-side error analysis
- **Graceful degradation testing**:
  - **Updated** Test graceful degradation patterns in database connection failures
  - Verify LLM validator provides error_return_value instead of crashing pipeline
  - Confirm system stability under various error conditions
- **Persona KPI tracking issues**:
  - **New** Verify persona resolution works correctly for different API paths
  - Check that persona_events_total and persona_operation_duration_seconds metrics are being recorded
  - Ensure automatic KPI recording occurs in v1 router operations
  - Validate persona KPI dashboard queries return expected results
- **V1 metrics router issues**:
  - **New** Verify /api/v1/metrics endpoints are properly routed through v1 router
  - Check authentication requirements for admin-only endpoints
  - Ensure frontend error logging endpoint properly increments tool usage metrics

**Section sources**
- [prometheus.yml:5-16](file://backend/docker/prometheus/prometheus.yml#L5-L16)
- [model_metrics.py:123-135](file://backend/app/services/model_metrics.py#L123-L135)
- [health_checks.py:85-127](file://backend/app/services/health_checks.py#L85-L127)
- [scholarform-overview.json:41-202](file://backend/ops/grafana/dashboards/scholarform-overview.json#L41-L202)
- [main.py:45-106](file://backend/app/main.py#L45-L106)
- [test_database.py:25-48](file://backend/tests/test_database.py#L25-L48)
- [llm_validator.py:116-118](file://backend/app/pipeline/safety/llm_validator.py#L116-L118)
- [test_persona_kpi_dashboard.py:6-14](file://backend/tests/test_persona_kpi_dashboard.py#L6-L14)
- [metrics.py:24-248](file://backend/app/routers/v1/metrics.py#L24-L248)

## Conclusion
The monitoring and metrics system provides comprehensive observability for the manuscript formatter pipeline. It combines Prometheus instrumentation, custom metrics, health/readiness endpoints, and Grafana dashboards. Enhanced Sentry error filtering with cancellation event suppression improves error reporting accuracy by reducing noise from intentional cancellations. Graceful degradation ensures system stability when Sentry SDK is unavailable. Comprehensive frontend Sentry integration provides error tracking across client, server, and edge environments. Optional Supabase persistence enables long-term analysis of model performance. **New persona-based KPI tracking automatically monitors all API operations with intelligent persona categorization, providing valuable insights into user behavior patterns. The consolidated v1 metrics router offers a unified interface for all monitoring endpoints. With proper alerting and capacity planning aligned to queue depths, LLM usage, and persona analytics, the system supports reliable production operations.**

## Appendices

### Enhanced Metrics Exposure Endpoints
**Updated**: V1 router structure:
- /api/v1/metrics/db: Database health and document count (admin-only)
- /api/v1/metrics/log-error: Frontend error logging with automatic tool usage tracking
- /api/v1/metrics/health: Aggregated health status
- /api/v1/metrics/dashboard: Live model and A/B test summaries
- /api/v1/metrics/enhancements: Enhancement capability profile
- /api/v1/metrics/vllm-readiness: vLLM adoption readiness monitoring
- /metrics: Prometheus scrape endpoint

**Section sources**
- [prometheus_metrics.py:135-142](file://backend/app/middleware/prometheus_metrics.py#L135-L142)
- [metrics.py:24-248](file://backend/app/routers/v1/metrics.py#L24-L248)

### Enhanced Custom Metric Definitions
- Pipeline: requests_total, pipeline_duration_seconds, pipeline_step_duration_seconds
- Agent: agent_tools_usage_total, agent_llm_tokens_total, agent_retries_total
- LLM: llm_failures_total, llm_ttft_seconds, llm_cache_hits_total, llm_cache_misses_total, llm_request_duration_seconds
- System: active_processing_jobs, celery_queue_depth, sse/ws connections, clamav_scan_duration_seconds, active_users
- **New**: Persona KPIs: persona_events_total (persona, event, outcome), persona_operation_duration_seconds (persona, operation)

**Section sources**
- [prometheus_metrics.py:15-167](file://backend/app/middleware/prometheus_metrics.py#L15-L167)

### Enhanced Alerting Strategies
- Suggested alerts:
  - High pipeline failure rate or sustained P95 latency increases
  - Low LLM cache hit rate or frequent failures
  - Elevated error rate from HTTP instrumentor
  - Rising queue depths without corresponding worker throughput
  - Declining active users or generation jobs
  - **Enhanced Sentry monitoring**: Reduced error volume due to cancellation filtering, allowing focus on genuine issues
  - **Graceful degradation monitoring**: Track Sentry SDK availability and fallback behavior
  - **New**: Persona KPI monitoring: persona success rate drops, persona latency increases, persona throughput anomalies
  - **New**: vLLM adoption monitoring: readiness status changes, provider performance degradation

### Log Aggregation and Distributed Tracing
- Structured logging can be enabled via settings for production environments
- **Enhanced Sentry integration**:
  - Backend: _sentry_before_send filters cancellation events and keyboard interrupts
  - Frontend: Separate client/server configurations for comprehensive coverage
  - Graceful degradation ensures system continues without error reporting when SDK unavailable
  - Request IDs are attached to responses for correlation across services
  - Replay integration for frontend error analysis
  - Edge function monitoring for serverless components
- **New**: Persona KPI correlation: automatic persona tagging for all monitored operations

**Section sources**
- [settings.py:26-28](file://backend/app/config/settings.py#L26-L28)
- [main.py:40-59](file://backend/app/main.py#L40-L59)
- [monitoring.py:17-50](file://backend/app/middleware/monitoring.py#L17-L50)
- [main.py:45-106](file://backend/app/main.py#L45-L106)
- [sentry.client.config.js:1-20](file://frontend/sentry.client.config.js#L1-L20)
- [sentry.server.config.js:1-12](file://frontend/sentry.server.config.js#L1-L12)
- [sentry.edge.config.js:1-11](file://frontend/sentry.edge.config.js#L1-L11)

### Enhanced Metric Retention and Capacity Planning
- Retention policy:
  - File cleanup scheduled periodically based on settings; configure retention_days accordingly
- Capacity planning insights:
  - Monitor queue_depth and active_processing_jobs to size Celery workers
  - Track LLM tokens_total and cache hit rates to right-size provider resources
  - Observe pipeline step durations to optimize slowest stages
  - **Enhanced error monitoring**: Reduced error volume allows better focus on genuine performance issues
  - **Graceful degradation monitoring**: Track system resilience under various failure conditions
  - **New**: Persona KPI insights: identify high-value personas, optimize for top-performing persona categories
  - **New**: vLLM adoption metrics: monitor readiness progress and performance improvements

**Section sources**
- [settings.py:128-131](file://backend/app/config/settings.py#L128-L131)
- [main.py:106-114](file://backend/app/main.py#L106-L114)
- [main.py:138-147](file://backend/app/main.py#L138-L147)
- [scholarform-overview.json:88-125](file://backend/ops/grafana/dashboards/scholarform-overview.json#L88-L125)
- [scholarform-persona-kpis.json:88-105](file://backend/ops/grafana/dashboards/scholarform-persona-kpis.json#L88-L105)

### Enhanced Production Monitoring Best Practices
- Enforce HTTPS and HSTS headers in production
- Configure CORS origins carefully
- Use readiness probes to gate traffic until dependencies are ready
- Set appropriate scrape intervals and alert thresholds
- Back up and monitor dashboards and recording rules
- **Implement enhanced error filtering**: Configure _sentry_before_send for optimal error reporting
- **Monitor cancellation patterns**: Track cancellation events separately from other errors for system health insights
- **Test graceful degradation**: Verify system stability under Sentry SDK unavailability and other failure scenarios
- **Frontend monitoring**: Implement comprehensive Sentry configuration across client, server, and edge environments
- **Resilient error handling**: Use graceful degradation patterns for all critical dependencies
- **New**: Persona analytics monitoring: establish baseline persona success rates and latency targets
- **New**: vLLM adoption tracking: monitor migration progress and performance benefits
- **New**: V1 router validation: ensure all metrics endpoints are properly exposed and accessible

**Section sources**
- [main.py:303-313](file://backend/app/main.py#L303-L313)
- [settings.py:76-82](file://backend/app/config/settings.py#L76-L82)
- [health_checks.py:130-192](file://backend/app/services/health_checks.py#L130-L192)
- [main.py:45-106](file://backend/app/main.py#L45-L106)
- [test_database.py:25-48](file://backend/tests/test_database.py#L25-L48)
- [llm_validator.py:116-118](file://backend/app/pipeline/safety/llm_validator.py#L116-L118)
- [test_persona_kpi_dashboard.py:6-14](file://backend/tests/test_persona_kpi_dashboard.py#L6-L14)
- [metrics.py:24-248](file://backend/app/routers/v1/metrics.py#L24-L248)