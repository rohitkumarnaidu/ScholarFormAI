import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import FileUpload from '../components/FileUpload';

function createFile(name, size) {
    return { name, size };
}

describe('FileUpload', () => {
    it('renders upload zone', () => {
        render(<FileUpload onFileSelect={() => {}} />);
        expect(screen.getByText('Drag and drop your manuscript here')).toBeInTheDocument();
    });

    it('shows validation error for unsupported format', () => {
        const onFileSelect = vi.fn();
        render(<FileUpload onFileSelect={onFileSelect} />);
        const hiddenInput = document.querySelector('input[type="file"]');
        Object.defineProperty(hiddenInput, 'files', {
            value: [createFile('bad.exe', 1000)],
        });
        fireEvent.change(hiddenInput);
        expect(screen.getByText(/Unsupported file format/)).toBeInTheDocument();
    });

    it('accepts valid docx file', () => {
        const onFileSelect = vi.fn();
        render(<FileUpload onFileSelect={onFileSelect} />);
        const hiddenInput = document.querySelector('input[type="file"]');
        Object.defineProperty(hiddenInput, 'files', {
            value: [createFile('thesis.docx', 1000)],
        });
        fireEvent.change(hiddenInput);
        expect(onFileSelect).toHaveBeenCalledWith(expect.objectContaining({ name: 'thesis.docx' }));
    });

    it('rejects file without name', () => {
        const onFileSelect = vi.fn();
        render(<FileUpload onFileSelect={onFileSelect} />);
        const hiddenInput = document.querySelector('input[type="file"]');
        Object.defineProperty(hiddenInput, 'files', {
            value: [createFile('', 1000)],
        });
        fireEvent.change(hiddenInput);
        expect(screen.getByText(/Unsupported file format/)).toBeInTheDocument();
    });

    it('shows validation error for oversized file', () => {
        const onFileSelect = vi.fn();
        render(<FileUpload onFileSelect={onFileSelect} />);
        const hiddenInput = document.querySelector('input[type="file"]');
        Object.defineProperty(hiddenInput, 'files', {
            value: [createFile('large.pdf', 60 * 1024 * 1024)],
        });
        fireEvent.change(hiddenInput);
        expect(screen.getByText(/Unsupported file format/)).toBeInTheDocument();
    });

    it('calls onFileSelect on Enter key press', () => {
        const onFileSelect = vi.fn();
        render(<FileUpload onFileSelect={onFileSelect} />);
        const zone = document.querySelector('[role="button"]');
        fireEvent.keyDown(zone, { key: 'Enter' });
        expect(onFileSelect).not.toHaveBeenCalled();
    });

    it('calls onFileSelect on Space key press', () => {
        const onFileSelect = vi.fn();
        render(<FileUpload onFileSelect={onFileSelect} />);
        const zone = document.querySelector('[role="button"]');
        fireEvent.keyDown(zone, { key: ' ' });
        expect(onFileSelect).not.toHaveBeenCalled();
    });

    it('sets drag-active class on dragover', () => {
        render(<FileUpload onFileSelect={() => {}} />);
        const zone = document.querySelector('[role="button"]');
        expect(zone.className).not.toContain('bg-blue-50');
        fireEvent.dragEnter(zone);
        expect(zone.className).toContain('bg-blue-50');
        fireEvent.dragLeave(zone);
        expect(zone.className).not.toContain('bg-blue-50');
    });

    it('handles file drop with valid file', () => {
        const onFileSelect = vi.fn();
        render(<FileUpload onFileSelect={onFileSelect} />);
        const zone = document.querySelector('[role="button"]');

        fireEvent.drop(zone, {
            dataTransfer: { files: [createFile('paper.docx', 1000)] },
        });

        expect(onFileSelect).toHaveBeenCalledWith(expect.objectContaining({ name: 'paper.docx' }));
    });

    it('handles file drop with invalid file', () => {
        const onFileSelect = vi.fn();
        render(<FileUpload onFileSelect={onFileSelect} />);
        const zone = document.querySelector('[role="button"]');

        fireEvent.drop(zone, {
            dataTransfer: { files: [createFile('bad.exe', 1000)] },
        });

        expect(onFileSelect).not.toHaveBeenCalled();
        expect(screen.getByText(/Unsupported file format/)).toBeInTheDocument();
    });

    it('accepts valid pdf file', () => {
        const onFileSelect = vi.fn();
        render(<FileUpload onFileSelect={onFileSelect} />);
        const hiddenInput = document.querySelector('input[type="file"]');
        Object.defineProperty(hiddenInput, 'files', {
            value: [createFile('paper.pdf', 1000)],
        });
        fireEvent.change(hiddenInput);
        expect(onFileSelect).toHaveBeenCalledWith(expect.objectContaining({ name: 'paper.pdf' }));
    });

    it('accepts valid txt file', () => {
        const onFileSelect = vi.fn();
        render(<FileUpload onFileSelect={onFileSelect} />);
        const hiddenInput = document.querySelector('input[type="file"]');
        Object.defineProperty(hiddenInput, 'files', {
            value: [createFile('notes.txt', 500)],
        });
        fireEvent.change(hiddenInput);
        expect(onFileSelect).toHaveBeenCalledWith(expect.objectContaining({ name: 'notes.txt' }));
    });
});
