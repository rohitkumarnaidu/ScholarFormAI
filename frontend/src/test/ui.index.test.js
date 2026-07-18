import { describe, it, expect } from 'vitest';

describe('ui/index.ts barrel exports', () => {
    it('exports all UI components', async () => {
        const mod = await import('../components/ui/index');
        expect(mod.Button).toBeDefined();
        expect(mod.Card).toBeDefined();
        expect(mod.Skeleton).toBeDefined();
        expect(mod.EmptyState).toBeDefined();
        expect(mod.Input).toBeDefined();
        expect(mod.Badge).toBeDefined();
        expect(mod.ConfirmDialog).toBeDefined();
    });
});
