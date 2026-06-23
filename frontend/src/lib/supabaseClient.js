// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

// Guard — do not call Supabase client factory with undefined args (crashes at runtime).
// Export null when env vars are missing; callers handle null gracefully.
if (!supabaseUrl || !supabaseAnonKey) {
    console.error('[Supabase] Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY. Auth and DB features will not work.');
}

// Use createClient from @supabase/supabase-js with default auth config.
//
// IMPORTANT: Do NOT set `storage: typeof window !== 'undefined' ? window.localStorage : undefined`.
// supabaseClient.js is imported at module evaluation time; in Next.js this can happen during SSR
// before `window` exists, resulting in `storage: undefined` → Supabase falls back to in-memory
// storage → sessions are lost on every page reload.
//
// createClient already uses localStorage automatically when running in a browser context.
// Let Supabase handle storage detection — do not override it manually.
export const supabase = (supabaseUrl && supabaseAnonKey)
    ? createClient(supabaseUrl, supabaseAnonKey)
    : null;
