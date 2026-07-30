# ScholarForm AI — Database Schema Reference

## Overview

ScholarForm AI uses a multi-store persistence architecture anchored by **Supabase PostgreSQL (v15+)** for relational data, transaction management, user accounting, and audit tracking. Complementary stores include **Redis** (caching, rate limiting, and Celery task broker) and **ChromaDB** (vector embeddings for publisher guidelines and RAG sessions).

---

## Entity-Relationship Diagram (ERD)

The ERD below details all relational tables in the Supabase PostgreSQL database and their foreign key relationships:

```mermaid
erDiagram
    auth_users ||--o| profiles : "id -> id("PK/FK")"
    profiles ||--o{ documents : "id -> user_id"
    profiles ||--o{ user_api_keys : "id -> user_id"
    profiles ||--o{ custom_providers : "id -> user_id"
    profiles ||--o{ suggestions : "id -> user_id"
    profiles ||--o{ generator_sessions : "id -> user_id"
    profiles ||--o{ webhook_subscriptions : "id -> user_id"
    profiles ||--o{ audit_log : "id -> user_id"

    documents ||--o{ document_versions : "id -> document_id"
    documents ||--o| document_results : "id -> document_id"
    documents ||--o{ processing_status : "id -> document_id"
    documents ||--o{ document_shares : "id -> document_id"
    documents ||--o{ suggestions : "id -> document_id"

    generator_sessions ||--o{ generator_messages : "session_id -> session_id"
    generator_sessions ||--o{ generator_documents : "session_id -> session_id"

    user_api_keys ||--o{ api_key_usage_log : "id -> user_api_key_id"

    webhook_subscriptions ||--o{ webhook_delivery_logs : "id -> subscription_id"
```

---

## Detailed Table Reference

### 1. `profiles` — User Account Profiles

Extends Supabase `auth.users` with billing tiers, profile details, and role specifications.

| Column Name | Data Type | Nullable | Constraints & Defaults | Description |
| ------------- | ----------- | ---------- | ------------------------ | ------------- |
| `id` | `UUID` | No | `PRIMARY KEY`, `FK -> auth.users(id) ON DELETE CASCADE` | Mirrors Supabase Auth User ID. |
| `email` | `TEXT` | Yes | Indexed | User primary email address. |
| `full_name` | `TEXT` | Yes | — | Display name of the user. |
| `institution` | `TEXT` | Yes | — | Academic or corporate organization. |
| `role` | `TEXT` | No | `DEFAULT 'authenticated'` | User RBAC role (`admin`, `pro`, `free`). |
| `plan_tier` | `TEXT` | No | `DEFAULT 'free'` | Subscription tier (`free`, `pro`, `enterprise`). |
| `stripe_customer_id` | `TEXT` | Yes | — | External Stripe customer identifier. |
| `billing_status` | `TEXT` | Yes | — | Billing account state (`active`, `past_due`). |
| `created_at` | `TIMESTAMPTZ` | No | `DEFAULT NOW()` | Timestamp of profile creation. |
| `updated_at` | `TIMESTAMPTZ` | No | `DEFAULT NOW()` | Auto-updated on record modification. |

- **Indexes**: `idx_profiles_email` on `email` (B-tree).

---

### 2. `documents` — Core Document Processing Jobs

Stores document formatting job metadata, upload status, file paths, and current pipeline stages.

| Column Name | Data Type | Nullable | Constraints & Defaults | Description |
| ------------- | ----------- | ---------- | ------------------------ | ------------- |
| `id` | `UUID` | No | `PRIMARY KEY DEFAULT gen_random_uuid()` | Unique document job identifier. |
| `user_id` | `UUID` | Yes | Indexed | Owner user ID (`auth.users.id`). |
| `filename` | `TEXT` | No | — | Original uploaded file name. |
| `template` | `TEXT` | Yes | — | Target style template slug (e.g., `"ieee"`). |
| `status` | `TEXT` | No | `DEFAULT 'RUNNING'` | Overall job state (`RUNNING`, `COMPLETED`, `FAILED`). |
| `original_file_path` | `TEXT` | Yes | — | Absolute path to uploaded raw document. |
| `raw_text` | `TEXT` | Yes | — | Full extracted plain text content. |
| `output_path` | `TEXT` | Yes | — | Path to generated output artifact (DOCX/PDF). |
| `formatting_options` | `JSONB` | Yes | — | Formatting parameters (line spacing, TOC, etc.). |
| `file_hash` | `TEXT` | Yes | Indexed | SHA-256 hash of original file payload. |
| `progress` | `INTEGER` | Yes | `DEFAULT 0` | Processing completion percentage (0–100). |
| `current_stage` | `TEXT` | Yes | — | Active pipeline stage (e.g., `"NLP_ANALYSIS"`). |
| `error_message` | `TEXT` | Yes | — | Failure error message if job failed. |
| `created_at` | `TIMESTAMPTZ` | No | `DEFAULT NOW()` | Job submission timestamp. |
| `updated_at` | `TIMESTAMPTZ` | No | `DEFAULT NOW()` | Last progress update timestamp. |

- **Indexes**:
    - `idx_documents_user_id` on `user_id`
    - `idx_documents_status` on `status`
    - `idx_documents_created_at` on `created_at DESC`
    - `idx_documents_file_hash` on `file_hash`
    - `idx_documents_user_created` composite on `(user_id, created_at DESC)`
    - `idx_documents_user_updated` composite on `(user_id, updated_at DESC)`
    - `idx_documents_fts` GIN on `to_tsvector('english', raw_text)`

---

### 3. `document_results` — Pipeline Structured Output

Contains parsed document block structures, validation results, and quality summary metrics.

| Column Name | Data Type | Nullable | Constraints & Defaults | Description |
| ------------- | ----------- | ---------- | ------------------------ | ------------- |
| `id` | `UUID` | No | `PRIMARY KEY DEFAULT gen_random_uuid()` | Unique result record ID. |
| `document_id` | `UUID` | No | `FK -> documents(id) ON DELETE CASCADE`, `UNIQUE` | One-to-one relationship with `documents`. |
| `structured_data` | `JSONB` | Yes | — | Parsed manuscript blocks, sections, and references. |
| `validation_results` | `JSONB` | Yes | — | Style rule violations, quality summary, and AI hints. |
| `created_at` | `TIMESTAMPTZ` | No | `DEFAULT NOW()` | Record creation timestamp. |
| `updated_at` | `TIMESTAMPTZ` | No | `DEFAULT NOW()` | Record modification timestamp. |

- **Constraints**: `uq_document_results_document_id` UNIQUE constraint on `document_id`.

---

### 4. `document_versions` — Output Edit Snapshots

Stores historic document version snapshots generated when users apply manual edits in the UI editor.

| Column Name | Data Type | Nullable | Constraints & Defaults | Description |
| ------------- | ----------- | ---------- | ------------------------ | ------------- |
| `id` | `UUID` | No | `PRIMARY KEY DEFAULT gen_random_uuid()` | Unique version ID. |
| `document_id` | `UUID` | No | `FK -> documents(id) ON DELETE CASCADE` | Associated document ID. |
| `version_number` | `TEXT` | No | — | Sequential version tag (e.g., `"v1"`, `"v2"`). |
| `edited_structured_data` | `JSONB` | Yes | — | Structured section snapshot for this version. |
| `output_path` | `TEXT` | Yes | — | File path to rendered version artifact. |
| `created_at` | `TIMESTAMPTZ` | No | `DEFAULT NOW()` | Version snapshot timestamp. |

- **Indexes**: `idx_document_versions_document_id` on `document_id`.

---

### 5. `processing_status` — Per-Phase Pipeline Status

Tracks individual pipeline phase progress (`UPLOAD`, `EXTRACTION`, `NLP_ANALYSIS`, `VALIDATION`, `PERSISTENCE`).

| Column Name | Data Type | Nullable | Constraints & Defaults | Description |
| ------------- | ----------- | ---------- | ------------------------ | ------------- |
| `id` | `UUID` | No | `PRIMARY KEY DEFAULT gen_random_uuid()` | Unique status record ID. |
| `document_id` | `UUID` | No | `FK -> documents(id) ON DELETE CASCADE` | Parent document job ID. |
| `phase` | `TEXT` | No | — | Phase name (`UPLOAD`, `EXTRACTION`, etc.). |
| `status` | `TEXT` | No | — | Phase status (`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`). |
| `progress_percentage` | `INTEGER` | Yes | — | Phase-specific progress (0–100). |
| `message` | `TEXT` | Yes | — | Human-readable phase message. |
| `updated_at` | `TIMESTAMPTZ` | No | `DEFAULT NOW()` | Last phase transition timestamp. |

- **Constraints**: `uq_processing_status_doc_phase` UNIQUE on `(document_id, phase)`.

---

### 6. `suggestions` — AI-Generated Editing Suggestions

Holds AI-proposed manuscript text edits, clarity improvements, and user accept/reject decisions.

| Column Name | Data Type | Nullable | Constraints & Defaults | Description |
| ------------- | ----------- | ---------- | ------------------------ | ------------- |
| `id` | `UUID` | No | `PRIMARY KEY DEFAULT gen_random_uuid()` | Unique suggestion ID. |
| `user_id` | `UUID` | No | Indexed | Requesting user ID. |
| `document_id` | `UUID` | Yes | Indexed | Associated document ID. |
| `session_id` | `TEXT` | Yes | — | Associated generator session ID. |
| `original_text` | `TEXT` | No | — | Source text targeting modification. |
| `suggested_text` | `TEXT` | No | — | AI-recommended replacement text. |
| `suggestion_type` | `TEXT` | No | — | Type (`"clarity"`, `"grammar"`, `"style"`). |
| `score` | `FLOAT` | No | `DEFAULT 0.0` | Confidence score (0.0–1.0). |
| `status` | `TEXT` | No | `DEFAULT 'pending'` | Decision state (`pending`, `accepted`, `rejected`). |
| `context` | `JSONB` | Yes | — | Surrounding paragraph context metadata. |
| `created_at` | `TIMESTAMPTZ` | No | `DEFAULT NOW()` | Suggestion creation timestamp. |
| `updated_at` | `TIMESTAMPTZ` | No | `DEFAULT NOW()` | Modification timestamp. |
| `accepted_at` | `TIMESTAMPTZ` | Yes | — | Timestamp when accepted by user. |

---

### 7. `user_api_keys` — Encrypted User LLM Keys

Stores Bring-Your-Own-Key (BYOK) credentials for custom LLM integration.

| Column Name | Data Type | Nullable | Constraints & Defaults | Description |
| ------------- | ----------- | ---------- | ------------------------ | ------------- |
| `id` | `UUID` | No | `PRIMARY KEY DEFAULT gen_random_uuid()` | Unique key record ID. |
| `user_id` | `UUID` | No | Indexed | Owner user ID. |
| `provider` | `VARCHAR(50)` | No | Indexed | Provider slug (`"openai"`, `"anthropic"`, `"groq"`). |
| `api_key_encrypted` | `TEXT` | No | — | Fernet AES-256 encrypted API key string. |
| `key_label` | `VARCHAR(100)` | Yes | — | User-defined label for the key. |
| `is_active` | `BOOLEAN` | No | `DEFAULT TRUE` | Active/deactivated flag. |
| `rate_limit_per_minute` | `INTEGER` | No | `DEFAULT 60` | Max requests per minute. |
| `rate_limit_per_hour` | `INTEGER` | No | `DEFAULT 1000` | Max requests per hour. |
| `daily_quota` | `INTEGER` | No | `DEFAULT 10000` | Max daily token/request quota. |
| `total_requests` | `INTEGER` | No | `DEFAULT 0` | Cumulative request counter. |
| `last_request_at` | `TIMESTAMPTZ` | Yes | — | Timestamp of last API key usage. |
| `created_at` | `TIMESTAMPTZ` | No | `DEFAULT NOW()` | Creation timestamp. |
| `updated_at` | `TIMESTAMPTZ` | No | `DEFAULT NOW()` | Last update timestamp. |

---

### 8. `api_key_usage_log` — Per-Key Telemetry & Audit

Tracks execution metric logs for every request authorized by user API keys.

| Column Name | Data Type | Nullable | Constraints & Defaults | Description |
| ------------- | ----------- | ---------- | ------------------------ | ------------- |
| `id` | `UUID` | No | `PRIMARY KEY DEFAULT gen_random_uuid()` | Log entry ID. |
| `user_api_key_id` | `UUID` | No | `FK -> user_api_keys(id) ON DELETE CASCADE` | Target API key ID. |
| `endpoint` | `VARCHAR(200)` | Yes | — | API path invoked. |
| `model` | `VARCHAR(100)` | Yes | — | LLM model invoked. |
| `tokens_used` | `INTEGER` | Yes | — | Total token consumption count. |
| `status_code` | `INTEGER` | Yes | — | HTTP status code returned. |
| `response_time_ms` | `INTEGER` | Yes | — | Request execution latency in ms. |
| `created_at` | `TIMESTAMPTZ` | No | `DEFAULT NOW()` | Usage event timestamp. |

- **Indexes**: `ix_api_key_usage_log_created_at` on `created_at`.

---

### 9. `custom_providers` — Custom LLM Endpoint Declarations

Configures custom self-hosted or proxy OpenAI-compatible API base URLs.

| Column Name | Data Type | Nullable | Constraints & Defaults | Description |
| ------------- | ----------- | ---------- | ------------------------ | ------------- |
| `id` | `UUID` | No | `PRIMARY KEY DEFAULT gen_random_uuid()` | Custom provider record ID. |
| `user_id` | `UUID` | No | Indexed | Owner user ID. |
| `name` | `VARCHAR(100)` | No | — | User-visible display name. |
| `base_url` | `VARCHAR(500)` | No | — | Endpoint API base URL. |
| `api_key_encrypted` | `TEXT` | Yes | — | Optional Fernet-encrypted authorization key. |
| `models` | `JSONB` | No | `DEFAULT '[]'` | Supported model names array. |
| `is_local` | `BOOLEAN` | No | `DEFAULT FALSE` | Flag for local Ollama instances. |
| `description` | `VARCHAR(500)` | Yes | — | Description of custom provider. |
| `is_active` | `BOOLEAN` | No | `DEFAULT TRUE` | Soft-delete status. |
| `created_at` | `TIMESTAMPTZ` | No | `DEFAULT NOW()` | Record creation timestamp. |
| `updated_at` | `TIMESTAMPTZ` | No | `DEFAULT NOW()` | Record modification timestamp. |

---

### 10. `generator_sessions` — AI Manuscript Authoring Sessions

Manages state for AI manuscript generation workflows.

| Column Name | Data Type | Nullable | Constraints & Defaults | Description |
| ------------- | ----------- | ---------- | ------------------------ | ------------- |
| `id` | `UUID` | No | `PRIMARY KEY DEFAULT gen_random_uuid()` | Generator session ID. |
| `user_id` | `TEXT` | Yes | — | User ID string. |
| `session_type` | `TEXT` | No | `DEFAULT 'agent'` | Session mode (`agent`, `multi_doc`). |
| `status` | `TEXT` | No | `DEFAULT 'pending'` | Session status (`pending`, `running`, `completed`). |
| `progress` | `INTEGER` | No | `DEFAULT 0` | Generation progress (0–100). |
| `config_json` | `JSONB` | Yes | — | Generation prompt and configuration settings. |
| `outline_json` | `JSONB` | Yes | — | Approved document outline tree. |
| `created_at` | `TIMESTAMPTZ` | No | `DEFAULT NOW()` | Session start timestamp. |
| `updated_at` | `TIMESTAMPTZ` | No | `DEFAULT NOW()` | Last activity timestamp. |

---

### 11. `generator_messages` — AI Authoring Chat Messages

Stores conversational exchanges during manuscript generation sessions.

| Column Name | Data Type | Nullable | Constraints & Defaults | Description |
| ------------- | ----------- | ---------- | ------------------------ | ------------- |
| `id` | `UUID` | No | `PRIMARY KEY DEFAULT gen_random_uuid()` | Message ID. |
| `session_id` | `UUID` | No | `FK -> generator_sessions(id) ON DELETE CASCADE` | Associated generator session ID. |
| `role` | `TEXT` | No | — | Message sender role (`user`, `assistant`, `system`). |
| `content` | `TEXT` | No | — | Full message body. |
| `token_count` | `INTEGER` | Yes | — | Estimated token count. |
| `created_at` | `TIMESTAMPTZ` | No | `DEFAULT NOW()` | Message timestamp. |

- **Indexes**: `ix_generator_messages_session_id` on `session_id`.

---

### 12. `generator_documents` — Generated Document Revisions

Holds generated manuscript text artifacts produced by authoring sessions.

| Column Name | Data Type | Nullable | Constraints & Defaults | Description |
| ------------- | ----------- | ---------- | ------------------------ | ------------- |
| `id` | `UUID` | No | `PRIMARY KEY DEFAULT gen_random_uuid()` | Generated document ID. |
| `session_id` | `UUID` | No | `FK -> generator_sessions(id) ON DELETE CASCADE` | Parent session ID. |
| `content_json` | `JSONB` | Yes | — | Full manuscript JSON content. |
| `docx_path` | `TEXT` | Yes | — | Path to rendered DOCX file. |
| `version_number` | `INTEGER` | No | `DEFAULT 1` | Generation revision number. |
| `created_at` | `TIMESTAMPTZ` | No | `DEFAULT NOW()` | Document creation timestamp. |

---

### 13. `audit_log` — System Security Audit Trail

Records security events, authentication attempts, API key creations, and document deletions.

| Column Name | Data Type | Nullable | Constraints & Defaults | Description |
| ------------- | ----------- | ---------- | ------------------------ | ------------- |
| `id` | `UUID` | No | `PRIMARY KEY DEFAULT gen_random_uuid()` | Audit record ID. |
| `user_id` | `TEXT` | Yes | Indexed | Performing user ID or system actor. |
| `action` | `TEXT` | No | — | Action slug (e.g., `"document.delete"`). |
| `resource_type` | `TEXT` | No | — | Target entity (`"document"`, `"user_api_key"`). |
| `resource_id` | `TEXT` | Yes | — | Target entity ID. |
| `ip_address` | `TEXT` | Yes | — | Client IP address. |
| `details` | `JSONB` | Yes | — | Event context details payload. |
| `created_at` | `TIMESTAMPTZ` | No | `DEFAULT NOW()` | Event logging timestamp. |

- **Indexes**:
    - `idx_audit_log_user_id` on `user_id`
    - `idx_audit_log_timestamp` on `created_at DESC`
    - `idx_audit_log_resource` composite on `(resource_type, resource_id)`

---

### 14. `webhook_subscriptions` — Outgoing Webhook Registrations

Manages client webhook subscriptions for processing event notifications.

| Column Name | Data Type | Nullable | Constraints & Defaults | Description |
| ------------- | ----------- | ---------- | ------------------------ | ------------- |
| `id` | `UUID` | No | `PRIMARY KEY DEFAULT gen_random_uuid()` | Webhook subscription ID. |
| `user_id` | `UUID` | No | Indexed | Subscriber user ID. |
| `name` | `TEXT` | No | — | Webhook description label. |
| `url` | `TEXT` | No | — | Target HTTP endpoint URL. |
| `events` | `JSONB` | No | — | Event array (e.g., `["document.completed"]`). |
| `secret` | `TEXT` | No | `DEFAULT ''` | HMAC signing secret key. |
| `is_active` | `BOOLEAN` | No | `DEFAULT TRUE` | Active/paused status. |
| `created_at` | `TIMESTAMPTZ` | No | `DEFAULT NOW()` | Registration timestamp. |
| `updated_at` | `TIMESTAMPTZ` | No | `DEFAULT NOW()` | Modification timestamp. |

- **Indexes**:
    - `idx_webhook_subs_user_id` on `user_id`
    - `idx_webhook_subs_active_events` GIN on `(is_active, events)`

---

### 15. `webhook_delivery_logs` — Webhook Dispatch Delivery History

Logs HTTP delivery attempts for outgoing webhooks.

| Column Name | Data Type | Nullable | Constraints & Defaults | Description |
| ------------- | ----------- | ---------- | ------------------------ | ------------- |
| `id` | `UUID` | No | `PRIMARY KEY DEFAULT gen_random_uuid()` | Log entry ID. |
| `subscription_id` | `UUID` | No | `FK -> webhook_subscriptions(id) ON DELETE CASCADE` | Associated subscription ID. |
| `event_type` | `TEXT` | No | — | Event type dispatched. |
| `payload` | `TEXT` | No | — | Serialized JSON payload string. |
| `status` | `TEXT` | No | — | Status (`"success"`, `"failed"`, `"retrying"`). |
| `response_code` | `INTEGER` | No | — | Target HTTP response status code. |
| `response_body` | `TEXT` | No | `DEFAULT ''` | Response snippet. |
| `attempted_at` | `TIMESTAMPTZ` | No | `DEFAULT NOW()` | Dispatch attempt timestamp. |
| `next_retry_at` | `TIMESTAMPTZ` | Yes | — | Scheduled timestamp for next retry. |

- **Indexes**: `idx_webhook_delivery_sub_attempted` composite on `(subscription_id, attempted_at DESC)`.

---

### 16. `document_shares` — Collaborative Document Permissions

Controls multi-user access permissions for shared document editing and viewing.

| Column Name | Data Type | Nullable | Constraints & Defaults | Description |
| ------------- | ----------- | ---------- | ------------------------ | ------------- |
| `id` | `UUID` | No | `PRIMARY KEY DEFAULT gen_random_uuid()` | Share record ID. |
| `document_id` | `UUID` | No | `FK -> documents(id) ON DELETE CASCADE` | Shared document ID. |
| `shared_with_user_id` | `TEXT` | No | Indexed | Recipient user ID string. |
| `permission` | `TEXT` | No | `DEFAULT 'view'` | Permission level (`"view"`, `"edit"`). |
| `shared_by_user_id` | `TEXT` | No | — | Granting user ID string. |
| `created_at` | `TIMESTAMPTZ` | No | `DEFAULT NOW()` | Grant timestamp. |
| `updated_at` | `TIMESTAMPTZ` | No | `DEFAULT NOW()` | Modification timestamp. |

- **Constraints**: `uq_document_shares` UNIQUE constraint on `(document_id, shared_with_user_id)`.

---

## Row Level Security (RLS) Policies

All user-facing tables in Supabase PostgreSQL enforce Row Level Security (RLS). Policies ensure that users can only access resources they own or have explicit sharing permissions for.

```sql
-- Enable RLS on core tables
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE custom_providers ENABLE ROW LEVEL SECURITY;
ALTER TABLE suggestions ENABLE ROW LEVEL SECURITY;
ALTER TABLE generator_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE webhook_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_shares ENABLE ROW LEVEL SECURITY;

-- Profiles Policies
CREATE POLICY "Users can read own profile" ON profiles
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON profiles
    FOR UPDATE USING (auth.uid() = id);

-- Documents Policies
CREATE POLICY "Users can select own documents" ON documents
    FOR SELECT USING (
        auth.uid() = user_id OR
        auth.uid()::text IN (
            SELECT shared_with_user_id FROM document_shares WHERE document_id = id
        )
    );

CREATE POLICY "Users can insert own documents" ON documents
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own documents" ON documents
    FOR UPDATE USING (
        auth.uid() = user_id OR
        auth.uid()::text IN (
            SELECT shared_with_user_id FROM document_shares 
            WHERE document_id = id AND permission = 'edit'
        )
    );

CREATE POLICY "Users can delete own documents" ON documents
    FOR DELETE USING (auth.uid() = user_id);

-- User API Keys Policies
CREATE POLICY "Users manage own api keys" ON user_api_keys
    FOR ALL USING (auth.uid() = user_id);

-- Service Role Override
-- Server-side background workers and FastAPI services connect using SUPABASE_SERVICE_ROLE_KEY
-- which bypasses RLS policies to execute system operations across tenant boundaries.
```

---

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) — System topology and security architecture.
- [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) — Subsystem detailed design and RAG flowcharts.
- [PIPELINE.md](PIPELINE.md) — Document processing pipeline sequence diagram.

---

*Last updated: July 2026*
