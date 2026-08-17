// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { useRef, useCallback } from 'react';
import { AlertTriangle, CheckCircle, Clock, CloudUpload, RefreshCw, X } from 'lucide-react';

const ACCEPTED_FORMATS = '.docx,.pdf,.tex,.txt,.html,.htm,.md,.markdown,.doc';

export default function BatchUploadPanel({ files, onFilesSelected, onRemove, onRetry, disabled }) {
    const inputRef = useRef(null);

    const handleDrop = useCallback(
        (e) => {
            e.preventDefault();
            if (disabled) return;
            const dropped = Array.from(e.dataTransfer.files);
            if (dropped.length > 0) onFilesSelected(dropped);
        },
        [disabled, onFilesSelected]
    );

    const handleDragOver = (e) => {
        e.preventDefault();
    };

    const handleInputChange = (e) => {
        const selected = Array.from(e.target.files);
        if (selected.length > 0) onFilesSelected(selected);
        e.target.value = '';
    };

    const statusIcon = (status) => {
        switch (status) {
            case 'done':
                return <CheckCircle className="text-green-500 text-lg" />;
            case 'error':
                return <AlertTriangle className="text-red-500 text-lg" />;
            case 'uploading':
                return <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />;
            default:
                return <Clock className="text-muted-foreground text-lg" />;
        }
    };

    const formatSize = (bytes) => {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    };

    const StatusBadge = ({ status }) => {
        const labels = { done: 'Completed', error: 'Failed', uploading: 'Processing', pending: 'Pending' };
        return (
            <span 
                role="status" 
                aria-label={`Status: ${labels[status] || 'Pending'}`}
                className={`px-2 py-0.5 rounded-full ${
                status === 'done' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' :
                status === 'error' ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' :
                status === 'uploading' ? 'bg-primary/10 text-primary dark:bg-primary/20 dark:text-primary' :
                'bg-muted text-muted-foreground'
            } text-[10px] font-bold uppercase tracking-wider shrink-0`}>
                {labels[status] || 'Pending'}
            </span>
        );
    };

    return (
        <div className="bg-card text-card-foreground rounded-xl border border-border shadow-sm overflow-hidden">
            {/* Drop Zone */}
            <div
                role="button"
                tabIndex={disabled ? -1 : 0}
                aria-label="Upload multiple files"
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onClick={() => !disabled && inputRef.current?.click()}
                onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        if (!disabled) inputRef.current?.click();
                    }
                }}
                className={`border-2 border-dashed rounded-xl m-4 p-8 text-center cursor-pointer transition-colors focus:ring-2 focus:ring-primary focus:outline-none ${disabled
                    ? 'border-border bg-muted/50 opacity-50 cursor-not-allowed'
                    : 'border-border hover:border-primary bg-muted/30'
                    }`}
            >
                <CloudUpload className="text-4xl text-muted-foreground mb-2" />
                <p className="text-muted-foreground font-medium">
                    Drag & drop files here, or <span className="text-primary font-semibold">browse</span>
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                    Accepts DOCX, PDF, TEX, TXT, HTML, MD files (up to 50MB each)
                </p>
                <input
                    ref={inputRef}
                    type="file"
                    multiple
                    accept={ACCEPTED_FORMATS}
                    onChange={handleInputChange}
                    className="hidden"
                />
            </div>

            {/* File List */}
            {files.length > 0 && (
                <div className="border-t border-border">
                    <div className="px-4 py-2 bg-muted/50">
                        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                            Files ({files.length})
                        </p>
                    </div>
                    <ul className="divide-y divide-border max-h-80 overflow-y-auto">
                        {files.map((entry) => (
                            <li
                                key={entry.id}
                                className="flex items-center gap-4 px-5 py-4 hover:bg-muted/30 transition-colors group"
                            >
                                <div className="shrink-0 mt-0.5">
                                    {statusIcon(entry.status)}
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className="flex justify-between items-center mb-1 gap-3">
                                        <p className="text-sm font-bold text-foreground truncate">
                                            {entry.file.name}
                                        </p>
                                        <StatusBadge status={entry.status} />
                                    </div>
                                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                        <span className="shrink-0">{formatSize(entry.file.size)}</span>
                                        {entry.error && (
                                            <span className="text-red-500 truncate max-w-xs" title={entry.error}>• {entry.error}</span>
                                        )}
                                        {entry.jobId && (
                                            <span className="text-green-600 dark:text-green-400 shrink-0">• Job: {entry.jobId.slice(0, 8)}</span>
                                        )}
                                    </div>
                                    {entry.status === 'uploading' && (
                                        <div className="w-full h-1.5 bg-muted rounded-full mt-2.5 overflow-hidden">
                                            <div
                                                className="h-full bg-primary rounded-full transition-all duration-300 relative"
                                                style={{ width: `${Math.max(2, entry.progress)}%` }}
                                            >
                                                <div className="absolute inset-0 bg-white/20 animate-[shimmer_1s_infinite] w-full" style={{ backgroundImage: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent)' }} />
                                            </div>
                                        </div>
                                    )}
                                </div>
                                <div className="shrink-0 flex items-center gap-2 opacity-100 md:opacity-0 group-hover:opacity-100 transition-opacity">
                                    {entry.status === 'pending' && (
                                        <button
                                            onClick={(e) => { e.stopPropagation(); onRemove(entry.id); }}
                                            disabled={disabled}
                                            className="p-1.5 text-muted-foreground hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors disabled:opacity-50"
                                            title="Remove File"
                                            aria-label="Remove File"
                                        >
                                            <X className="text-lg" />
                                        </button>
                                    )}
                                    {entry.status === 'error' && onRetry && (
                                        <button
                                            onClick={(e) => { e.stopPropagation(); onRetry(entry.id); }}
                                            disabled={disabled}
                                            className="px-3 py-1.5 bg-primary/10 text-primary hover:bg-primary hover:text-white rounded-lg text-xs font-bold transition-colors disabled:opacity-50 flex items-center gap-1.5"
                                        >
                                            <RefreshCw className="text-[16px]" />
                                            Retry
                                        </button>
                                    )}
                                </div>
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
}
