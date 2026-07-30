<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

---

title: ScholarForm AI — Webhooks
description: Outgoing event webhook system — subscription management, HMAC-SHA256 signed delivery, retry policy, and security
sidebar_position: 12
version: "1.0"
status: ✅ Complete
owner: Engineering Team
review_cadence: quarterly
last_updated: July 2026
---

# Webhooks

ScholarForm AI provides an outgoing webhook system that notifies your services when document processing, synthesis, or generation events occur. Webhooks are delivered via HTTP POST with HMAC-SHA256 signature verification, automatic retries, and full delivery logging.

- [Overview](#overview)
- [Event Types](#event-types)
- [Subscription Management](#subscription-management)
    - [Create a Subscription](#create-a-subscription)
    - [List Subscriptions](#list-subscriptions)
    - [Get a Subscription](#get-a-subscription)
    - [Update a Subscription](#update-a-subscription)
    - [Delete a Subscription](#delete-a-subscription)
- [Delivery](#delivery)
    - [HTTP Request Format](#http-request-format)
    - [Retry Policy](#retry-policy)
    - [Delivery Timeout](#delivery-timeout)
- [Signature Verification](#signature-verification)
    - [Node.js Verification](#nodejs-verification)
    - [Python Verification](#python-verification)
- [Security](#security)
    - [Secret Encryption at Rest](#secret-encryption-at-rest)
    - [Replay Protection](#replay-protection)
    - [Origin Validation](#origin-validation)
    - [SSRF Prevention](#ssrf-prevention)
- [Testing](#testing)
- [Delivery Logs](#delivery-logs)
- [Rate Limits](#rate-limits)
- [Configuration](#configuration)
- [See Also](#see-also)

---

## Overview

The webhook system is built on a **publish-subscribe** model:

1. You create a **subscription** pointing to your endpoint URL and select which event types to receive.
2. When an event occurs, ScholarForm AI **dispatches** an HTTP POST to your endpoint.
3. Each payload includes an `X-Webhook-Signature` header for **integrity verification**.
4. Failed deliveries are **retried** up to 3 times with exponential backoff.
5. Every delivery is **logged** — status codes, response bodies, and timestamps are persisted for audit.

> **Important**: Webhooks are dispatched from the backend service. Your endpoint must be publicly accessible (or reachable from the ScholarForm AI server). Localhost and private IP addresses are not supported.

The webhook API is available under both **v1** (`/api/v1/webhooks`) and **v2** (`/api/v2/webhooks`). v2 re-exports the v1 router with identical behavior. All examples in this document use the v1 path prefix.

> **Base URL**: `https://api.scholarform.ai` (production) | `http://localhost:8000` (development)
> **Auth**: `Authorization: Bearer <supabase_access_token>`

---

## Event Types

Webhook subscriptions filter events by type. Each subscription can listen for one or more event types. When an event occurs, ScholarForm AI dispatches it to **all active subscriptions** whose event list includes the matching type.

| Event Type | Triggered When |
| --- | --- |
| `document.uploaded` | A manuscript document has been successfully uploaded |
| `document.completed` | Document processing pipeline has finished |
| `document.failed` | Document processing failed |
| `synthesis.started` | Synthesis generation has begun |
| `synthesis.completed` | Synthesis has been generated |
| `synthesis.failed` | Synthesis generation failed |
| `generator.started` | Manuscript formatting has started |
| `generator.completed` | Manuscript formatting completed successfully |
| `generator.failed` | Manuscript formatting failed |
| `test.ping` | Test event dispatched via the test endpoint |

> **Note**: Event types are arbitrary strings matched via PostgREST's `contains` operator on the subscription's event list. The system does not validate event type names — any string is accepted. The events above are the canonical set emitted by the platform.

---

## Subscription Management

All subscription CRUD operations are scoped to the authenticated user. You can only access your own subscriptions.

### Create a Subscription

```
POST /api/v1/webhooks
```

Creates a new webhook subscription. The webhook secret is encrypted at rest before storage.

**Request body:**

```json
{
  "name": "My Production Webhook",
  "url": "https://hooks.example.com/scholarform",
  "events": [
    "document.completed",
    "document.failed",
    "synthesis.completed"
  ],
  "secret": "your-webhook-secret-key"
}
```

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | string | Yes | Human-readable label (1–200 characters) |
| `url` | string (URL) | Yes | HTTPS endpoint to receive webhook payloads |
| `events` | array[string] | Yes | Event types to subscribe to (min 1) |
| `secret` | string | No | Shared secret for HMAC signature generation (max 512 chars) |

**Response (201):**

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "user_id": "user-abc-123",
  "name": "My Production Webhook",
  "url": "https://hooks.example.com/scholarform",
  "events": ["document.completed", "document.failed", "synthesis.completed"],
  "is_active": true,
  "created_at": "2026-07-16T12:00:00Z",
  "updated_at": "2026-07-16T12:00:00Z"
}
```

> **Important**: The `secret` is never returned in API responses. Once set, it is encrypted and only used for outbound payload signing.

**cURL example:**

```bash
curl -X POST https://api.scholarform.ai/api/v1/webhooks \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "CI/CD Notifier",
    "url": "https://hooks.example.com/scholarform",
    "events": ["document.completed", "document.failed"],
    "secret": "whsec_abc123def456"
  }'
```

### List Subscriptions

```
GET /api/v1/webhooks
```

Returns all subscriptions for the authenticated user, ordered by creation date (newest first).

**Response (200):**

```json
{
  "subscriptions": [
    {
      "id": "a1b2c3d4-...",
      "user_id": "user-abc-123",
      "name": "My Production Webhook",
      "url": "https://hooks.example.com/scholarform",
      "events": ["document.completed", "document.failed"],
      "is_active": true,
      "created_at": "2026-07-16T12:00:00Z",
      "updated_at": "2026-07-16T12:00:00Z"
    }
  ],
  "total": 1
}
```

**cURL example:**

```bash
curl https://api.scholarform.ai/api/v1/webhooks \
  -H "Authorization: Bearer <token>"
```

### Get a Subscription

```
GET /api/v1/webhooks/{sub_id}
```

Returns a single subscription by ID. Returns `404` if not found or if the subscription belongs to a different user.

**cURL example:**

```bash
curl https://api.scholarform.ai/api/v1/webhooks/a1b2c3d4-e5f6-7890-abcd-ef1234567890 \
  -H "Authorization: Bearer <token>"
```

### Update a Subscription

```
PUT /api/v1/webhooks/{sub_id}
```

Updates one or more fields of an existing subscription. Only provided fields are updated. To rotate the secret, include a new `secret` value — it will be encrypted before storage.

**Request body (partial update):**

```json
{
  "name": "Updated Webhook Name",
  "events": ["document.completed", "synthesis.completed", "generator.completed"],
  "is_active": true
}
```

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | string | No | New label (1–200 chars) |
| `url` | string (URL) | No | New HTTPS endpoint |
| `events` | array[string] | No | New event type list (min 1 if provided) |
| `is_active` | boolean | No | Enable or disable the subscription |
| `secret` | string | No | Rotate the signing secret |

Returns `404` if the subscription does not exist or belongs to another user. Returns `422` if no update fields are provided.

**cURL example:**

```bash
curl -X PUT https://api.scholarform.ai/api/v1/webhooks/a1b2c3d4-e5f6-7890-abcd-ef1234567890 \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'
```

### Delete a Subscription

```
DELETE /api/v1/webhooks/{sub_id}
```

Deactivates a subscription (soft delete). The subscription's `is_active` flag is set to `false` and the record is retained for audit purposes. Delivery will stop immediately.

Returns `200` with `{"status": "deleted"}` on success, or `404` if the subscription does not exist.

**cURL example:**

```bash
curl -X DELETE https://api.scholarform.ai/api/v1/webhooks/a1b2c3d4-e5f6-7890-abcd-ef1234567890 \
  -H "Authorization: Bearer <token>"
```

---

## Delivery

When an event is triggered, ScholarForm AI dispatches it to all matching subscriptions in a single asynchronous call. Each subscription receives an independent HTTP POST request.

### HTTP Request Format

**Headers:**

| Header | Value | Description |
| --- | --- | --- |
| `Content-Type` | `application/json` | Payload format |
| `X-Webhook-Signature` | `sha256=<hex digest>` | HMAC-SHA256 of the raw JSON body |
| `User-Agent` | `ScholarForm-Webhook/1.0` | Origin identifier |

**Body:**

The request body is a JSON object whose structure depends on the event type. All payloads include the event type context:

```json
{
  "doc_id": "abc-123",
  "status": "completed",
  "timestamp": "2026-07-16T12:00:00Z",
  ...event_specific_fields
}
```

### Retry Policy

If a delivery fails (non-2xx response or network error), ScholarForm AI retries automatically:

| Attempt | Delay Before Retry |
| --- | --- |
| 1st delivery | Immediate |
| 2nd attempt | 120 seconds |
| 3rd attempt | 240 seconds |

- **Maximum retries**: 2 retries after the initial attempt (3 total attempts)
- **Backoff algorithm**: `min(2^attempt * 60, 3600)` seconds, where `attempt` is 1-indexed
- **Cap**: Maximum delay is 3600 seconds (1 hour)
- **Condition**: Retries occur on any non-2xx HTTP status or network error (`httpx.RequestError`)
- **On success**: The retry loop exits immediately — no further attempts are made
- **After exhaustion**: The delivery is marked `failed` in the delivery log with the last response code and body

When a delivery fails, the `next_retry_at` timestamp is calculated and stored in the delivery log, allowing external monitoring to track pending retries.

### Delivery Timeout

Each HTTP POST request has a **10-second timeout** (configured via `httpx.AsyncClient(timeout=10.0)`). If your endpoint does not respond within 10 seconds, the delivery is treated as a failure and triggers a retry.

---

## Signature Verification

Every webhook payload includes an `X-Webhook-Signature` header containing an HMAC-SHA256 hex digest of the raw JSON request body, computed using your subscription's secret.

**Signature algorithm:**

```
signature = HMAC-SHA256(secret, raw_request_body).hexdigest()
```

The `secret` is the plaintext value you provided when creating the subscription. It is encrypted at rest and decrypted only at the moment of signing.

Your endpoint **should** verify every incoming webhook:

1. Read the `X-Webhook-Signature` header value.
2. Recompute the HMAC-SHA256 digest using the shared secret and the raw request body.
3. Compare using a **constant-time comparison** function (not `==`).

### Node.js Verification

```javascript
import crypto from 'crypto';

function verifyWebhookSignature(payload, signature, secret) {
  const computed = crypto
    .createHmac('sha256', secret)
    .update(payload)
    .digest('hex');

  // Constant-time comparison prevents timing attacks
  return crypto.timingSafeEqual(
    Buffer.from(computed),
    Buffer.from(signature)
  );
}

// Usage in an Express handler
app.post('/webhook', express.text({ type: 'application/json' }), (req, res) => {
  const signature = req.headers['x-webhook-signature'];
  const secret = process.env.SCHOLARFORM_WEBHOOK_SECRET;

  if (!verifyWebhookSignature(req.body, signature, secret)) {
    return res.status(401).send('Invalid signature');
  }

  const event = JSON.parse(req.body);
  // Process the event...
  res.status(200).send('OK');
});
```

### Python Verification

```python
import hmac
import hashlib

def verify_webhook_signature(payload: str, signature: str, secret: str) -> bool:
    computed = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    # Constant-time comparison
    return hmac.compare_digest(computed, signature)


# Usage in a FastAPI handler
@app.post("/webhook")
async def handle_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("x-webhook-signature")
    secret = os.environ["SCHOLARFORM_WEBHOOK_SECRET"]

    if not verify_webhook_signature(body.decode(), signature, secret):
        raise HTTPException(status_code=401, detail="Invalid signature")

    event = json.loads(body)
    # Process the event...
    return {"status": "ok"}
```

> **Important**: Always use `hmac.compare_digest` (Python) or `crypto.timingSafeEqual` (Node.js) for comparison. Standard equality operators (`==`) are vulnerable to timing attacks.

---

## Security

### Secret Encryption at Rest

Webhook secrets are encrypted before being stored in the database using the ScholarForm AI encryption service. The encryption is transparent to the API — you provide the plaintext secret on creation or update, and it is encrypted automatically. Secrets are never returned in API responses.

- **Encryption**: AES-based via `EncryptionService.encrypt()`
- **Decryption**: Performed only at the moment of payload signing
- **Error handling**: If decryption fails for a given subscription, that subscription is silently skipped and an error is logged

### Replay Protection

The current implementation does not include built-in replay attack detection. The same event payload dispatched twice will be delivered twice to all matching subscriptions. Future versions will add:

- **Idempotency keys** on dispatched events
- **Timestamps** in the payload for consumer-side window validation
- **Nonce verification** for deduplication

As a consumer-side mitigation, include a `timestamp` field in your webhook handler logic and reject payloads whose timestamp is outside an acceptable window (e.g., 5 minutes).

### Origin Validation

- **User-Agent**: All webhook deliveries include `User-Agent: ScholarForm-Webhook/1.0`
- **Signature verification**: The HMAC-SHA256 signature is the primary origin validation mechanism
- **No IP allowlisting**: ScholarForm AI does not publish a static IP range. Always verify webhooks via the signature header

### SSRF Prevention

- **HTTPS enforcement**: The API schema requires `HttpUrl` for the subscription URL (Pydantic validation)
- **Internal network blocking**: HTTP requests to private IP ranges (10.x.x.x, 172.16-31.x.x, 192.168.x.x, 127.x.x.x) are not explicitly blocked at the service layer — delivery to internal addresses will fail at the HTTP transport layer
- **Production recommendation**: Use a webhook proxy or firewall to restrict outbound traffic if needed

---

## Testing

The webhook system provides a built-in test endpoint that dispatches a simulated event to all matching subscriptions.

```
POST /api/v1/webhooks/test
```

**Request body:**

```json
{
  "event_type": "test.ping",
  "payload": {
    "message": "test"
  }
}
```

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `event_type` | string | `"test.ping"` | The event type to simulate (must match a subscription's subscribed events) |
| `payload` | object | `{"message": "test"}` | Arbitrary JSON payload to include in the delivery |

**Response (200):**

```json
{
  "event_type": "test.ping",
  "delivered_to": 2,
  "message": "Event dispatched to 2 subscription(s)"
}
```

Use this endpoint to:

- Verify your endpoint is reachable and responds correctly
- Validate your signature verification implementation
- Test your event processing logic in a staging environment
- Confirm subscription event filtering works as expected

**cURL example:**

```bash
curl -X POST https://api.scholarform.ai/api/v1/webhooks/test \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "test.ping",
    "payload": {"message": "integration test", "timestamp": "2026-07-16T12:00:00Z"}
  }'
```

---

## Delivery Logs

Every webhook delivery attempt is logged to the `webhook_delivery_logs` table. Logs are visible via the API and provide full audit trail for all dispatches.

```
GET /api/v1/webhooks/{sub_id}/deliveries
```

**Response (200):**

```json
{
  "deliveries": [
    {
      "id": "log-abc-123",
      "subscription_id": "a1b2c3d4-...",
      "event_type": "document.completed",
      "status": "success",
      "response_code": 200,
      "attempted_at": "2026-07-16T12:00:00Z"
    },
    {
      "id": "log-def-456",
      "subscription_id": "a1b2c3d4-...",
      "event_type": "document.completed",
      "status": "failed",
      "response_code": 500,
      "attempted_at": "2026-07-16T12:00:05Z"
    }
  ],
  "total": 2
}
```

**Delivery log fields:**

| Field | Type | Description |
| --- | --- | --- |
| `id` | string | Unique log entry identifier |
| `subscription_id` | string | The subscription that received this delivery |
| `event_type` | string | The event type that was dispatched |
| `payload` | string | The full JSON payload sent to the endpoint |
| `status` | string | `"success"` or `"failed"` |
| `response_code` | integer | HTTP status code returned by your endpoint (0 on network error) |
| `response_body` | string | Response body from your endpoint (truncated to 2000 characters) |
| `attempted_at` | string | ISO 8601 timestamp of the delivery attempt |
| `next_retry_at` | number | Unix timestamp of the next scheduled retry (`null` if final attempt) |

**Logging behavior:**

- A delivery is logged after all retry attempts are exhausted or on first success
- The response body is truncated to 2000 characters for storage efficiency
- On network errors (`httpx.RequestError`), the response code is 0 and the response body contains the error message
- Failed log insertion does not affect the delivery itself — delivery continues even if the log write fails

**cURL example:**

```bash
curl https://api.scholarform.ai/api/v1/webhooks/a1b2c3d4-e5f6-7890-abcd-ef1234567890/deliveries \
  -H "Authorization: Bearer <token>"
```

---

## Rate Limits

Webhook dispatch is subject to the same rate limits as the rest of the ScholarForm AI API:

| Tier | General Rate | Description |
| --- | --- | --- |
| Free | 60 requests/min | Standard sliding-window rate limit |
| Pro | 300 requests/min | Higher throughput for production workloads |
| Health | Unlimited | Health endpoints exempt |

Rate limiting applies to the **subscription management API** (CRUD endpoints). Webhook **delivery** events are dispatched asynchronously from the backend service and are not subject to per-endpoint rate limits.

> **Note**: There is no per-webhook delivery rate cap in the current implementation. Mitigations for runaway delivery loops will be added in a future release.

---

## Configuration

Webhook behavior is configured through environment variables in the backend service:

| Variable | Default | Description |
| --- | --- | --- |
| `STRIPE_WEBHOOK_SECRET` | `mock-webhook` | Stripe incoming webhook secret (for billing, not related to outgoing event webhooks) |
| `ENCRYPTION_KEY` | (required) | Base64-encoded 32-byte key for encrypting webhook secrets at rest |

There are no webhook-specific environment variables for the outgoing event system. The following are hardcoded in the `WebhookService`:

| Parameter | Value | Location |
| --- | --- | --- |
| Delivery timeout | 10 seconds | `httpx.AsyncClient(timeout=10.0)` in `_deliver()` |
| Max retries | 2 retries (3 total attempts) | `for attempt in range(3)` in `dispatch_event()` |
| Backoff base | `min(2^attempt * 60, 3600)` seconds | `_calculate_retry_delay()` |
| Response body truncation | 2000 characters | `response_body[:2000]` in log entry |
| User-Agent | `ScholarForm-Webhook/1.0` | Delivery HTTP header |
| Database tables | `webhook_subscriptions`, `webhook_delivery_logs` | Supabase/PostgreSQL |
| Delivery log limit | 50 entries per query | `.limit(50)` in `get_deliveries()` |

---

## Database Schema

The webhook system uses two database tables:

### `webhook_subscriptions`

| Column | Type | Description |
| --- | --- | --- |
| `id` | uuid | Primary key |
| `user_id` | uuid | Owner of the subscription |
| `name` | varchar(200) | Human-readable label |
| `url` | text | HTTPS endpoint URL |
| `events` | jsonb | Array of subscribed event type strings |
| `secret` | text | Encrypted HMAC signing secret |
| `is_active` | boolean | Whether the subscription is active |
| `created_at` | timestamptz | Creation timestamp |
| `updated_at` | timestamptz | Last update timestamp |

### `webhook_delivery_logs`

| Column | Type | Description |
| --- | --- | --- |
| `id` | uuid | Primary key |
| `subscription_id` | uuid | FK to `webhook_subscriptions.id` |
| `event_type` | varchar | The dispatched event type |
| `payload` | text | Full JSON payload |
| `status` | varchar | `success` or `failed` |
| `response_code` | integer | HTTP status code (0 on network error) |
| `response_body` | text | Truncated response (max 2000 chars) |
| `attempted_at` | timestamptz | Delivery timestamp |
| `next_retry_at` | timestamptz | Next scheduled retry (null if final) |

---

## See Also

- [API Reference](API.md) — Complete API documentation with all endpoint examples
- [API Versioning](archive/API_VERSIONING.md) — Version policy and lifecycle
- [Configuration Reference](CONFIGURATION_REFERENCE.md) — All environment variables
- [Security Architecture](SECURITY_ARCHITECTURE.md) — Platform security overview
- [Disaster Recovery](DISASTER_RECOVERY.md) — DR procedures including webhook delivery guarantees
- [Architecture Overview](architecture.md) — System architecture
- [OPERATIONS_RUNBOOK.md](OPERATIONS_RUNBOOK.md) — Operational procedures for webhook delivery monitoring
