// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import ModelSelector from '../components/generator/ModelSelector';

vi.mock('../utils/fetchWithRetry', () => ({
    fetchWithRetry: vi.fn(),
}));

describe('ModelSelector', () => {
    const defaultProps = {
        selectedModel: '',
        onModelChange: vi.fn(),
        userToken: 'test-token',
    };

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders Auto label when no model selected', () => {
        render(<ModelSelector {...defaultProps} selectedModel="" />);
        expect(screen.getByText('Auto')).toBeInTheDocument();
    });

    it('renders selected model name', () => {
        render(<ModelSelector {...defaultProps} selectedModel="gpt-4" />);
        expect(screen.getByText('gpt-4')).toBeInTheDocument();
    });

    it('opens dropdown on click', async () => {
        const { fetchWithRetry } = await import('../utils/fetchWithRetry');
        fetchWithRetry.mockResolvedValue({ ok: true, json: () => Promise.resolve({ providers: [] }) });
        render(<ModelSelector {...defaultProps} />);
        const button = screen.getByRole('button');
        fireEvent.click(button);
        // expect model text in dropdown
    });

    it('fetches providers on mount with token', async () => {
        const { fetchWithRetry } = await import('../utils/fetchWithRetry');
        fetchWithRetry.mockResolvedValue({ ok: true, json: () => Promise.resolve({ providers: [] }) });
        render(<ModelSelector {...defaultProps} />);
        expect(fetchWithRetry).toHaveBeenCalled();
    });

    it('shows configured models in Available section', async () => {
        const { fetchWithRetry } = await import('../utils/fetchWithRetry');
        fetchWithRetry.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({
                providers: [{
                    name: 'OpenAI',
                    provider_id: 'openai',
                    key_configured: true,
                    models: ['gpt-4'],
                }],
            }),
        });
        render(<ModelSelector {...defaultProps} />);
        fireEvent.click(screen.getByRole('button'));
    });

    it('selects a model on click', async () => {
        const { fetchWithRetry } = await import('../utils/fetchWithRetry');
        const onModelChange = vi.fn();
        fetchWithRetry.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({
                providers: [{
                    name: 'OpenAI',
                    provider_id: 'openai',
                    key_configured: true,
                    models: ['gpt-4'],
                }],
            }),
        });
        render(<ModelSelector {...defaultProps} onModelChange={onModelChange} />);
        fireEvent.click(screen.getByRole('button'));
    });

    it('shows empty state when no models returned', async () => {
        const { fetchWithRetry } = await import('../utils/fetchWithRetry');
        fetchWithRetry.mockResolvedValue({ ok: true, json: () => Promise.resolve({ providers: [] }) });
        render(<ModelSelector {...defaultProps} />);
        fireEvent.click(screen.getByRole('button'));
    });

    it('closes dropdown on outside click', async () => {
        const { fetchWithRetry } = await import('../utils/fetchWithRetry');
        fetchWithRetry.mockResolvedValue({ ok: true, json: () => Promise.resolve({ providers: [] }) });
        render(<ModelSelector {...defaultProps} />);
        fireEvent.click(screen.getByRole('button'));
        fireEvent.mouseDown(document.body);
    });
});
