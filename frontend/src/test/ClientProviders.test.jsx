import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import ClientProviders from '../components/layout/ClientProviders';

vi.mock('@/context/ThemeContext', () => ({
    ThemeProvider: ({ children }) => <div data-testid="theme">{children}</div>,
}));

vi.mock('@/context/AuthContext', () => ({
    AuthProvider: ({ children }) => <div data-testid="auth">{children}</div>,
}));

vi.mock('@/context/ToastContext', () => ({
    ToastProvider: ({ children }) => <div data-testid="toast">{children}</div>,
}));

vi.mock('@/context/DocumentContext', () => ({
    DocumentProvider: ({ children }) => <div data-testid="document">{children}</div>,
}));

vi.mock('@/context/UserPreferencesContext', () => ({
    UserPreferencesProvider: ({ children }) => <div data-testid="prefs">{children}</div>,
}));

vi.mock('@/components/layout/FocusManager', () => ({
    default: () => <div data-testid="focus" />,
}));

vi.mock('@/components/layout/DynamicMeta', () => ({
    default: () => <div data-testid="meta" />,
}));

describe('ClientProviders', () => {
    it('wraps children with all providers', () => {
        render(<ClientProviders><p>Content</p></ClientProviders>);
        expect(screen.getByTestId('theme')).toBeInTheDocument();
        expect(screen.getByTestId('auth')).toBeInTheDocument();
        expect(screen.getByTestId('toast')).toBeInTheDocument();
        expect(screen.getByTestId('document')).toBeInTheDocument();
        expect(screen.getByTestId('prefs')).toBeInTheDocument();
        expect(screen.getByTestId('focus')).toBeInTheDocument();
        expect(screen.getByTestId('meta')).toBeInTheDocument();
        expect(screen.getByText('Content')).toBeInTheDocument();
    });
});
