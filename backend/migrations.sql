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
