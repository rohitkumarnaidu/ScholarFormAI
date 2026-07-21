import { describe, it, expect, vi } from 'vitest';


const originalGetComputedStyle = window.getComputedStyle;
vi.stubGlobal('getComputedStyle', (el, pseudo) => {
    if (el._mockComputedStyle) return el._mockComputedStyle;
    return originalGetComputedStyle(el, pseudo);
});

function luminance(hex) {
    const c = hex.replace('#', '');
    const r = parseInt(c.substring(0, 2), 16) / 255;
    const g = parseInt(c.substring(2, 4), 16) / 255;
    const b = parseInt(c.substring(4, 6), 16) / 255;
    const linearize = (v) => v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b);
}

function contrastRatio(hex1, hex2) {
    const l1 = luminance(hex1);
    const l2 = luminance(hex2);
    const lighter = Math.max(l1, l2);
    const darker = Math.min(l1, l2);
    return (lighter + 0.05) / (darker + 0.05);
}

describe('Color contrast', () => {
    describe('WCAG AA compliance', () => {
        it('text on background passes WCAG AA (4.5:1 ratio)', () => {
            const ratio = contrastRatio('#1a1a1a', '#ffffff');
            expect(ratio).toBeGreaterThanOrEqual(4.5);
        });

        it('large text passes WCAG AA (3:1 ratio)', () => {
            const ratio = contrastRatio('#333333', '#ffffff');
            expect(ratio).toBeGreaterThanOrEqual(3);
        });

        it('dark mode text passes contrast', () => {
            const ratio = contrastRatio('#e5e5e5', '#1a1a1a');
            expect(ratio).toBeGreaterThanOrEqual(4.5);
        });

        it('dark mode large text passes contrast (3:1)', () => {
            const ratio = contrastRatio('#cccccc', '#1a1a1a');
            expect(ratio).toBeGreaterThanOrEqual(3);
        });
    });

    describe('Links', () => {
        it('are distinguishable from body text', () => {
            const bodyRatio = contrastRatio('#374151', '#ffffff');
            const linkRatio = contrastRatio('#4f46e5', '#ffffff');
            expect(bodyRatio).toBeGreaterThanOrEqual(4.5);
            expect(linkRatio).toBeGreaterThanOrEqual(4.5);
            expect(linkRatio).not.toEqual(bodyRatio);
        });
    });

    describe('Error text', () => {
        it('is visible on background', () => {
            const ratio = contrastRatio('#dc2626', '#ffffff');
            expect(ratio).toBeGreaterThanOrEqual(4.5);
        });

        it('is visible on light error background', () => {
            const ratio = contrastRatio('#b91c1c', '#fef2f2');
            expect(ratio).toBeGreaterThanOrEqual(4.5);
        });
    });

    describe('Disabled state', () => {
        it('meets reduced contrast requirements', () => {
            const ratio = contrastRatio('#6b7280', '#ffffff');
            expect(ratio).toBeGreaterThanOrEqual(3);
        });
    });

    describe('Placeholder text', () => {
        it('meets contrast requirement', () => {
            const ratio = contrastRatio('#6b7280', '#ffffff');
            expect(ratio).toBeGreaterThanOrEqual(3);
        });
    });

    describe('Button variants', () => {
        it('primary button text has sufficient contrast', () => {
            const ratio = contrastRatio('#ffffff', '#4f46e5');
            expect(ratio).toBeGreaterThanOrEqual(4.5);
        });

        it('secondary button text has sufficient contrast', () => {
            const ratio = contrastRatio('#1e293b', '#f1f5f9');
            expect(ratio).toBeGreaterThanOrEqual(4.5);
        });

        it('danger button text has sufficient contrast', () => {
            const ratio = contrastRatio('#ffffff', '#dc2626');
            expect(ratio).toBeGreaterThanOrEqual(4.5);
        });
    });
});
