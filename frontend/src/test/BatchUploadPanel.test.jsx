import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import BatchUploadPanel from '../components/BatchUploadPanel';

function createFile(name, size) {
    return { name, size };
}

describe('BatchUploadPanel', () => {
    const defaultFiles = [
        { id: '1', file: createFile('doc1.docx', 1000), status: 'done', progress: 100 },
        { id: '2', file: createFile('doc2.pdf', 2000), status: 'pending', progress: 0 },
    ];

    it('renders drop zone', () => {
        render(<BatchUploadPanel files={[]} onFilesSelected={() => {}} onRemove={() => {}} />);
        expect(screen.getByText(/Drag & drop files here/)).toBeInTheDocument();
    });

    it('renders file list', () => {
        render(<BatchUploadPanel files={defaultFiles} onFilesSelected={() => {}} onRemove={() => {}} />);
        expect(screen.getByText('doc1.docx')).toBeInTheDocument();
        expect(screen.getByText('doc2.pdf')).toBeInTheDocument();
    });

    it('shows file count', () => {
        render(<BatchUploadPanel files={defaultFiles} onFilesSelected={() => {}} onRemove={() => {}} />);
        expect(screen.getByText('Files (2)')).toBeInTheDocument();
    });

    it('calls onFilesSelected on drop', () => {
        const onFilesSelected = vi.fn();
        render(<BatchUploadPanel files={[]} onFilesSelected={onFilesSelected} onRemove={() => {}} />);
        const zone = screen.getByRole('button');

        fireEvent.drop(zone, {
            dataTransfer: { files: [createFile('test.docx', 500)] },
        });

        expect(onFilesSelected).toHaveBeenCalled();
    });

    it('calls onRemove when remove button clicked', () => {
        const onRemove = vi.fn();
        const files = [{ id: '1', file: createFile('doc.docx', 100), status: 'pending', progress: 0 }];
        render(<BatchUploadPanel files={files} onFilesSelected={() => {}} onRemove={onRemove} />);
        const removeBtn = screen.getByLabelText('Remove File');
        fireEvent.click(removeBtn);
        expect(onRemove).toHaveBeenCalledWith('1');
    });

    it('shows retry button for errored files', () => {
        const onRetry = vi.fn();
        const files = [{ id: '1', file: createFile('doc.docx', 100), status: 'error', progress: 0 }];
        render(<BatchUploadPanel files={files} onFilesSelected={() => {}} onRemove={() => {}} onRetry={onRetry} />);
        fireEvent.click(screen.getByText('Retry'));
        expect(onRetry).toHaveBeenCalledWith('1');
    });

    it('does not show retry when no onRetry provided', () => {
        const files = [{ id: '1', file: createFile('doc.docx', 100), status: 'error', progress: 0 }];
        render(<BatchUploadPanel files={files} onFilesSelected={() => {}} onRemove={() => {}} />);
        expect(screen.queryByText('Retry')).not.toBeInTheDocument();
    });
});
