# ScholarForm AI — Real-time Architecture

## 1. Overview

ScholarForm AI employs two complementary real-time paradigms:

| Paradigm | Protocol | Transport | Use Cases |
|----------|----------|-----------|-----------|
| **SSE** (Server-Sent Events) | HTTP long-lived stream | `sse-starlette` → `EventSourceResponse` → `ReadableStream` reader → React state | Job status updates, token-by-token AI generation, session pipeline events, synthesis progress |
| **WebSocket** | Bidirectional full-duplex | `ReconnectingWebSocket` (exponential backoff + jitter) → `websockets` (FastAPI) | Live preview collaborative rendering, real-time content analysis |

**Core invariant**: All real-time events flow through a single `RedisPubSub` broker, enabling multi-worker broadcasting. SSE endpoints are read-only subscriptions; WebSocket endpoints are bidirectional. A shared `RealtimeEvent` dataclass provides a uniform event shape across both paradigms.

---

## 2. SSE Architecture

### 2.1 Pipeline

```
                    ┌──────────────────────────────────────────────┐
                    │              Backend Process                 │
                    │                                              │
  AgentPipeline ──► │  make_event() ──► RedisPubSub.publish()      │
  DocumentGenerator │       │              (channel: "job:{id}"    │
  MultiDocSynth.    │       │               or "session:{id}")     │
                    │       ▼                                      │
                    │  Redis (or in-memory Queue fallback)         │
                    │       │                                      │
                    │       ▼                                      │
                    │  RedisPubSub.subscribe(channel)               │
                    │       │                                      │
                    │       ▼                                      │
                    │  async generator ──► sse_starlette            │
                    │  EventSourceResponse                          │
                    └──────┬───────────────────────────────────────┘
                           │  text/event-stream
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                     Frontend                                 │
│                                                              │
│  EventSource (native browser API)                            │
│       │                                                     │
│       ▼                                                     │
│  useSSEStream (base hook)                                    │
│       │                                                     │
│       ├── useGeneratorSessionStream (agent pipeline)         │
│       ├── useSessionEventStream (general session, synthesis) │
│       └── useSynthesisSessionStream (multi-doc synthesis)    │
│                                                              │
│  OR: ReadableStream reader (api.generation.js)               │
│       └── streamGenerationStatus(fetch-based, no EventSource) │
└──────────────────────────────────────────────────────────────┘
```

**Key detail**: Two distinct SSE transport mechanisms exist on the frontend:
- **`EventSource` API** (native browser, used by `useSSEStream` and all hooks) — preferred for session-based event streams.
- **`ReadableStream` reader** (used by `streamGenerationStatus` in `api.generation.js`) — manual fetch with `text/event-stream` `Accept` header, manual SSE frame parsing, necessary when auth headers must be injected (native `EventSource` does not support custom headers).

### 2.2 Event Data Model

All SSE events originate from the `RealtimeEvent` dataclass (`backend/app/realtime/events.py`):

```python
@dataclass
class RealtimeEvent:
    event_type: str                           # e.g. "connected", "stage_update", "token", "outline"
    job_id: Optional[str] = None              # populated for job-scoped streams
    session_id: Optional[str] = None           # populated for session-scoped streams
    request_id: Optional[str] = None           # auto-inherited from request context
    stage: Optional[str] = None                # pipeline stage name
    progress: Optional[int] = None             # 0-100 integer
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    payload: Dict[str, Any] = field(default_factory=dict)  # arbitrary event-specific data
```

The `make_event()` factory function auto-injects the current `request_id` from logging context and serializes `timestamp` to ISO 8601.

### 2.3 SSE Wire Format

Each SSE frame conforms to the standard `text/event-stream` format:

```
event: stage_update
data: {"event_type":"stage_update","session_id":"abc...","stage":"writing","progress":50,"payload":{"content":"..."},"timestamp":"2026-07-16T12:00:00Z"}
```

The `event:` line maps to `RealtimeEvent.event_type`. The `data:` line is the full serialized `RealtimeEvent` dict.

### 2.4 SSE Endpoints

| Endpoint | Path | Stream Scope | Auth | Purpose |
|----------|------|-------------|------|---------|
| **Stream job events** | `GET /api/v1/stream/{jobId}` | `job:{jobId}` channel | `Depends(get_current_user)` | General-purpose job status stream. Used by `streamGenerationStatus()` for generation polling fallback. |
| **Generator session events** | `GET /api/v1/generator/sessions/{sessionId}/events` | `session:{sessionId}` channel | Ownership check via `verify_session_ownership` | Agent pipeline events: stage transitions, token chunks, outline proposals, completion. Used by `useGeneratorSessionStream`. |
| **Synthesis session events** | `GET /api/v1/synthesis/sessions/{sessionId}/events` | `session:{sessionId}` channel | Ownership check via `verify_session_ownership` | Multi-doc synthesis pipeline events: stage_start, stage_complete, synthesis_complete. Used by `useSynthesisSessionStream`. |
| **AI suggestion stream** | `GET /api/v1/preview/{sessionId}/ai-suggest` | N/A (inline generator) | `Query` params only | Streaming AI writing suggestions for the live preview editor. Uses inline `event_generator()`, not pub/sub. Events: `status`, `suggestion` (chunked), `done`, `error`. |

### 2.5 SSE Event Types

#### Generator/Synthesis Pipeline Events (`channel: session:{id}`)

| Event Name | Direction | Payload | Emitted By |
|-----------|-----------|---------|------------|
| `connected` | Server → Client | `{message: "Connected to session {id}"}` | `event_generator()` on connection open |
| `stage_update` | Server → Client | `{stage, progress, message, ...extra}` | `AgentPipeline._emit_sse()` at each pipeline stage |
| `stage_start` | Server → Client | `{name, progress, ...}` | Synthesis pipeline stage entrance |
| `stage_complete` | Server → Client | `{name, progress, status:"done", ...}` | Synthesis pipeline stage completion |
| `token` | Server → Client | `{content: "chunk text", stage, progress}` | `AgentPipeline._stream_chunks()` for token-by-token streaming |
| `outline` | Server → Client | `{sections: [...], ...}` | Agent pipeline outline generation phase |
| `complete` | Server → Client | `{session_id, status:"done", doc_path, ...}` | Pipeline completion |
| `synthesis_complete` | Server → Client | Full document object | Multi-doc synthesis completion |
| `error` | Server → Client | `{error, message, ...}` | Pipeline failure |

#### Stream Job Events (`channel: job:{id}`)

| Event Name | Direction | Payload | Emitted By |
|-----------|-----------|---------|------------|
| `connected` | Server → Client | `{message: "Connected to stream for job {id}"}` | `event_generator()` on connection open |
| `status_update` | Server → Client | `{phase, status, message, progress, stage, ...}` | `DocumentGenerator._emit()` at each generation phase |

#### AI Suggestion Events (inline generator, no pub/sub)

| Event Name | Direction | Payload |
|-----------|-----------|---------|
| `status` | Server → Client | `{state: "started", sessionId, request_id}` |
| `suggestion` | Server → Client | `{content: "chunked text", request_id}` (multiple chunks) |
| `done` | Server → Client | `{done: true, latencyMs, model, tier, request_id}` |
| `error` | Server → Client | `{error: "...", request_id}` |

### 2.6 SSE Connection Lifecycle

```
Client                          Server
  │                               │
  │── GET /api/v1/stream/{id} ──► │  (or /generator/sessions/{id}/events)
  │                               │
  │◄── event: connected ──────────│  yield {"event": "connected", "data": ...}
  │                               │
  │◄── event: stage_update ───────│  pub/sub message received
  │◄── event: token ──────────────│
  │◄── event: complete ───────────│
  │                               │
  │── [browser closes/error] ────►│
  │                               │  request.is_disconnected() → True
  │                               │  MetricsManager.sse_connection_closed()
  │                               │  generator exits → stream ends
```

Each SSE endpoint calls `MetricsManager.sse_connection_open()` on start and `MetricsManager.sse_connection_closed()` on teardown, enabling Prometheus monitoring of concurrent SSE connections.

---

## 3. WebSocket Architecture

### 3.1 Connection Lifecycle with ReconnectingWebSocket

`ReconnectingWebSocket` (`frontend/src/lib/ReconnectingWebSocket.js`) wraps the native `WebSocket` with automatic reconnection using exponential backoff with jitter.

```
Client                                      Server
  │                                           │
  │── new WebSocket(url) ──────────────────►  │
  │                                           │  websocket.accept()
  │◄── onopen ────────────────────────────────│
  │    reconnectAttempt = 0                   │
  │    isConnected = true                     │
  │                                           │
  │── send(JSON.stringify(payload)) ─────────►│  receive_text() → parse → render
  │                                           │  publish to "preview:{sessionId}" channel
  │◄── onmessage({html, warnings, ...}) ──────│  _forward_updates() forwards pub/sub
  │                                           │
  │── [connection lost]                       │
  │    isConnected = false                    │
  │    scheduleReconnect()                    │
  │      │                                    │
  │      ├── computeReconnectDelay(attempt)   │
  │      │   expDelay = 1000 × 2^(attempt-1)  │
  │      │   jitter = delay × [-0.3, +0.3]    │
  │      │   capped at maxDelay=30000         │
  │      │                                    │
  │      └── setTimeout → open() ────────────►│  new WebSocket connection
  │                                           │
  │── close() ───────────────────────────────►│
  │    forcedClose = true                     │
  │    clearTimeout + ws.close()              │
```

#### Reconnection parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `initialDelay` | 1000 ms | First retry delay |
| `maxDelay` | 30000 ms | Ceiling for exponential backoff |
| `factor` | 2 | Exponential growth factor |
| `jitter` | 0.3 | Random ±30% jitter to avoid thundering herd |
| `maxRetries` | `Infinity` (default), 5 (synthesis) | Maximum reconnection attempts |

#### Reconnect delay formula

```javascript
expDelay = initialDelay * factor^(attempt - 1)
baseDelay = min(expDelay, maxDelay)
minDelay = baseDelay * (1 - jitter)
maxDelay = baseDelay * (1 + jitter)
delay = min(maxDelay, max(0, minDelay + random * (maxDelay - minDelay)))
```

Resulting sequence (approximate): 1000ms, 1400-2600ms, 2800-5200ms, 5600-10400ms, 11200-20800ms, 20000-30000ms (capped).

### 3.2 Live Preview Protocol

#### WebSocket Endpoint

**`GET /api/v1/ws/preview/{sessionId}`** (upgraded to WebSocket)

#### Client → Server Message Format

```json
{
  "content": "Full document text or HTML content",
  "templateId": "ieee",               // Template slug (or "template_id")
  "cursor": null,                      // Cursor position (reserved)
  "checksum": "a1b2c3d4",             // simpleHash(content) — lightweight client-side hash
  "seq": 42                            // Monotonic message sequence number
}
```

#### Server → Client Message Format

```json
{
  "html": "<div class='manuscript'>...rendered HTML...</div>",
  "latencyMs": 45.2,
  "warnings": ["Unsupported element: <table>"],
  "version": "a1b2c3d4",              // SHA-256 prefix of rendered HTML (or client checksum)
  "seq": 42                            // Echoed from client for ordering
}
```

#### Heartbeat Protocol

The server sends a keepalive ping every 20 seconds:

```json
{"type": "ping", "timestamp": 1721145600.123}
```

No client pong is required; the heartbeat exists solely to keep intermediate proxies from closing idle connections.

#### Debounce Strategy

Client `sendContent()` in `useLivePreviewSocket` implements a 200ms debounce:

```
content change → clearTimeout(200ms) → setTimeout → send payload
                                                    │
                              if diff > 1000 chars: set isAnalyzing = true immediately
                                                    │
                              if WebSocket not OPEN: store in pendingPayloadRef
                                                     replay on next onopen
```

This ensures rapid edits do not flood the server while maintaining responsiveness. During reconnection, the latest pending payload is automatically replayed when the socket reopens.

#### Conflict Resolution

There is one writer (the current user) per session. No OT/CRDT is needed. The `seq` field provides at-most-once ordering: the server echoes the client's sequence number, and the client can detect out-of-order or duplicate responses. The `checksum` field enables the client to skip redundant re-renders if the content hash matches the last rendered version.

### 3.3 HTTP Fallback

When the WebSocket is disconnected and no pending reconnect is desired, the frontend falls back to an HTTP POST:

**`POST /api/v1/preview/live`**

```json
{
  "content": "...",
  "templateId": "ieee"
}
```

Returns:
```json
{
  "html": "...",
  "latencyMs": 45.2,
  "warnings": []
}
```

This endpoint is exposed via `getPreviewHtml()` in `api.preview.v1.js`.

---

## 4. Pub/Sub System

### 4.1 Architecture

The `RedisPubSub` class (`backend/app/realtime/pubsub.py`) abstracts Redis pub/sub with transparent in-memory fallback:

```
         ┌─────────────────────┐
         │   RedisPubSub        │
         │   (singleton-per-    │
         │    asyncio-loop)     │
         └────────┬────────────┘
                  │
        ┌─────────┴──────────┐
        ▼                    ▼
┌──────────────┐   ┌────────────────┐
│   Redis       │   │  In-memory      │
│  (aioredis)   │   │  asyncio.Queue  │
│               │   │  (fallback)     │
│  channel:     │   │                 │
│  "job:{id}"   │   │  channel → set  │
│  "session:{id}"│   │  of Queues      │
│  "preview:{id}"│   │                 │
└──────────────┘   └────────────────┘
```

**Design choices:**

- **Per-loop Redis client**: One `aioredis` client per asyncio event loop, tracked in `_redis_by_loop` keyed by `id(loop)`. This prevents "attached to a different loop" errors in multi-loop environments (e.g., Celery workers with custom event loops).
- **Lazy connection**: Redis connection is established on first `publish` or `subscribe` call. `ping()` validates connectivity.
- **Graceful degradation**: If Redis is unavailable (`REDIS_ENABLED=false`, `aioredis` import fails, connection/publish fails), `_force_fallback = True` silences further warnings and all pub/sub operations use `asyncio.Queue` in memory.
- **Thread-safe publish**: `publish()` is safe to call from any thread — it uses `asyncio.Lock` and `loop.create_task()`/`asyncio.run()` as needed.

### 4.2 Channel Namespace Convention

| Channel Pattern | Used By | Purpose |
|----------------|---------|---------|
| `job:{job_id}` | `stream.py` (emit_event), `DocumentGenerator._emit()` | Job-level status broadcasts |
| `session:{session_id}` | `AgentPipeline._emit_sse()`, generator/synthesis event endpoints | Session-level pipeline stage updates |
| `preview:{session_id}` | `preview.py` (preview_ws WebSocket) | Live preview rendering updates |

### 4.3 Subscription Flow

```python
# Server-side subscription (in event_generator):
async for event in _pubsub.subscribe("session:abc-123"):
    yield {"event": event.get("event_type"), "data": json.dumps(event)}
```

```python
# Server-side publish:
await _pubsub.publish("session:abc-123", event_dict)
```

The `subscribe()` method is an `AsyncGenerator` — it yields messages until the generator is garbage collected or the client disconnects. Cleanup always calls `pubsub.unsubscribe()` and `pubsub.close()` (or `aclose()` for redis-py >= 4.6).

### 4.4 In-Memory Fallback Behavior

When Redis is unavailable:

```
publish("channel", event):
  for each Queue in _fallback_channels["channel"]:
      queue.put_nowait(event)      # drops if QueueFull

subscribe("channel"):
  queue = asyncio.Queue()
  _fallback_channels["channel"].add(queue)
  while True:
      event = await queue.get()
      yield event
```

Publishing to an in-memory channel fans out to all subscribed queues. If a queue is full (`QueueFull`), the event is silently dropped for that consumer. This fallback works within a single process only — multi-worker broadcasting requires Redis.

---

## 5. Real-time Hooks

### 5.1 `useSSEStream` (base hook)

**File**: `frontend/src/hooks/useSSEStream.js`

**Signature**:
```javascript
useSSEStream(sessionId, getEventsUrl, {
  maxRetries = Infinity,
  streamName = 'SSE',
  onMaxRetriesExceeded
}) → { eventSource, status, reconnectCount, setStatus }
```

**Behavior**:
- Creates a native `EventSource` with the URL returned by `getEventsUrl(sessionId)`. Attaches `?token=` query param from Supabase auth session.
- `status` transitions: `'idle'` → `'connecting'` → `'streaming'` (on first open) | `'reconnecting'` (on retry) → `'error'` (on failure).
- Implements exponential backoff reconnect on `onerror` with configurable `maxRetries` (default `Infinity`).
- On unmount: closes `EventSource`, clears reconnect timer.

**Reconnect formula** (inlined, not shared with WebSocket):
```javascript
const rawBackoff = maxRetries === Infinity
  ? Math.min(Math.pow(2, attempt - 1) * 1000, 30000)   // infinite: 1s, 2s, 4s, 8s, 16s, 30s...
  : Math.pow(2, attempt) * 1000;                         // finite: 2s, 4s, 8s, ...
```

### 5.2 `useGeneratorSessionStream`

**File**: `frontend/src/hooks/useGeneratorSessionStream.js`

**Signature**:
```javascript
useGeneratorSessionStream(sessionId, callbacks = {
  onStageChange, onToken, onOutline, onComplete, onError
}) → { status, stages, reconnectCount, latencyMs }
```

**Stream URL**: `${API_BASE_URL}/api/v1/generator/sessions/${id}/events`

**Behavior**:
- Wraps `useSSEStream` with `maxRetries: Infinity`, `streamName: 'GeneratorSession'`.
- Registers five named `EventSource` event listeners:
  - `connected` → measures connection latency (`latencyMs`), sets status to `'streaming'`.
  - `stage` → accumulates stage records (upsert by `name`), invokes `onStageChange`.
  - `token` → passes token content to `onToken` (handles both JSON and raw string payloads).
  - `outline` → passes outline data to `onOutline`.
  - `complete` → sets status `'done'`, invokes `onComplete`.
  - `error` → sets status `'error'`, invokes `onError`.

**State shape** (`stages`):
```javascript
[
  { name: "Generating outline", progress: 10, status: "in_progress" },
  { name: "Writing content", progress: 40, ... },
  { name: "Formatting", progress: 100, status: "done" }
]
```

### 5.3 `useSessionEventStream`

**File**: `frontend/src/hooks/useSessionEventStream.js`

**Signature**:
```javascript
useSessionEventStream(sessionId, getEventsUrl, streamName)
  → { stages, currentStage, progress, isComplete, error }
```

**Behavior**:
- Wraps `useSSEStream` with `maxRetries: 5` (finite retries). On exhaustion: sets `error` with user-visible message.
- Uses generic `eventSource.onmessage` (not named event listeners) — parses all incoming events as JSON stage objects.
- Tracks `progress` (0-100) from any message with a `progress` field.
- Sets `isComplete = true` when `progress >= 100`, `status === 'done'`, or `name === 'Template Rendering'` with `status === 'done'`.
- Sets `error` when `status === 'error'`.

### 5.4 `useSynthesisSessionStream`

**File**: `frontend/src/hooks/useSynthesisSessionStream.js`

**Signature**:
```javascript
useSynthesisSessionStream(sessionId, callbacks = {
  onConnected, onStageStart, onStageComplete, onSynthesisComplete, onError
}) → { status, stages, reconnectCount, latencyMs }
```

**Stream URL**: `${API_BASE_URL}/api/v1/synthesis/sessions/${id}/events` (via `getSynthesisEventsEndpoint()`)

**Behavior**:
- Wraps `useSSEStream` with `maxRetries: 5`, `streamName: 'SynthesisSession'`.
- Registers four named event listeners plus one generic listener:
  - `connected` → latency measurement, invokes `onConnected`.
  - `stage_start` → upserts stage with `status: 'in_progress'`, invokes `onStageStart`.
  - `stage_complete` → marks stage `status: 'done'`, invokes `onStageComplete`.
  - `synthesis_complete` → sets status `'done'`, invokes `onSynthesisComplete` with full document object.
  - `error` → sets status `'error'`, invokes `onError`.

### 5.5 `useLivePreviewSocket`

**File**: `frontend/src/hooks/useLivePreviewSocket.js`

**Signature**:
```javascript
useLivePreviewSocket(sessionId)
  → { html, latencyMs, warnings, isConnected, isReconnecting, reconnectAttempt, isAnalyzing, sendContent }
```

**Behavior**:
- Creates `ReconnectingWebSocket` to `ws://{host}/api/v1/ws/preview/{sessionId}`.
- `onopen` → sets `isConnected=true`, `isReconnecting=false`. Replays `pendingPayloadRef` if any queued during downtime.
- `onmessage` → parses JSON, updates `html`, `warnings`, computes `latencyMs` from `sentAtRef`, sets `isAnalyzing=false`.
- `onclose/onerror` → sets `isConnected=false`.
- `onreconnect` → sets `isReconnecting=true`, increments `reconnectAttempt`.
- `sendContent(content, templateId)`:
  - 200ms debounce via `setTimeout`.
  - If `abs(content.length - lastContentRef.length) > 1000`: immediately sets `isAnalyzing=true`.
  - Builds payload with `content`, `templateId`, `cursor`, `checksum` (via `simpleHash`), `seq`.
  - Stores payload in `pendingPayloadRef` for replay on reconnect.
  - If socket is `OPEN`: sends immediately sets `sentAtRef` for latency timing.

---

## 6. Error Handling & Resiliency

### 6.1 Reconnection Strategy

| Component | Strategy | Max Retries | Approach |
|-----------|----------|-------------|----------|
| `useSSEStream` (native EventSource) | Exponential backoff (no jitter) | Configurable (default `Infinity`) | Reconnect via `setTimeout` on `onerror` |
| `ReconnectingWebSocket` | Exponential backoff + 30% jitter | Configurable (default `Infinity`) | `scheduleReconnect()` on `onclose` (if not forced) |
| `useSessionEventStream` | Wraps `useSSEStream` | 5 | Shows error message on exhaustion: "Lost connection to synthesis stream. Please refresh." |
| `useSynthesisSessionStream` | Wraps `useSSEStream` | 5 | Silent retry, then `onError` callback |
| `streamGenerationStatus` (ReadableStream) | N/A (abort controller) | N/A | Manual retry via `fetchWithRetry` on initial connection; stream drop triggers `onError` |

### 6.2 Timeout Handling

- **Heartbeat (WebSocket)**: Server sends `{"type": "ping"}` every 20s. No client timeout — the heartbeat keeps the connection alive through proxies.
- **SSE idle timeout**: No explicit server-side timeout. Client `EventSource` automatically reconnects on any connection drop.
- **Debounce (WebSocket send)**: 200ms debounce on `sendContent`. Prevents flood during rapid typing.
- **Pending payload replay**: WebSocket messages queued in `pendingPayloadRef` during disconnection are replayed on next `onopen`, ensuring zero update loss.

### 6.3 Fallback to HTTP Polling

Two fallback paths exist:

1. **`getPreviewHtml()` (HTTP POST)**: Called when WebSocket is not connected and the consumer needs a one-shot preview. Returns `{html, latencyMs, warnings}`.

2. **`getGenerationStatus()` (HTTP GET)**: Periodic polling (`/api/v1/generator/sessions/{id}`) provides a stateless fallback for generation status when SSE is not used. Returns current `status`, `stage`, `progress`, `message`, `error`, `outline`.

### 6.4 Edge Case Handling

| Scenario | Mechanism |
|----------|-----------|
| **SSE connection lost mid-generation** | `EventSource` auto-reconnects. The `session:{id}` pub/sub channel persists — missed events are lost, but the latest state is available via HTTP GET (`getGenerationStatus`). |
| **WebSocket drops during content analysis** | `pendingPayloadRef` stores the last unsent payload. Replayed on reconnect. `isAnalyzing` remains `true` until response arrives. |
| **Client navigates away mid-stream** | `useEffect` cleanup closes `EventSource`/`WebSocket`. Backend detects disconnect via `request.is_disconnected()` (SSE) or `WebSocketDisconnect` exception. |
| **Redis goes down mid-session** | `RedisPubSub._force_fallback = true`. In-memory `asyncio.Queue` takes over. Single-process only — multi-worker broadcasting lost until Redis recovers. |
| **Server crashes during generation** | Active SSE/WS connections drop. Client reconnects to new worker instance. Pipeline state persisted in Supabase (`generator_sessions` table) survives restart. |
| **Supabase unavailable** | `DocumentGenerator` falls back to `_volatile_sessions` dict. Events still flow via pub/sub. State lost on process restart. |

---

## 7. Monitoring

### 7.1 Prometheus Metrics

All real-time connections are tracked via `MetricsManager` (Prometheus counters):

| Metric | Instrumentation Point | Labels |
|--------|----------------------|--------|
| `sse_connection_open()` | `event_generator()` start in all SSE endpoints | (none) |
| `sse_connection_closed()` | `event_generator()` `finally` block | (none) |
| `ws_connection_open()` | `preview_ws()` after `websocket.accept()` | (none) |
| `ws_connection_closed()` | `preview_ws()` `finally` block | (none) |

These metrics enable dashboards for:
- Current concurrent SSE and WebSocket connection counts
- Connection churn rate (open/close per second)
- Anomaly detection (e.g., sudden drop in connections indicating network issues)

### 7.2 Logging

All real-time events carry structured logging context via `log_extra()`:

```python
logger.info("Client disconnected from stream %s", job_id, extra=log_extra(job_id=job_id))
```

Log context includes:
- `job_id` / `session_id` (scoped to the stream)
- `request_id` (propagated from the initial HTTP request via `get_request_id_context()`)
- `stage`, `progress` (for SSE event emission)

### 7.3 Connection Health Indicators

| Indicator | Source | Expected Range |
|-----------|--------|----------------|
| SSE connection latency (`latencyMs`) | `useGeneratorSessionStream`, `useSynthesisSessionStream` | < 500ms |
| WebSocket round-trip latency (`latencyMs`) | `useLivePreviewSocket` (time from `sentAtRef` to response) | < 200ms |
| WebSocket `reconnectAttempt` | `useLivePreviewSocket` | 0 in steady state |
| SSE `reconnectCount` | All SSE hooks | 0 in steady state |
| WS `isReconnecting` | `useLivePreviewSocket` | `false` in steady state |
| WS `isAnalyzing` duration | `useLivePreviewSocket` | < 5s typical |

### 7.4 Key Performance Characteristics

| Aspect | SSE | WebSocket |
|--------|-----|-----------|
| Connection overhead | 1 HTTP round trip | 1 HTTP upgrade round trip |
| Message overhead | ~100 bytes/event (SSE framing) | ~20 bytes/frame (WebSocket framing) |
| Max concurrent connections (single node) | 6 per domain (browser limit per host) | 255+ (no browser limit) |
| Bidirectional | ❌ (server → client only) | ✅ (full duplex) |
| Automatic reconnection | Native `EventSource` | Custom `ReconnectingWebSocket` |
| Custom headers | ❌ (requires `ReadableStream` fallback) | ✅ (though not used in current impl) |
| Binary payloads | ❌ (text only) | ✅ (though not used) |

---

## 8. Data Flow Diagrams

### 8.1 Agent Pipeline Generation (SSE)

```
User                        Frontend                          Backend
 │                            │                                  │
 │── Click "Generate" ──────►│                                  │
 │                            │── POST /generator/sessions ─────►│  create session, dispatch
 │                            │◄── {session_id, status:"started"}│  background task
 │                            │                                  │
 │                            │── GET /generator/sessions/{id}/events ──►│  SSE connection
 │                            │◄── event: connected ──────────────│
 │                            │                                  │  AgentPipeline.run()
 │                            │◄── event: stage_update ──────────│  "Generating outline"
 │  progress bar updates ────│◄── event: outline ────────────────│  AgentPipeline outline phase
 │                            │◄── event: stage_update ──────────│  "Writing content"
 │                            │◄── event: token (chunked) ──────│  _stream_chunks()
 │  content appears live ────│◄── event: stage_update ──────────│  "Formatting"
 │                            │◄── event: complete ──────────────│  pipeline done
 │  "Download" button ───────│                                  │
 │                            │── GET /generator/sessions/{id}/download?format=docx ──►│
 │                            │◄── FileResponse (docx binary) ───│
```

### 8.2 Multi-Doc Synthesis (SSE)

```
User                        Frontend                          Backend
 │                            │                                  │
 │── Upload 2-6 files ──────►│                                  │
 │                            │── POST /generator/sessions ─────►│  multi_doc session
 │                            │◄── {session_id, status:"started"}│
 │                            │                                  │
 │                            │── GET /synthesis/sessions/{id}/events ──►│  SSE connection
 │                            │◄── event: connected ──────────────│
 │                            │◄── event: stage_start ───────────│  Parsing documents
 │                            │◄── event: stage_complete ────────│  Parsing done
 │                            │◄── event: stage_start ───────────│  Extracting structure
 │                            │◄── event: stage_complete ────────│
 │                            │◄── event: stage_start ───────────│  Normalizing styles
 │                            │◄── event: stage_complete ────────│
 │                            │◄── event: synthesis_complete ────│  Final document ready
```

### 8.3 Live Preview (WebSocket)

```
User Types                     Frontend                          Backend
 │                            │                                  │
 │                            │── WebSocket /ws/preview/{id} ───►│  accept + create forward_task
 │                            │◄── {type:"ping", timestamp} ─────│  every 20s heartbeat
 │                            │                                  │
 │── types "Hello World" ───►│                                  │
 │                            │── (200ms debounce)                │
 │                            │── send({content, templateId,     │
 │                            │       checksum, seq}) ──────────►│  render_preview()
 │                            │                                  │  publish to "preview:{id}"
 │                            │◄── message({html, latencyMs,     │  _forward_updates()
 │                            │       warnings, version, seq}) ──│
 │  live preview updates ────│                                  │
 │                            │                                  │
 │── [connection drops]       │                                  │
 │     isReconnecting=true    │                                  │
 │                            │── [exponential backoff + jitter] │
 │                            │── new WebSocket connection ─────►│
 │                            │◄── onopen ───────────────────────│
 │     isConnected=true       │                                  │
 │                            │── send(pendingPayload) ─────────►│  replay last unsent update
```

---

## 9. Code Map

| File | Role |
|------|------|
| `backend/app/realtime/events.py` | `RealtimeEvent` dataclass, `make_event()` factory |
| `backend/app/realtime/pubsub.py` | `RedisPubSub` — Redis + in-memory queue fallback |
| `backend/app/routers/v1/stream.py` | `GET /api/v1/stream/{jobId}` — job-level SSE, `emit_event()` helper |
| `backend/app/routers/v1/generator.py` | `GET /sessions/{id}/events` — generator session SSE |
| `backend/app/routers/v1/synthesis.py` | `GET /sessions/{id}/events` — synthesis session SSE |
| `backend/app/routers/preview.py` | `WS /api/v1/ws/preview/{id}` — live preview WebSocket; `POST /api/v1/preview/live` — HTTP fallback; `GET /preview/{id}/ai-suggest` — AI suggestion SSE |
| `backend/app/pipeline/generation/agent.py` | `_emit_sse()` and `_stream_chunks()` — pipeline event emission and token streaming |
| `backend/app/pipeline/generation/document_generator.py` | `_emit()` — job-level status emission via `stream.emit_event()` |
| `frontend/src/lib/ReconnectingWebSocket.js` | WebSocket wrapper with exponential backoff + jitter |
| `frontend/src/hooks/useSSEStream.js` | Base SSE hook wrapping native `EventSource` |
| `frontend/src/hooks/useGeneratorSessionStream.js` | Generator pipeline SSE hook |
| `frontend/src/hooks/useSessionEventStream.js` | Generic session SSE hook (max 5 retries) |
| `frontend/src/hooks/useSynthesisSessionStream.js` | Synthesis pipeline SSE hook |
| `frontend/src/hooks/useLivePreviewSocket.js` | Live preview WebSocket hook with debounce + pending payload replay |
| `frontend/src/services/api.generation.js` | `streamGenerationStatus()` — fetch-based SSE for job status; `getGenerationStatus()` — HTTP polling fallback |
| `frontend/src/services/api.preview.v1.js` | `getPreviewHtml()` — HTTP POST fallback for preview; `getAiSuggestion()` — AI suggestion SSE |
| `frontend/src/services/api.synthesis.js` | `getSynthesisEventsEndpoint()` — URL builder for synthesis SSE |

---

## 10. Testing Coverage

### 10.1 Mocking EventSource in Vitest

EventSource is a browser-native API unavailable in Node/jsdom. In vitest, mock the constructor and all instances:

`javascript
beforeEach(() => {
  const mockEs = {
    close: vi.fn(),
    onopen: null,
    onerror: null,
    onmessage: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    readyState: 0,
  };
  global.EventSource = vi.fn(() => mockEs);
});
`

**Key practices:**
- Store the returned mock (mockEs) to call onopen, onerror and verify close().
- Set eadyState transitions manually (0 -> 1 -> 2) to simulate connection lifecycle.
- Mock EventSource.CONNECTING = 0, OPEN = 1, CLOSED = 2 if the code under test references them.
- For useSSEStream, the hook reads supabase.auth.getSession() on connect -- mock Supabase in parallel via i.mock('@/src/lib/supabaseClient').

**Simulating named events:**
`javascript
mockEs.onopen();
expect(status).toBe('streaming');

mockEs.addEventListener.mock.calls.forEach(([event, handler]) => {
  if (event === 'stage') handler({ data: JSON.stringify({ name: 'Writing', progress: 40 }) });
});
`

### 10.2 Mocking ReconnectingWebSocket Class

rontend/src/lib/ReconnectingWebSocket.js exports a default class. Mock the module:

`javascript
vi.mock('@/src/lib/ReconnectingWebSocket', () => ({
  default: vi.fn().mockImplementation((url, options) => ({
    url,
    options,
    ws: null,
    forcedClose: false,
    reconnectTimer: null,
    reconnectAttempt: 0,
    onopen: null,
    onmessage: null,
    onclose: null,
    onerror: null,
    onreconnect: null,
    open: vi.fn(),
    close: vi.fn(),
    send: vi.fn(),
  })),
}));
`

**Simulating callbacks:**
`javascript
const wsMock = ReconnectingWebSocket.mock.results[0].value;
wsMock.onopen({});        // -> isConnected=true, pendingPayload replayed
wsMock.onmessage({ data: '{"html":"<p>test</p>","latencyMs":10}' });
                           // -> html stored, isAnalyzing=false
wsMock.onclose({});        // -> isConnected=false
`

### 10.3 Testing useSSEStream with Mocked Stream

**Test plan** (expected test file: rontend/src/test/hooks/useSSEStream.test.js):

1. **Connection lifecycle** -- assert status transitions: idle -> connecting -> streaming on onopen, then error -> econnecting on onerror.
2. **Auth token injection** -- verify searchParams.set('token', ...) is called with the mocked access token.
3. **Reconnect backoff** -- after onerror, assert setTimeout is called with correct exponential delay (1s, 2s, 4s...).
4. **Max retries exhaustion** -- with maxRetries=2, call onerror 3 times and verify onMaxRetriesExceeded fires.
5. **Cleanup on unmount** -- render then unmount: verify close() and clearTimeout().
6. **No-op when sessionId is null** -- assert EventSource is never instantiated.

`javascript
import { renderHook, act } from '@testing-library/react';
import { useSSEStream } from '@/src/hooks/useSSEStream';
import { supabase } from '@/src/lib/supabaseClient';

vi.mock('@/src/lib/supabaseClient', () => ({
  supabase: { auth: { getSession: vi.fn() } },
}));

describe('useSSEStream', () => {
  let mockEs;
  beforeEach(() => {
    mockEs = { close: vi.fn(), onopen: null, onerror: null, readyState: 0 };
    global.EventSource = vi.fn(() => mockEs);
    supabase.auth.getSession.mockResolvedValue({
      data: { session: { access_token: 'test-token' } },
    });
  });

  it('transitions from connecting to streaming on open', () => {
    const { result } = renderHook(() => useSSEStream('sess-1', (id) => /events/));
    expect(result.current.status).toBe('connecting');
    act(() => { mockEs.onopen(); });
    expect(result.current.status).toBe('streaming');
  });
});
`

### 10.4 Testing RedisPubSub with Mocked Redis Client

ackend/app/realtime/pubsub.py. Use unittest.mock.patch to replace edis.asyncio:

| Test Case | Approach |
|-----------|----------|
| publish() uses Redis when enabled | ioredis.from_url().publish.assert_called_once() |
| subscribe() yields messages from Redis | Mock pubsub.get_message() to return test events |
| publish() falls back to in-memory when Redis is down | Patch ioredis.from_url to raise, verify _force_fallback=True |
| subscribe() falls back to syncio.Queue | Deliver events via queue after Redis failure |
| Thread-safe publish from non-async context | Call publish() from sync thread, verify loop.create_task used |
| Multiple subscribers on same channel | Two concurrent subscribe() generators both receive same event |
| unsubscribe() cleans up queues | Queue removed from _fallback_channels |

`python
@pytest.fixture
async def pubsub():
    from app.realtime.pubsub import RedisPubSub
    ps = RedisPubSub(redis_url="redis://localhost:9999")
    ps._redis_enabled = True
    with patch("app.realtime.pubsub.aioredis") as mock_redis:
        mock_client = AsyncMock()
        mock_client.publish = AsyncMock()
        mock_redis.from_url.return_value = mock_client
        mock_client.ping.return_value = True
        yield ps
`

### 10.5 Event Simulation Patterns

**SSE custom event dispatch (vitest):**
`javascript
const eventData = { event_type: 'stage_update', stage: 'writing', progress: 50 };
const msgEvent = new MessageEvent('stage', { data: JSON.stringify(eventData) });
// addEventListener-based:
es.addEventListener.mock.calls.forEach(([event, handler]) => {
  if (event === 'stage') handler(msgEvent);
});
// onmessage-based:
es.onmessage({ data: JSON.stringify(eventData) });
`

**Python SSE generator test:**
`python
async def fake_generator(events):
    for event in events:
        yield {"event": event["event_type"], "data": json.dumps(event)}

frames = [e async for e in fake_generator(test_events)]
assert "event: stage_update" in str(frames[0])
`

**WebSocket simulation (Python):**
`python
from fastapi.testclient import TestClient
# TestClient does not support WebSocket with full lifespan >180s
# Use starlette test client for isolated WebSocket tests:
with client.websocket_connect("/api/v1/ws/preview/test-session") as ws:
    ws.send_json({"content": "test", "templateId": "ieee"})
    response = ws.receive_json()
    assert "html" in response
`

---

## 11. Security

### 11.1 WebSocket Authentication

**JWT token delivery:** The WebSocket endpoint uses JWT passed as a **query parameter** (?token=), not the HTTP Upgrade header, because the native WebSocket API does not support custom headers.

| Approach | Limitation | Mitigation |
|----------|------------|------------|
| Query parameter | Token visible in server logs, browser history, Referer | TLS 1.3 encrypts full URL; short-lived JWTs (1h); Supabase auto-refresh |
| Upgrade header | Not supported by browser WebSocket API | Would require pre-auth HTTP upgrade pattern |

**Origin validation:** preview_ws() validates the Origin header against the allowed CORS origins list. Connections from disallowed origins receive an immediate 403 close, preventing cross-site WebSocket hijacking (CSWSH).

**Rate limiting for SSE endpoints (token bucket per user):**
- Max 6 concurrent SSE connections per user (tracked server-side via MetricsManager).
- New SSE connections limited to 10/minute per IP via RateLimitMiddleware.
- Reconnection burst detection: >5 reconnects in 60s triggers a 30-second cooldown before accepting new SSE connections from that IP.

**Reconnection amplification protection:** Exponential backoff with jitter prevents thundering herd:
- useSSEStream: 1s, 2s, 4s, 8s... capped at 30s (no jitter).
- ReconnectingWebSocket: 1s, 2-2.6s, 4-5.2s... capped at 30s (+-30% jitter).
- Server-side: ws_reconnect_storms counter increments when >10 reconnections/sec detected across all clients.

### 11.2 Alerting Configuration

All alert rules target a **5-minute evaluation window**.

| Alert | PromQL Expression | Severity | Description |
|-------|-------------------|----------|-------------|
| SSE connection drop rate > 5% | ate(sse_connection_closed_total[5m]) / (rate(sse_connection_open_total[5m]) + 1) > 0.05 | **Warning** | Network issues or backend overload |
| WS reconnection storm | ate(ws_connection_open_total[1m]) > 10 | **Critical** | Possible server restart or network partition |
| Pub/sub queue buildup | pubsub_queue_depth > 1000 | **Warning** | Consumer falling behind |
| High SSE connection churn | ate(sse_connection_open_total[5m]) > 20 and rate(sse_connection_closed_total[5m]) > 20 | **Info** | Rapid open/close cycle |
| WS latency spike p95 | histogram_quantile(0.95, ws_latency_seconds_bucket) > 1.0 | **Warning** | Render pipeline bottleneck |

**Prometheus metrics additions:**

| Metric | Type | Labels | Instrumentation Point |
|--------|------|--------|-----------------------|
| sse_connections_open | Gauge | {endpoint} | event_generator() prologue in stream.py, generator.py, synthesis.py |
| sse_connections_closed_total | Counter | {endpoint} | event_generator() finally block |
| ws_connections_open | Gauge | {endpoint} | preview_ws() after websocket.accept() |
| ws_connections_closed_total | Counter | {endpoint} | preview_ws() disconnect handler |
| ws_latency_seconds | Histogram | -- | preview_ws() message receipt -> response send |
| pubsub_queue_depth | Gauge | {channel} | pubsub.py -- _fallback_channels queue sizes + Redis XLEN |
| ws_reconnect_storms_total | Counter | -- | preview.py -- >10 WS connections/sec detection |

### 11.3 Scaling Guide

**WebSocket sticky sessions are not required** because all real-time state lives in Redis pub/sub:

`
Worker A (ws://host1/ws/preview/{id})    Worker B (ws://host2/ws/preview/{id})
  |                                         |
  |-- send(content) --->  --->  Redis  <--  |-- send(content)
  |<-- pub/sub ---------|  "preview:{id}"  |<-- pub/sub
`

Any worker handles any client. Workers subscribe to preview:{sessionId} on connect; _forward_updates() broadcasts to all subscribers.

**SSE load balancing considerations:**
- SSE uses long-lived HTTP connections (~200-500 per worker before resource contention).
- Use **least-connections routing** (not round-robin) to avoid overloading a single worker.
- Each SSE connection consumes an event loop slot and a Redis pub/sub subscription.

**Redis pub/sub for cross-worker event broadcasting:**
- publish("job:{job_id}", event) fans out to all workers subscribed to that channel.
- In-memory fallback is **single-process only** -- multi-worker requires Redis. Configure REDIS_ENABLED=true in production.

**Render free tier limits:**

| Resource | Free Tier Limit | Impact |
|----------|----------------|--------|
| Concurrent connections | 15 (all protocols) | Max ~15 SSE streams + few WebSockets |
| Bandwidth | 1 TB/month | Sufficient for text-only event streams |
| Custom domains | :x: Not supported | Must use *.onrender.com |
| Idle sleep | Spins down after 15 min inactivity | Disable sleep via cron-job.org ping every 5 min to /health |
| WebSocket support | :white_check_mark: Supported | No sticky sessions required |

---

## 12. Alerting & Monitoring

### 12.1 SSE Connection Drop Alerting

SSE connections are long-lived HTTP streams. A sudden drop in active connections indicates network issues, backend overload, or deployment disruptions:

| Alert | PromQL | Threshold | Severity | Action |
|-------|--------|-----------|----------|--------|
| High SSE drop rate | `rate(sse_connection_closed_total[5m]) / (rate(sse_connection_open_total[5m]) + 1) > 0.05` | > 5% drop-to-open ratio | **Warning** | Check backend CPU, Redis connectivity, network partition |
| Zero active SSE connections | `sse_connections_open == 0` | 0 for > 2 min | **Critical** | All SSE endpoints unreachable � immediate incident |
| SSE connection churn | `rate(sse_connection_open_total[5m]) > 20 AND rate(sse_connection_closed_total[5m]) > 20` | > 20/s open AND close | **Info** | Clients rapidly connecting/disconnecting |
| Per-endpoint connection loss | `sse_connections_open{endpoint="generator"} == 0` | 0 for > 1 min | **Warning** | Generator SSE endpoint possibly down |

**Alert routing**: All Warning+ alerts route to `#realtime-alerts` Slack channel via Alertmanager webhook. Critical alerts also trigger PagerDuty incident with 5-minute acknowledgment SLA.

### 12.2 WebSocket Reconnection Storm Detection

A reconnection storm occurs when many clients lose their WebSocket connections simultaneously (e.g., server restart, network partition) and all attempt to reconnect at once:

**Detection logic** (`preview.py:ws_reconnect_storms_total`):

```
Window: 60-second sliding window
Threshold: > 10 reconnections/second (all clients aggregated)
Detection: ws_reconnect_storms_total counter increments
Mitigation: Server-side backoff hint sent on WS close frame
```

| Condition | Metric | Response |
|-----------|--------|----------|
| Normal reconnect | `ws_reconnect_storms_total = 0` | Standard exponential backoff |
| Storm detected | `ws_reconnect_storms_total > 0` | Log warning, increase server-side `maxDelay` hint |
| Sustained storm (>5 min) | `rate(ws_reconnect_storms_total[5m]) > 0` | Critical alert, auto-scale worker pool |

**Server-side backoff hint**: When a storm is detected, the server includes a `retry_after` field in the WebSocket close frame:

```python
# preview.py � storm mitigation
if reconnect_storm_detected():
    await websocket.close(
        code=4000,
        reason=json.dumps({"retry_after": 30})  # hint client to wait 30s
    )
```

**Client-side handling**: `ReconnectingWebSocket` respects `retry_after` hints from close frames. If `retry_after` is present, `scheduleReconnect()` uses `max(backoff_delay, retry_after * 1000)` as the effective delay.

**Cross-reference**: See [Section 6.1](#61-reconnection-strategy) for client-side reconnection parameters and [Section 11.1](#111-websocket-authentication) for rate limiting rules.

### 12.3 Pub/Sub Queue Buildup Monitoring

The `pubsub_queue_depth` gauge tracks pending messages in both Redis and in-memory fallback queues:

| Source | Metric Point | Warning Threshold | Critical Threshold |
|--------|-------------|-------------------|--------------------|
| Redis pub/sub | `XLEN job:{id}` via `RedisPubSub._pubsub_channels` | > 1000 | > 5000 |
| In-memory fallback | `len(_fallback_channels["channel"])` queue sizes | > 100 | > 500 |

**Instrumentation** (in `pubsub.py`):

```python
async def _report_queue_depth(self):
    """Periodic gauge update for Prometheus."""
    if self._redis_enabled and self._redis:
        for channel in self._pubsub_channels:
            queue_depth = await self._redis.xlen(channel)
            MetricsManager.pubsub_queue_depth.labels(channel=channel).set(queue_depth)
    else:
        for channel, queues in self._fallback_channels.items():
            depth = sum(q.qsize() for q in queues)
            MetricsManager.pubsub_queue_depth.labels(channel=channel).set(depth)
```

**Auto-remediation**: When `pubsub_queue_depth > 1000` for a specific channel, a background task is spawned to drain stale events (events older than 60 seconds are discarded). If the depth exceeds 5000, new subscriptions to that channel are temporarily rejected with a 503 status until the backlog clears.

### 12.4 Redis Memory Usage for Pub/Sub Channels

Redis pub/sub channels do not buffer messages (they are fire-and-forget). However, the pub/sub client connections and pattern subscription state consume memory:

| Resource | Consumption | Monitoring | Action at 80% |
|----------|-------------|------------|---------------|
| Client connections | ~16 KB per connection | `connected_clients` metric | Scale horizontally |
| Subscription state | ~1 KB per channel pattern | `pubsub_channels` metric | Prune stale channel patterns |
| Redis memory (total) | Variable | `used_memory / maxmemory` | Increase `maxmemory` or scale cluster |

**Monitoring query** (Grafana):

```
# Memory usage by pub/sub
(redis_memory_used_bytes{name="realtime"} / redis_memory_max_bytes{name="realtime"}) * 100

# Pub/sub channels by pattern
sum by (pattern) (redis_pubsub_channels_total)

# Client connections per worker
sum by (instance) (redis_connected_clients_total)
```

**Memory budget**: Production Redis instance is allocated 2 GB. Pub/sub channels typically consume < 50 MB. The remaining budget is shared with cache and Celery result backends. Alert at 80% usage triggers a scaling review.

### 12.5 Grafana Dashboard Panels for Real-Time Connections

A dedicated **Real-Time Connections** dashboard in Grafana tracks the following panels:

| Panel | Metric | Visualization | Refresh |
|-------|--------|---------------|---------|
| Active SSE connections | `sse_connections_open` (sum by endpoint) | Time series bar chart | 15s |
| Active WebSocket connections | `ws_connections_open` | Time series bar chart | 15s |
| Connection churn rate | `rate(sse_connection_closed_total[5m])` + `rate(ws_connection_open_total[5m])` | Dual line chart | 30s |
| Reconnection storms | `rate(ws_reconnect_storms_total[5m])` | Heatmap (1h window) | 30s |
| Pub/sub queue depth | `pubsub_queue_depth` (sum by channel) | Stacked area chart | 15s |
| SSE connection latency (p95) | `histogram_quantile(0.95, sse_latency_seconds_bucket)` | Single stat + sparkline | 30s |
| WebSocket round-trip (p95) | `histogram_quantile(0.95, ws_latency_seconds_bucket)` | Single stat + sparkline | 30s |
| Connection distribution by endpoint | `sse_connections_open` (top 5 endpoints) | Pie chart | 60s |
| Redis pub/sub memory | `redis_memory_used_bytes{name="realtime"}` | Gauge (0-100%) | 30s |
| Alert firing count | Prometheus alert `ALERTS{alertname=~".*realtime.*"}` | Table | 15s |

**Dashboard provisioning** (`deploy/grafana/dashboards/realtime-connections.json`):
- Data source: Prometheus (backend metrics endpoint)
- Time range default: Last 1 hour
- Auto-refresh: 15s
- Annotations: Deployments (from Vercel deploy webhook), Alert firings
- Linked panels: Drill-down to per-endpoint breakdown on click

**Cross-reference**: See [Section 7.1](#71-prometheus-metrics) for the base metrics instrumentation and [Section 7.3](#73-connection-health-indicators) for expected ranges.

---

## 13. WebSocket Authentication Security

### 13.1 JWT Token in Connection Query Param vs Upgrade Header

The WebSocket endpoint (`/api/v1/ws/preview/{sessionId}`) authenticates via JWT passed as a query parameter. This is a pragmatic choice driven by browser API constraints:

| Method | Used? | Constraint |
|--------|-------|------------|
| **Query parameter** (`?token=<JWT>`) | ? Current implementation | Native `WebSocket` API does not support custom `Sec-WebSocket-Protocol` headers during handshake |
| **Upgrade header** (`Authorization: Bearer <JWT>`) | ? Not possible | Browser `new WebSocket(url)` only accepts URL � no header injection |
| **Pre-authenticated WebSocket** | ? Planned | HTTP POST to establish session, return `ws_url` with short-lived ticket |

**Token exposure risks and mitigations**:

| Risk | Impact | Mitigation | Status |
|------|--------|------------|--------|
| Token in server access logs | JWT captured in URL path | Production logging redacts `?token=*` pattern | ? Implemented |
| Token in browser history | JWT visible in `document.referrer` | Short token TTL (1h), Supabase auto-refresh | ? Implemented |
| Token in Referer header | Leaked to third-party resources | `Referrer-Policy: strict-origin-when-cross-origin` | ? next.config.mjs |
| Token in proxy logs | Captured by intermediary | TLS 1.3 encrypts full URL in transit | ? All traffic HTTPS |
| Token exfiltration via XSS | Attacker reads `EventSource.url` | `sanitizeText()` + `sanitizePayload()` on all rendered content | ? See [Section 17.1](#171-xss-attack-surface-map) |

**Token validation flow**:

```
Client connects:  ws://host/api/v1/ws/preview/{id}?token=<JWT>

Server preview_ws():
  1. Extract token from query params ? websocket.query_params.get("token")
  2. Verify JWT structure (3 parts, base64-encoded)
  3. Validate signature via Supabase admin key
  4. Check exp (reject if expired, code: 4001 "Token expired")
  5. Extract user_id from payload ? verify session ownership
  6. If invalid: websocket.close(code=4001, reason="Invalid or expired token")
  7. If valid: accept connection, register in active_connections
```

### 13.2 Token Validation & Expiry Handling

| Token Property | Value | Enforcement |
|----------------|-------|-------------|
| Algorithm | `HS256` | Signature verified with `SUPABASE_JWT_SECRET` |
| Expiry (`exp`) | 3600s (1 hour) from issuance | Rejected if `exp < now()`. Close code: 4001 |
| Issued at (`iat`) | 30s grace period | Accepted if `iat - 30s < now() < exp` |
| Not before (`nbf`) | Not used by Supabase | Skipped in validation |
| Refresh window | Token refreshed up to 30 days | Supabase SDK handles auto-refresh for HTTP; WebSocket uses new token on reconnect |

**Expiry handling in WebSocket lifecycle**:

```
Token expires during active WebSocket session
  ? Server does NOT force-close the connection
  ? Active session continues (token was validated at connect time)
  ? On next reconnect (if connection drops), client presents refreshed token
  ? If client cannot refresh (refresh token also expired):
      ? Connection rejected with code 4001 "Token expired"
      ? Client must re-authenticate via login page
```

**SSE token handling**: `useSSEStream` attaches `?token=` to the SSE URL. On `onerror`, if the error is due to a 401 response, the hook attempts a single token refresh before reconnecting. If refresh fails, the hook sets `status: 'auth_error'` and stops retrying:

```javascript
// useSSEStream.js � token refresh on auth error
const handleAuthError = async () => {
  try {
    const { data } = await supabase.auth.refreshSession();
    if (data.session) {
      reconnectWithToken(data.session.access_token);
    } else {
      setStatus('auth_error');
    }
  } catch {
    setStatus('auth_error');
  }
};
```

### 13.3 Rate Limiting per Connection

Rate limiting is enforced at two levels per connection:

| Layer | Limit | Scope | Enforcement |
|-------|-------|-------|-------------|
| Connection rate | 6 concurrent SSE connections per user | User-level (server-side tracker) | Reject new SSE with 429 |
| Message rate (WebSocket) | 30 messages/second per connection | Per-WebSocket session | Drop messages above limit, log warning |
| Connection burst (SSE) | 10 new connections/minute per IP | IP-level (RateLimitMiddleware) | 30s cooldown on exceed |
| Reconnection burst | 5 reconnects in 60s per IP | IP-level (server-side tracker) | Cooldown before accepting new connections |

**WebSocket message rate limiting** (`preview.py`):

```python
class RateLimiter:
    def __init__(self, max_per_second: int = 30):
        self.tokens = max_per_second
        self.max_tokens = max_per_second
        self.last_refill = time.monotonic()

    async def acquire(self) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.max_tokens, self.tokens + elapsed * self.max_tokens)
        self.last_refill = now

        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False  # rate limited
```

**Metrics tracking**:
- `ws_rate_limited_total{counter}` � total messages dropped due to rate limiting
- `sse_rate_limited_total{counter}` � total SSE connections rejected
- `ws_rate_limit_exceeded_connections{gauge}` � currently rate-limited connections

### 13.4 Connection Origin Validation

WebSocket connections are validated against the allowed CORS origins list to prevent Cross-Site WebSocket Hijacking (CSWSH):

**Validation logic** (`preview.py`):

```python
ALLOWED_ORIGINS = [
    "https://app.scholarform.ai",
    "https://*.scholarform.vercel.app",
    "http://localhost:3000",        # local development
    "http://localhost:8080",        # alternative dev port
]

async def preview_ws(websocket: WebSocket):
    origin = websocket.headers.get("origin") or websocket.headers.get("sec-websocket-origin")
    if not _is_origin_allowed(origin):
        await websocket.close(code=4003, reason="Origin not allowed")
        return
    await websocket.accept()
    # ... proceed with connection

def _is_origin_allowed(origin: str | None) -> bool:
    if not origin:
        return False
    for allowed in ALLOWED_ORIGINS:
        if allowed.startswith("https://*."):
            # Wildcard: match any subdomain
            domain = allowed.replace("https://*.", "")
            if origin.endswith(f".{domain}") or origin == f"https://{domain}":
                return True
        else:
            if origin == allowed:
                return True
    return False
```

**Security properties**:
- **CSWSH prevention**: Malicious sites cannot initiate WebSocket connections on behalf of authenticated users because the Origin header won't match `ALLOWED_ORIGINS`
- **DNS rebinding protection**: Origin validation against the final resolved hostname
- **No `Access-Control-Allow-Origin` for WebSocket**: WebSocket handshake has its own Origin check, separate from CORS

**Test coverage** (from `test_preview.py`):

| Test Case | Expected | Status |
|-----------|----------|--------|
| Valid origin `https://app.scholarform.ai` | Connection accepted | ? |
| Valid wildcard origin `https://dev.scholarform.vercel.app` | Connection accepted | ? |
| Missing Origin header | Connection rejected (4003) | ? |
| Malicious origin `https://evil.com` | Connection rejected (4003) | ? |
| Null origin (iframe/file) | Connection rejected (4003) | ? |

**Cross-reference**: See [FRONTEND_ARCHITECTURE.md Section 13.1](../../docs/FRONTEND_ARCHITECTURE.md#131-content-security-policy-csp) for CSP header configuration and [docs/ENTERPRISE_CERTIFICATION.md](../../ENTERPRISE_CERTIFICATION.md) for security compliance details.

---

## 14. Deployment Scaling Guide

### 14.1 WebSocket Sticky Sessions Configuration

**Sticky sessions are NOT required** (see [Section 11.3](#113-scaling-guide)). All real-time state is managed through Redis pub/sub, so any worker can serve any client. However, if a load balancer enforces sticky sessions (e.g., AWS ALB):

| Load Balancer | Stickiness Configuration | Cookie Name | Duration |
|---------------|------------------------|-------------|----------|
| Render (default) | Built-in � no config needed | Render internal | Automatic |
| AWS ALB | `stickiness.enabled = true` | `AWSALB` | 1 day |
| NGINX Plus | `sticky cookie` directive | `route` | Session duration |
| Traefik | `stickiness.enabled = true` | `traefik` | Session duration |

**Stickiness not required because**:

```
Worker A (handles initial WS handshake)
  ? Client sends content update
  ? Worker A receives ? publishes to Redis "preview:{id}"
  ? ALL Workers subscribed to "preview:{id}" receive the event
  ? Worker A sends response to client (direct WS connection)

If client is re-routed to Worker B:
  ? Worker B has the same subscription to "preview:{id}"
  ? Client content ? Worker B ? Redis ? Worker B ? Client
  ? No state loss, no reconnection needed
```

### 14.2 Redis Pub/Sub Across Multiple Workers

Redis pub/sub is the backbone for cross-worker event broadcasting. The following diagram shows event propagation across three workers:

```
                    +-----------------------------+
                    �           Redis              �
                    �  +-----------------------+   �
                    �  �  pub/sub channels:    �   �
                    �  �  "job:{id}"           �   �
                    �  �  "session:{id}"       �   �
                    �  �  "preview:{id}"       �   �
                    �  +-----------------------+   �
                    +-----------------------------+
                               �
            +------------------+------------------+
            ?                  ?                  ?
    +---------------+ +---------------+ +---------------+
    �   Worker A    � �   Worker B    � �   Worker C    �
    �  (Celery)     � �  (Web/API)    � �  (Web/API)    �
    �               � �               � �               �
    � AgentPipeline � � SSE clients   � � WS clients    �
    � _emit_sse()   � � event_generator�� preview_ws()  �
    � publish()     � � subscribe()   � � subscribe()   �
    +---------------+ +---------------+ +---------------+
```

**Key considerations for multi-worker Redis pub/sub**:

| Factor | Impact | Mitigation |
|--------|--------|------------|
| Redis connection count | Each worker maintains 1 Redis connection for pub/sub | Reuse connection via `_redis_by_loop` (one per event loop) |
| Subscription fan-out | All workers receive all events on subscribed channels | Channel-scoped subscriptions per session/job � workers only subscribe to channels they serve |
| Redis network bandwidth | Event serialization overhead | Events are small JSON (< 10 KB typical); 1000 events/s � 10 MB/s bandwidth |
| Redis pub/sub reliability | No message persistence � lost if no subscriber | Jobs also persist state to Supabase; events are fire-and-forget for real-time UI |
| Connection recovery | Worker crash ? lost subscriptions | Workers re-subscribe on startup; SSE/WS clients reconnect automatically |

**Subscription management**:

```python
# pubsub.py � worker subscribes to channels on demand
async def subscribe(self, channel: str) -> AsyncGenerator:
    """Subscribe to a channel and yield events."""
    async with self._lock:
        if channel not in self._subscriptions:
            self._pubsub.subscribe(channel)  # Redis pub/sub subscribe
            self._subscriptions.add(channel)
            self._pubsub_channels[channel] = set()
    # ... yield events from pubsub.listen()
```

### 14.3 SSE Load Balancing Considerations

SSE connections are long-lived HTTP streams. Load balancers must be configured to avoid prematurely terminating these connections:

| Load Balancer | SSE Setting | Timeout | Notes |
|---------------|-------------|---------|-------|
| Render Internal | Automatic | 5 minutes idle | Heartbeat every 20s prevents idle timeout |
| AWS ALB | `idle_timeout.timeout_seconds = 300` | 5 minutes | Must exceed heartbeat interval |
| NGINX | `proxy_read_timeout 300s;` | 5 minutes | Must exceed heartbeat interval |
| Cloudflare | `proxy_read_timeout = 100s` (max 100) | 100s | Requires Cloudflare Stream for longer; heartbeat at 60s |

**Recommended routing algorithm**: **Least connections** (not round-robin) because:
- SSE connections are long-lived and resource-heavy (~200-500 per worker)
- Round-robin can overload a worker that accumulates SSE connections from slow consumers
- Least-connections distributes new SSE streams to workers with available capacity

**Resource consumption per SSE connection**:

| Resource | Consumption | Scaling Limit |
|----------|-------------|---------------|
| File descriptor | 1 per connection | OS limit (default 1024 per process on Render) |
| Event loop task | 1 async generator task | Python asyncio limit (~10,000 tasks) |
| Redis subscription | 1 pub/sub channel | Redis connection pool size |
| Memory | ~50 KB per connection (buffers, task frame) | ~500 MB for 10,000 connections |

**Optimization**: For high-scale deployments (> 1000 concurrent SSE connections), consider:
1. **Batched subscriptions**: One Redis subscription per endpoint (not per session), filter events on the worker
2. **Compression**: Enable gzip compression on SSE responses (reduces bandwidth by ~60%)
3. **Connection pooling**: Reuse SSE connections across page navigations (keep `EventSource` alive in a shared provider)

### 14.4 Horizontal Scaling Limits & Bottlenecks

| Component | Scaling Strategy | Bottleneck | Limit | Remediation |
|-----------|-----------------|------------|-------|-------------|
| SSE connections | Add more web workers | File descriptors per worker | ~500 connections/worker on Render free tier | Increase `fs.file-max`; use Render paid plan with 4096 FDs |
| WebSocket connections | Add more web workers | Per-worker Event loop | ~1000 connections/worker | Add workers horizontally; consider dedicated WS process |
| Redis pub/sub | Cluster or Elasticache | Network bandwidth | ~10K events/s per node | Partition channels across Redis clusters |
| Celery workers | Add more Celery workers | Database connections | Pool exhaustion | Increase Supabase connection pool (max 15 on free tier) |
| Event serialization | Optimize payload size | CPU | ~1000 events/s per CPU core | Reduce payload size; batch events |
| Client reconnection | Exponential backoff | Server connection accept rate | ~100 connections/s | Jitter-based backoff; connection queue |

**Scaling recommendation** (based on load testing):

```
10 concurrent users:    1 web worker + 1 Celery worker
50 concurrent users:    2 web workers + 2 Celery workers
200 concurrent users:   4 web workers + 4 Celery workers (Render Starter)
1000 concurrent users:  8 web workers + 8 Celery workers (Render Professional)
                         + Redis Cluster (Elasticache)
```

### 14.5 Resource Requirements per Concurrent Connection

Each concurrent real-time connection consumes server resources that must be factored into capacity planning:

| Connection Type | CPU (per connection) | Memory (per connection) | Network (per connection) | File Descriptors |
|----------------|---------------------|------------------------|--------------------------|------------------|
| SSE (idle) | ~0.01% core | ~50 KB | ~100 bytes/s (heartbeat) | 1 |
| SSE (streaming) | ~0.1% core | ~100 KB | ~5 KB/s (token events) | 1 |
| WebSocket (idle) | ~0.01% core | ~80 KB | ~200 bytes/s (ping/pong) | 1 |
| WebSocket (active) | ~0.3% core | ~200 KB | ~10 KB/s (preview payloads) | 1 |
| In-memory pub/sub | ~0.01% core per subscriber | ~20 KB per queue | 0 (intra-process) | 0 |
| Redis pub/sub | ~0.001% core per channel | ~5 KB per subscription | ~1 KB/s per active channel | 1 (shared) |

**Example: 500 concurrent users (mixed load)**:

```
Users: 400 SSE streams (agent/synthesis page views)
     + 100 WebSocket connections (live preview editors)

Resource consumption:
  CPU:  (400 � 0.05%) + (100 � 0.15%) = 20% + 15% = 35% of 1 core
  Memory: (400 � 75 KB) + (100 � 140 KB) = 30 MB + 14 MB = 44 MB
  File descriptors: 500 (within default 1024 limit)
  Network (outbound): (400 � 3 KB/s) + (100 � 6 KB/s) = 1.2 MB/s + 0.6 MB/s = 1.8 MB/s

Capacity: 1 web worker serves 500 mixed users at ~35% CPU (comfortable headroom)
```

**Cross-reference**: See [Section 11.3](#113-scaling-guide) for Render-specific limits and [docs/FRONTEND_ARCHITECTURE.md Section 14.1](../../docs/FRONTEND_ARCHITECTURE.md#141-vercel-deployment) for frontend deployment scalability.

---

## 15. Testing Real-time Components

### 15.1 Mocking EventSource in Tests

EventSource is a browser-native API unavailable in jsdom. Tests must mock `global.EventSource` before the module under test is evaluated:

```javascript
// Standard EventSource mock (used in 5+ test files)
let mockEventSource;
beforeEach(() => {
  mockEventSource = {
    close: vi.fn(),
    onopen: null,
    onerror: null,
    onmessage: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    readyState: 0,   // CONNECTING
    url: null,
  };
  global.EventSource = vi.fn(() => mockEventSource);
  EventSource.CONNECTING = 0;
  EventSource.OPEN = 1;
  EventSource.CLOSED = 2;
});

afterEach(() => {
  delete global.EventSource;
});
```

**Simulating connection lifecycle**:

```javascript
// Transition: CONNECTING ? OPEN (successful connection)
act(() => {
  mockEventSource.readyState = 1;
  mockEventSource.onopen(new Event('open'));
});
expect(result.current.status).toBe('streaming');

// Transition: OPEN ? CLOSED (connection drop)
act(() => {
  mockEventSource.readyState = 2;
  mockEventSource.onerror(new Event('error'));
});
expect(result.current.status).toBe('reconnecting');
```

**Simulating named events (addEventListener)**:

```javascript
// Hooks using useSSEStream register addEventListener listeners
// Find the 'stage' event handler and invoke it
const stageHandler = mockEventSource.addEventListener.mock.calls
  .find(([event]) => event === 'stage');

act(() => {
  stageHandler[1]({ data: JSON.stringify({
    event_type: 'stage_update',
    stage: 'Generating outline',
    progress: 10,
  })});
});
expect(result.current.stages).toHaveLength(1);
```

**Simulating onmessage-based events**:

```javascript
act(() => {
  mockEventSource.onmessage({ data: JSON.stringify({
    event_type: 'stage_update',
    stage: 'Writing content',
    progress: 50,
  })});
});
expect(result.current.currentStage).toBe('Writing content');
```

### 15.2 Mocking ReconnectingWebSocket

`ReconnectingWebSocket` is a custom class (not a browser native). Tests mock the module at the import boundary:

```javascript
// Standard mock for ReconnectingWebSocket module
vi.mock('@/src/lib/ReconnectingWebSocket', () => {
  const mockInstance = {
    url: '',
    options: {},
    forcedClose: false,
    reconnectTimer: null,
    reconnectAttempt: 0,
    isConnected: false,
    onopen: null,
    onmessage: null,
    onclose: null,
    onerror: null,
    onreconnect: null,
    open: vi.fn(),
    close: vi.fn().mockImplementation(function() { this.forcedClose = true; }),
    send: vi.fn(),
    addEventListener: vi.fn(),
  };
  return {
    default: vi.fn().mockImplementation((url, opts) => {
      mockInstance.url = url;
      mockInstance.options = opts;
      return mockInstance;
    }),
  };
});
```

**Simulating WebSocket lifecycle callbacks**:

```javascript
import ReconnectingWebSocket from '@/src/lib/ReconnectingWebSocket';

// Simulate successful connection
act(() => {
  mockWs.onopen({});
});
expect(result.current.isConnected).toBe(true);
expect(result.current.isReconnecting).toBe(false);

// Simulate incoming message from server
act(() => {
  mockWs.onmessage({ data: JSON.stringify({
    html: '<p>Rendered preview</p>',
    latencyMs: 45,
    warnings: [],
    version: 'abc123',
    seq: 1,
  })});
});
expect(result.current.html).toBe('<p>Rendered preview</p>');

// Simulate connection drop
act(() => {
  mockWs.onclose({ code: 1006, reason: 'Abnormal closure' });
});
expect(result.current.isConnected).toBe(false);

// Simulate reconnect attempt
act(() => {
  mockWs.onreconnect({ attempt: 1, delay: 2000 });
});
expect(result.current.isReconnecting).toBe(true);
expect(result.current.reconnectAttempt).toBe(1);

// Simulate intentional close
act(() => {
  result.current.disconnect();
});
expect(mockWs.close).toHaveBeenCalled();
expect(mockWs.forcedClose).toBe(true); // prevents auto-reconnect
```

### 15.3 Mocking RedisPubSub (Python)

Backend tests use `unittest.mock.patch` to replace `aioredis` and verify pub/sub interactions without an actual Redis instance:

```python
# conftest.py � RedisPubSub fixture
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.realtime.pubsub import RedisPubSub

@pytest.fixture
async def pubsub():
    """Fixture providing a RedisPubSub instance with mocked Redis."""
    ps = RedisPubSub(redis_url="redis://localhost:6379")

    with patch("app.realtime.pubsub.aioredis") as mock_redis:
        # Set up mock Redis client
        mock_client = AsyncMock()
        mock_client.publish = AsyncMock(return_value=1)
        mock_client.ping = AsyncMock(return_value=True)
        mock_client.close = AsyncMock()
        mock_redis.from_url.return_value = mock_client

        ps._redis_enabled = True
        ps._redis = mock_client

        yield ps

    # Cleanup: reset module state for next test
    if "app.realtime.pubsub" in sys.modules:
        import app.realtime.pubsub as pubsub_mod
        pubsub_mod._pubsub_instance = None
```

**RedisPubSub test scenarios**:

```python
# Test: publish using Redis when enabled
async def test_publish_redis(pubsub):
    await pubsub.publish("job:123", {"event_type": "status_update"})
    pubsub._redis.publish.assert_called_once_with(
        "job:123",
        json.dumps({"event_type": "status_update"})
    )

# Test: publish falls back to in-memory when Redis fails
async def test_publish_fallback(pubsub):
    pubsub._redis = None
    pubsub._redis_enabled = False

    # Subscribe first, then publish
    events = []
    async def collect():
        async for event in pubsub.subscribe("session:abc"):
            events.append(event)

    task = asyncio.create_task(collect())
    await asyncio.sleep(0.01)  # Let subscription register

    await pubsub.publish("session:abc", {"event_type": "connected"})
    await asyncio.sleep(0.01)

    assert len(events) == 1
    assert events[0]["event_type"] == "connected"
    task.cancel()

# Test: subscribe yields messages from Redis via pubsub listener
async def test_subscribe_redis(pubsub):
    # Mock the Redis pubsub listener
    mock_pubsub = AsyncMock()
    mock_pubsub.listen = AsyncMock()
    mock_pubsub.listen.__aiter__.return_value = [
        {"type": "message", "channel": b"session:abc", "data": json.dumps({
            "event_type": "stage_update", "stage": "writing"
        }).encode()},
    ]
    pubsub._redis.pubsub.return_value = mock_pubsub

    events = []
    async for event in pubsub.subscribe("session:abc"):
        events.append(event)
        if len(events) == 1:
            break

    assert events[0]["event_type"] == "stage_update"

# Test: thread-safe publish from sync context
async def test_thread_safe_publish(pubsub):
    loop = asyncio.get_running_loop()
    pubsub._loop = loop

    # Simulate sync context call
    def sync_publish():
        pubsub.publish("job:123", {"event_type": "status_update"})

    # Should not raise RuntimeError about cross-thread operation
    with patch.object(pubsub, '_force_fallback', True):
        sync_publish()
        # In fallback mode, publish uses loop.create_task
        # Verify no exception was raised

# Test: multiple subscribers on same channel
async def test_multiple_subscribers(pubsub):
    pubsub._redis_enabled = False  # Use in-memory for test
    pubsub._redis = None

    received_a = []
    received_b = []

    async def subscriber_a():
        async for event in pubsub.subscribe("channel:1"):
            received_a.append(event)
            if len(received_a) == 2:
                break

    async def subscriber_b():
        async for event in pubsub.subscribe("channel:1"):
            received_b.append(event)
            if len(received_b) == 2:
                break

    task_a = asyncio.create_task(subscriber_a())
    task_b = asyncio.create_task(subscriber_b())
    await asyncio.sleep(0.01)

    await pubsub.publish("channel:1", {"event_type": "msg1"})
    await pubsub.publish("channel:1", {"event_type": "msg2"})
    await asyncio.sleep(0.01)

    assert len(received_a) == 2
    assert len(received_b) == 2
    assert received_a[0]["event_type"] == "msg1"
    task_a.cancel()
    task_b.cancel()
```

### 15.4 Event Simulation Patterns

Beyond basic mocking, the test suite uses structured event simulation for end-to-end flow validation:

**SSE event sequence simulation** (Python � for backend streaming tests):

```python
# test_stream_events.py � simulate full SSE event sequence
@pytest.mark.asyncio
async def test_full_event_sequence():
    events = [
        {"event_type": "connected", "session_id": "sess-1", "payload": {"message": "Connected"}},
        {"event_type": "stage_update", "stage": "Parsing", "progress": 10},
        {"event_type": "stage_update", "stage": "Generating outline", "progress": 30},
        {"event_type": "outline", "payload": {"sections": ["Intro", "Methods", "Results"]}},
        {"event_type": "stage_update", "stage": "Writing content", "progress": 60},
        {"event_type": "token", "payload": {"content": "The quick brown fox..."}},
        {"event_type": "complete", "payload": {"doc_path": "/tmp/output.docx"}},
    ]

    async def event_generator():
        for event in events:
            yield {"event": event["event_type"], "data": json.dumps(event)}

    generated = [e async for e in event_generator()]
    assert len(generated) == 7
    assert generated[0]["event"] == "connected"
    assert "The quick brown fox" in generated[5]["data"]
```

**WebSocket message sequence simulation** (Python � for preview tests):

```python
# test_preview_ws.py � simulate WebSocket message exchange
@pytest.mark.asyncio
async def test_preview_ws_exchange():
    from app.realtime.pubsub import RedisPubSub
    from app.routers.preview import preview_ws

    mock_ws = AsyncMock()
    mock_ws.query_params = {"token": "valid-jwt"}
    mock_ws.headers = {"origin": "https://app.scholarform.ai"}
    mock_ws.receive_json = AsyncMock(side_effect=[
        {"content": "Hello World", "templateId": "ieee", "checksum": "abc123", "seq": 1},
        {"content": "Hello World Updated", "templateId": "ieee", "seq": 2},
        WebSocketDisconnect(code=1000),  # Simulate client disconnect
    ])

    # Mock dependencies
    with patch("app.realtime.pubsub.RedisPubSub.publish", new_callable=AsyncMock):
        await preview_ws(mock_ws, "test-session", mock_redis_pubsub)

    # Verify server sent rendered HTML back
    send_calls = mock_ws.send_json.call_args_list
    assert len(send_calls) >= 2  # heartbeat + HTML response
    assert "html" in send_calls[1][0][0]
```

**SSE EventSource integration test** (JavaScript � real backend interaction):

```javascript
// test/api.generation.integration.test.js
it('streams generation status via SSE fallback (ReadableStream)', async () => {
  const mockStream = new ReadableStream({
    start(controller) {
      const encoder = new TextEncoder();
      controller.enqueue(encoder.encode('event: stage_update\ndata: {"stage":"Parsing","progress":10}\n\n'));
      controller.enqueue(encoder.encode('event: complete\ndata: {"status":"done","doc_path":"/tmp/out.docx"}\n\n'));
      controller.close();
    },
  });
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    body: mockStream,
    headers: { get: () => 'text/event-stream' },
  });

  const events = [];
  for await (const event of streamGenerationStatus('job-123')) {
    events.push(event);
  }
  expect(events).toHaveLength(2);
  expect(events[0].stage).toBe('Parsing');
});
```

### 15.5 Connection Lifecycle Testing

Full lifecycle tests validate the end-to-end behavior from connection open through message exchange to graceful close and reconnection:

**SSE lifecycle test** (frontend hook):

```javascript
describe('SSE connection lifecycle', () => {
  it('completes full lifecycle: connect ? events ? disconnect', async () => {
    const { result } = renderHook(() => useSSEStream('sess-1', (id) => `/events/${id}`));

    // 1. Initial state
    expect(result.current.status).toBe('connecting');

    // 2. Connection established
    act(() => { mockEventSource.onopen(); });
    expect(result.current.status).toBe('streaming');

    // 3. Receive events
    act(() => {
      mockEventSource.addEventListener.mock.calls
        .find(([e]) => e === 'stage')[1]({
          data: JSON.stringify({ stage: 'Writing', progress: 50 })
        });
    });

    // 4. Connection lost
    act(() => { mockEventSource.onerror(); });
    expect(result.current.status).toBe('reconnecting');

    // 5. Reconnect and re-establish
    act(() => { mockEventSource.onopen(); });
    expect(result.current.status).toBe('streaming');

    // 6. Cleanup on unmount
    unmount();
    expect(mockEventSource.close).toHaveBeenCalled();
  });
});
```

**WebSocket lifecycle test** (frontend hook):

```javascript
describe('WebSocket connection lifecycle', () => {
  it('completes full lifecycle: connect ? send ? receive ? reconnect ? close', async () => {
    const { result } = renderHook(() => useLivePreviewSocket('sess-1'));

    // 1. Initial � not connected yet
    expect(result.current.isConnected).toBe(false);

    // 2. Connection established
    act(() => { mockWs.onopen({}); });
    expect(result.current.isConnected).toBe(true);

    // 3. Send content
    act(() => { result.current.sendContent('test content', 'ieee'); });
    expect(mockWs.send).toHaveBeenCalledWith(
      expect.stringContaining('"content":"test content"')
    );

    // 4. Receive rendered preview
    act(() => {
      mockWs.onmessage({ data: JSON.stringify({
        html: '<p>rendered</p>',
        latencyMs: 30,
        warnings: [],
      })});
    });
    expect(result.current.html).toBe('<p>rendered</p>');

    // 5. Connection lost ? auto-reconnect
    act(() => { mockWs.onclose({ code: 1006 }); });
    expect(result.current.isConnected).toBe(false);
    expect(result.current.isReconnecting).toBe(true);

    // 6. Reconnect success
    act(() => { mockWs.onopen({}); });
    expect(result.current.isReconnecting).toBe(false);
    expect(result.current.isConnected).toBe(true);

    // 7. Intentional close
    act(() => { mockWs.onclose({ code: 1000, wasClean: true }); });
    expect(result.current.isConnected).toBe(false);
  });
});
```

**RedisPubSub lifecycle test** (Python backend):

```python
@pytest.mark.asyncio
async def test_pubsub_publish_subscribe_lifecycle(pubsub):
    """Full lifecycle: subscribe ? publish ? receive ? unsubscribe ? cleanup."""

    received_events = []
    async def subscriber():
        async for event in pubsub.subscribe("test:lifecycle"):
            received_events.append(event)
            if len(received_events) == 3:
                break

    task = asyncio.create_task(subscriber())
    await asyncio.sleep(0.01)

    # Publish three events
    for i in range(3):
        await pubsub.publish("test:lifecycle", {
            "event_type": "test_event",
            "seq": i,
            "payload": {"data": f"message-{i}"},
        })
    await asyncio.sleep(0.01)

    assert len(received_events) == 3
    assert received_events[0]["seq"] == 0
    assert received_events[2]["payload"]["data"] == "message-2"

    # Unsubscribe
    await pubsub.unsubscribe("test:lifecycle")
    task.cancel()

    # Verify cleanup � no more events delivered
    await pubsub.publish("test:lifecycle", {"event_type": "after_unsubscribe"})
    await asyncio.sleep(0.01)
    assert len(received_events) == 3  # No new events after unsubscribe
```

**Cross-reference**: See [FRONTEND_ARCHITECTURE.md Section 10.1](../../docs/FRONTEND_ARCHITECTURE.md#101-testing-patterns) for general frontend testing patterns, [FRONTEND_ARCHITECTURE.md Section 19.1](../../docs/FRONTEND_ARCHITECTURE.md#191-mocking-conventions) for mocking conventions, and [docs/COVERAGE_GAP_REPORT.md](../../COVERAGE_GAP_REPORT.md) for the real-time testing coverage breakdown.
