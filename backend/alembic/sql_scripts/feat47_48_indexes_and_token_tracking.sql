-- FEAT 47: Database indexes and constraints for performance
-- Run this SQL in your Supabase SQL editor or via a migration.

-- ── Performance Indexes ────────────────────────────────────────────────────────

-- Speed up document listing by user
CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);

-- Speed up status-based filtering
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);

-- Speed up template-based filtering
CREATE INDEX IF NOT EXISTS idx_documents_template ON documents(template);

-- Speed up date range queries
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at DESC);

-- Speed up result lookups by document
CREATE INDEX IF NOT EXISTS idx_document_results_doc_id ON document_results(document_id);

-- Speed up processing status lookups
CREATE INDEX IF NOT EXISTS idx_processing_status_doc_id ON processing_status(document_id);
CREATE INDEX IF NOT EXISTS idx_processing_status_phase ON processing_status(document_id, phase);

-- ── Foreign Key Constraints ────────────────────────────────────────────────────

-- document_results → documents (if not already present)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_document_results_document_id'
    ) THEN
        ALTER TABLE document_results
        ADD CONSTRAINT fk_document_results_document_id
        FOREIGN KEY (document_id)
        REFERENCES documents(id)
        ON DELETE CASCADE;
    END IF;
END $$;

-- processing_status → documents (if not already present)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_processing_status_document_id'
    ) THEN
        ALTER TABLE processing_status
        ADD CONSTRAINT fk_processing_status_document_id
        FOREIGN KEY (document_id)
        REFERENCES documents(id)
        ON DELETE CASCADE;
    END IF;
END $$;

-- ── Token Usage Tracking Table (FEAT 48) ───────────────────────────────────────

CREATE TABLE IF NOT EXISTS llm_token_usage (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    model VARCHAR(100) NOT NULL,
    provider VARCHAR(50) NOT NULL DEFAULT 'unknown',
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER GENERATED ALWAYS AS (prompt_tokens + completion_tokens) STORED,
    estimated_cost_usd NUMERIC(10, 6) DEFAULT 0,
    stage VARCHAR(50),  -- e.g., 'analysis', 'validation', 'formatting'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_llm_token_usage_doc_id ON llm_token_usage(document_id);
CREATE INDEX IF NOT EXISTS idx_llm_token_usage_model ON llm_token_usage(model);
CREATE INDEX IF NOT EXISTS idx_llm_token_usage_created_at ON llm_token_usage(created_at DESC);
