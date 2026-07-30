-- Migration: Create Model Metrics and AB Testing Tables
-- Run this in the Supabase SQL Editor

CREATE TABLE IF NOT EXISTS public.model_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name TEXT NOT NULL,
    latency_ms REAL NOT NULL,
    success BOOLEAN NOT NULL DEFAULT true,
    quality_score REAL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for fast time-series dashboard queries
CREATE INDEX IF NOT EXISTS idx_model_metrics_timestamp ON public.model_metrics (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_model_metrics_model ON public.model_metrics (model_name);

CREATE TABLE IF NOT EXISTS public.ab_test_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nvidia_latency REAL,
    deepseek_latency REAL,
    nvidia_success BOOLEAN NOT NULL DEFAULT false,
    deepseek_success BOOLEAN NOT NULL DEFAULT false,
    latency_winner TEXT,
    both_succeeded BOOLEAN NOT NULL DEFAULT false,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for dashboard filtering
CREATE INDEX IF NOT EXISTS idx_ab_test_results_timestamp ON public.ab_test_results (timestamp DESC);

-- Allow authenticated users to view if needed for dashboard (Optional RLS)
-- We enforce security on the API level, but if RLS is enabled:
ALTER TABLE public.model_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ab_test_results ENABLE ROW LEVEL SECURITY;

-- Create policies for service role bypassing (Supabase automatically bypasses RLS for service role,
-- but we allow select for authenticated backend users if needed).
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'model_metrics'
          AND policyname = 'Allow read access to anyone'
    ) THEN
        CREATE POLICY "Allow read access to anyone"
        ON public.model_metrics
        FOR SELECT
        USING (true);
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'ab_test_results'
          AND policyname = 'Allow read access to anyone'
    ) THEN
        CREATE POLICY "Allow read access to anyone"
        ON public.ab_test_results
        FOR SELECT
        USING (true);
    END IF;
END
$$;

-- FIX 47: Indexes for Documents Table Queries
ALTER TABLE public.documents ADD COLUMN IF NOT EXISTS file_hash TEXT;
CREATE INDEX IF NOT EXISTS idx_documents_user_id ON public.documents (user_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON public.documents (status);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON public.documents (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_documents_template ON public.documents (template);
CREATE INDEX IF NOT EXISTS idx_documents_file_hash ON public.documents (file_hash);

-- Enterprise Update Management System Tables (Milestone 1)

CREATE TABLE IF NOT EXISTS public.update_channels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_recommended BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_update_channels_name ON public.update_channels (name);

CREATE TABLE IF NOT EXISTS public.update_releases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version TEXT NOT NULL UNIQUE,
    channel TEXT NOT NULL DEFAULT 'stable',
    release_name TEXT,
    published_at TIMESTAMPTZ,
    download_url TEXT,
    signature_url TEXT,
    checksum_sha256 TEXT,
    signature_ed25519 TEXT,
    signature_rsa TEXT,
    size_bytes BIGINT NOT NULL DEFAULT 0,
    is_mandatory BOOLEAN NOT NULL DEFAULT false,
    is_security BOOLEAN NOT NULL DEFAULT false,
    min_supported_version TEXT,
    changelog_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_update_releases_version ON public.update_releases (version);
CREATE INDEX IF NOT EXISTS idx_update_releases_channel ON public.update_releases (channel);
CREATE INDEX IF NOT EXISTS idx_update_releases_published_at ON public.update_releases (published_at DESC);

CREATE TABLE IF NOT EXISTS public.update_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    device_id TEXT,
    from_version TEXT,
    to_version TEXT NOT NULL,
    channel TEXT NOT NULL DEFAULT 'stable',
    status TEXT NOT NULL DEFAULT 'installed',
    checksum TEXT,
    checksum_type TEXT DEFAULT 'sha256',
    error_message TEXT,
    rolled_back BOOLEAN NOT NULL DEFAULT false,
    rollback_version TEXT,
    installed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_update_history_installed_at ON public.update_history (installed_at DESC);
CREATE INDEX IF NOT EXISTS idx_update_history_user_id ON public.update_history (user_id);
CREATE INDEX IF NOT EXISTS idx_update_history_device_id ON public.update_history (device_id);

CREATE TABLE IF NOT EXISTS public.update_rollback_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    history_id UUID,
    from_version TEXT NOT NULL,
    target_version TEXT NOT NULL,
    backup_path TEXT,
    reason TEXT,
    status TEXT NOT NULL DEFAULT 'success',
    error_message TEXT,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_update_rollback_logs_executed_at ON public.update_rollback_logs (executed_at DESC);

-- Enable RLS for update tables
ALTER TABLE public.update_channels ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.update_releases ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.update_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.update_rollback_logs ENABLE ROW LEVEL SECURITY;

-- Seed default update channels
INSERT INTO public.update_channels (name, description, is_recommended)
VALUES
    ('stable', 'Production-ready releases. Recommended for all users.', true),
    ('beta', 'Pre-release versions with new features. May contain bugs.', false),
    ('nightly', 'Daily builds with latest changes. Unstable.', false),
    ('pre-release', 'Release candidates for testing before stable.', false)
ON CONFLICT (name) DO NOTHING;

