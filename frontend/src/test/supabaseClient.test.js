import { describe, it, expect, vi, beforeEach } from 'vitest';

describe('supabaseClient', () => {
    const OLD_ENV = process.env;

    beforeEach(() => {
        vi.resetModules();
        process.env = { ...OLD_ENV };
    });

    it('exports null when env vars are missing', async () => {
        delete process.env.NEXT_PUBLIC_SUPABASE_URL;
        delete process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

        const { supabase } = await import('../lib/supabaseClient');
        expect(supabase).toBeNull();
    });

    it('creates client when env vars are present', async () => {
        process.env.NEXT_PUBLIC_SUPABASE_URL = 'https://test.supabase.co';
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = 'test-anon-key';

        const { supabase } = await import('../lib/supabaseClient');
        expect(supabase).not.toBeNull();
        expect(supabase).toBeDefined();
    });
});
