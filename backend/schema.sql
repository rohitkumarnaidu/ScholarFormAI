-- =============================================================================
-- ScholarForm AI — Complete Postgres Schema
-- Target: Supabase (Postgres 15+)
-- Generated: 2026-02-18
--
-- HOW TO USE:
--   1. Open Supabase Dashboard → SQL Editor
--   2. Paste this entire file and run it
--   3. Or run via psql:
--        psql "$SUPABASE_DB_URL" -f schema.sql
--
-- NOTES:
--   - auth.users is managed by Supabase Auth — DO NOT recreate it here.
--   - profiles.id references auth.users(id) via FK.
--   - RLS policies are included but commented out — enable them in the
--     Supabase dashboard or uncomment after verifying service-role access works.
--   - pipeline_jobs table is commented out — it is a nice-to-have for Celery
--     task tracking and can be enabled later.
-- =============================================================================


-- ── Extensions ────────────────────────────────────────────────────────────────

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";


-- ── Helper: auto-update updated_at ────────────────────────────────────────────

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- =============================================================================
-- TABLE: profiles
-- Mirrors Supabase auth.users with extra profile fields.
-- id = auth.users.id (UUID from Supabase Auth)
-- =============================================================================

CREATE TABLE IF NOT EXISTS profiles (
    id              UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email           TEXT,
    full_name       TEXT,
    institution     TEXT,
    role            TEXT NOT NULL DEFAULT 'authenticated',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_profiles_email ON profiles(email);

-- Auto-update updated_at
DROP TRIGGER IF EXISTS trg_profiles_updated_at ON profiles;
CREATE TRIGGER trg_profiles_updated_at
    BEFORE UPDATE ON profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- RLS: Enable after confirming service-role access works
-- ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
--
-- -- Users can read/update their own profile
-- CREATE POLICY "profiles_select_own" ON profiles
--     FOR SELECT USING (auth.uid() = id);
--
-- CREATE POLICY "profiles_update_own" ON profiles
--     FOR UPDATE USING (auth.uid() = id);
--
-- -- Service role can do everything (bypasses RLS automatically)


-- =============================================================================
-- TABLE: documents
-- Core table. One row per uploaded document job.
-- =============================================================================

CREATE TABLE IF NOT EXISTS documents (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    filename            TEXT NOT NULL,
    template            TEXT,
    status              TEXT NOT NULL DEFAULT 'RUNNING',   -- RUNNING | COMPLETED | FAILED
    original_file_path  TEXT,
    raw_text            TEXT,
    output_path         TEXT,
    output_hash         TEXT,
    formatting_options  JSONB,
    file_hash           TEXT,

    -- Job state
    progress            INTEGER DEFAULT 0,                 -- 0-100
    current_stage       TEXT,
    error_message       TEXT,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_documents_user_id   ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_status     ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_documents_file_hash    ON documents(file_hash);
CREATE INDEX IF NOT EXISTS idx_documents_output_hash ON documents(output_hash);

-- Auto-update updated_at
DROP TRIGGER IF EXISTS trg_documents_updated_at ON documents;
CREATE TRIGGER trg_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- RLS: Enable after confirming service-role access works
-- ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
--
-- -- Users can only see their own documents
-- CREATE POLICY "documents_select_own" ON documents
--     FOR SELECT USING (auth.uid() = user_id);
--
-- CREATE POLICY "documents_insert_own" ON documents
--     FOR INSERT WITH CHECK (auth.uid() = user_id);
--
-- CREATE POLICY "documents_update_own" ON documents
--     FOR UPDATE USING (auth.uid() = user_id);
--
-- CREATE POLICY "documents_delete_own" ON documents
--     FOR DELETE USING (auth.uid() = user_id);


-- =============================================================================
-- TABLE: document_versions
-- Stores snapshots of edited structured data per document.
-- =============================================================================

CREATE TABLE IF NOT EXISTS document_versions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id             UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    version_number          TEXT NOT NULL,          -- e.g. "v1", "v2-edited"
    edited_structured_data  JSONB,                  -- Snapshot of what was edited
    output_path             TEXT,                   -- Path to the DOCX/PDF for this version
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_document_versions_document_id ON document_versions(document_id);


-- =============================================================================
-- TABLE: document_results
-- Stores structured pipeline output (sections, citations, validation).
-- =============================================================================

CREATE TABLE IF NOT EXISTS document_results (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id         UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    structured_data     JSONB,          -- Detected sections, citations, references
    validation_results  JSONB,          -- Violations, suggested fixes
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- UNIQUE constraint required for upsert(on_conflict='document_id')
    CONSTRAINT uq_document_results_document_id UNIQUE (document_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_document_results_document_id ON document_results(document_id);


-- =============================================================================
-- TABLE: processing_status
-- Tracks per-phase pipeline progress for a document.
-- =============================================================================

CREATE TABLE IF NOT EXISTS processing_status (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id         UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    phase               TEXT NOT NULL,  -- UPLOAD | EXTRACTION | NLP_ANALYSIS | VALIDATION | PERSISTENCE
    status              TEXT NOT NULL,  -- PENDING | IN_PROGRESS | COMPLETED | FAILED
    progress_percentage INTEGER,        -- 0-100
    message             TEXT,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- UNIQUE constraint required for upsert(on_conflict='document_id,phase')
    CONSTRAINT uq_processing_status_doc_phase UNIQUE (document_id, phase)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_processing_status_document_id ON processing_status(document_id);

-- Auto-update updated_at
DROP TRIGGER IF EXISTS trg_processing_status_updated_at ON processing_status;
CREATE TRIGGER trg_processing_status_updated_at
    BEFORE UPDATE ON processing_status
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- =============================================================================
-- TABLE: pipeline_jobs  [COMMENTED OUT — enable when Celery tracking is needed]
-- Tracks Celery async task state for long-running pipeline jobs.
-- =============================================================================


-- =============================================================================
-- TABLE: model_metrics
-- Stores model latency/success/quality events for dashboard and health checks.
-- =============================================================================

CREATE TABLE IF NOT EXISTS model_metrics (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name    TEXT NOT NULL,
    latency_ms    REAL NOT NULL,
    success       BOOLEAN NOT NULL DEFAULT TRUE,
    quality_score REAL,
    timestamp     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_model_metrics_timestamp ON model_metrics(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_model_metrics_model     ON model_metrics(model_name);

-- CREATE TABLE IF NOT EXISTS pipeline_jobs (
--     id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
--     celery_task_id  TEXT,                   -- Celery task UUID
--     status          TEXT NOT NULL DEFAULT 'PENDING',  -- PENDING | RUNNING | COMPLETED | FAILED
--     error_message   TEXT,
--     started_at      TIMESTAMPTZ,
--     completed_at    TIMESTAMPTZ,
--     created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
--     updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
-- );
--
-- CREATE INDEX IF NOT EXISTS idx_pipeline_jobs_document_id    ON pipeline_jobs(document_id);
-- CREATE INDEX IF NOT EXISTS idx_pipeline_jobs_celery_task_id ON pipeline_jobs(celery_task_id);
--
-- DROP TRIGGER IF EXISTS trg_pipeline_jobs_updated_at ON pipeline_jobs;
-- CREATE TRIGGER trg_pipeline_jobs_updated_at
--     BEFORE UPDATE ON pipeline_jobs
--     FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- =============================================================================
-- DONE
-- Run \dt in psql to verify all tables were created.
-- =============================================================================
