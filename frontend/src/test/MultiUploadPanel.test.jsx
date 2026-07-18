// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import MultiUploadPanel from '../components/generator/MultiUploadPanel';

const { mockGetBuiltinTemplates } = vi.hoisted(() => ({
    mockGetBuiltinTemplates: vi.fn().mockResolvedValue([
        { id: 'ieee', name: 'IEEE' },
        { id: 'nature', name: 'Nature' },
    ]),
}));

vi.mock('../services/api.templates', () => ({
    getBuiltinTemplates: mockGetBuiltinTemplates,
}));

vi.mock('react-dropzone', () => ({
    useDropzone: () => ({
        getRootProps: () => ({}),
        getInputProps: () => ({ type: 'file', multiple: true }),
        isDragActive: false,
    }),
}));

Object.defineProperty(globalThis, 'crypto', {
    value: {
        subtle: {
            digest: vi.fn().mockResolvedValue(new Uint8Array(32).fill(1)),
        },
    },
    writable: true,
});

describe('MultiUploadPanel', () => {
    const onStart = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
        mockGetBuiltinTemplates.mockResolvedValue([
            { id: 'ieee', name: 'IEEE' },
            { id: 'nature', name: 'Nature' },
        ]);
    });

    it('renders upload drop zone', () => {
        render(<MultiUploadPanel onStart={onStart} />);
        expect(screen.getByText(/Drag & Drop documents here/)).toBeInTheDocument();
    });

    it('renders file count limits', () => {
        render(<MultiUploadPanel onStart={onStart} />);
        expect(screen.getByText(/2 to 6 files/)).toBeInTheDocument();
    });

    it('shows Browse Files button', () => {
        render(<MultiUploadPanel onStart={onStart} />);
        expect(screen.getByText('Browse Files')).toBeInTheDocument();
    });

    it('loads templates on mount', async () => {
        render(<MultiUploadPanel onStart={onStart} />);
        await vi.waitFor(() => {
            expect(mockGetBuiltinTemplates).toHaveBeenCalled();
        });
    });

    it('renders without crashing when onStart not provided', () => {
        render(<MultiUploadPanel />);
        expect(screen.getByText('Browse Files')).toBeInTheDocument();
    });

    it('renders UploadCloud icon', () => {
        const { container } = render(<MultiUploadPanel onStart={onStart} />);
        expect(container.querySelector('svg')).toBeInTheDocument();
    });
});
