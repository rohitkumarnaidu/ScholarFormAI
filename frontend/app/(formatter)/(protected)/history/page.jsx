// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import usePageTitle from '@/src/hooks/usePageTitle';
import React, { memo, useCallback, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

import { useDocument } from '@/src/context/DocumentContext';
import Footer from '@/src/components/Footer';
import { isCompleted, isFailed } from '@/src/constants/status';
import DeleteConfirmDialog from '@/src/components/DeleteConfirmDialog';
import { deleteDocument, useDocuments } from '@/src/services/api';

const Checkbox = ({ checked, onChange, disabled, label }) => (
    <label className="inline-flex items-center justify-center cursor-pointer">
        <input
            type="checkbox"
            checked={checked}
            onChange={(e) => !disabled && onChange(e.target.checked)}
            disabled={disabled}
            className={`w-5 h-5 rounded border transition-colors cursor-pointer accent-primary focus:ring-2 focus:ring-primary/50 focus:ring-offset-1 ${disabled ? 'opacity-50 cursor-not-allowed border-slate-200 dark:border-slate-800' : checked ? 'bg-primary border-primary text-white' : 'bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700'}`}
            aria-label={label || 'Select item'}
        />
    </label>
);

const toTimestamp = (value) => new Date(value || 0).getTime();
const resolveFilename = (item) => (
    item?.filename
    || item?.original_file_name
    || item?.originalFileName
    || 'Untitled'
);

const buildVersionedHistory = (records) => {
    const groups = new Map();

    records.forEach((record) => {
        const key = String(resolveFilename(record)).toLowerCase();
        if (!groups.has(key)) {
            groups.set(key, []);
        }
        groups.get(key).push(record);
    });

    const versionMetaById = new Map();

    groups.forEach((group) => {
        const sortedGroup = [...group].sort((left, right) => toTimestamp(left.timestamp) - toTimestamp(right.timestamp));
        sortedGroup.forEach((record, index) => {
            if (!record?.id) return;
            versionMetaById.set(record.id, {
                versionNumber: index + 1,
                totalVersions: sortedGroup.length,
                previous: index > 0 ? sortedGroup[index - 1] : null,
            });
        });
    });

    return records.map((record, index) => {
        const fallbackMeta = {
            versionNumber: 1,
            totalVersions: 1,
            previous: null,
        };
        const meta = record?.id ? versionMetaById.get(record.id) || fallbackMeta : fallbackMeta;
        const previous = meta.previous;
        const diffIndicators = [meta.versionNumber > 1 ? 'Reprocessed' : 'Original'];

        if (previous) {
            const previousTemplate = String(previous.template || '').toUpperCase();
            const currentTemplate = String(record.template || '').toUpperCase();
            const previousStatus = String(previous.status || '').toUpperCase();
            const currentStatus = String(record.status || '').toUpperCase();

            if (previousTemplate !== currentTemplate) {
                diffIndicators.push('Template changed');
            }
            if (previousStatus !== currentStatus) {
                diffIndicators.push('Status changed');
            }
            if (toTimestamp(record.updated_at || record.timestamp) > toTimestamp(previous.updated_at || previous.timestamp)) {
                diffIndicators.push('New revision');
            }
        }

        return {
            ...record,
            key: record.id || `${resolveFilename(record)}-${record.timestamp || index}`,
            versionNumber: meta.versionNumber,
            totalVersions: meta.totalVersions,
            diffIndicators,
        };
    });
};

const HistoryRow = memo(function HistoryRow({
    item,
    isSelected,
    onToggleSelection,
    onRestore,
    onDownload,
    onRequestDelete,
}) {
    return (
        <tr className={`transition-colors group ${isSelected ? 'bg-primary/5 dark:bg-primary/10' : 'hover:bg-slate-50 dark:hover:bg-slate-800/40'}`}>
            <td className="px-6 py-5 whitespace-nowrap text-center">
                <Checkbox
                    checked={isSelected}
                    onChange={() => item.id && onToggleSelection(item.id)}
                    disabled={!item.id}
                    label={`Select ${resolveFilename(item)}`}
                />
            </td>
            <td className="px-6 py-5 whitespace-nowrap">
                <span className="text-slate-600 dark:text-slate-400 text-sm">
                    {new Date(item.timestamp).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}
                </span>
            </td>
            <td className="px-6 py-5">
                <div className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-slate-400 group-hover:text-primary transition-colors">description</span>
                    <span className="text-slate-900 dark:text-white font-bold text-sm truncate max-w-[200px]">{resolveFilename(item)}</span>
                </div>
            </td>
            <td className="px-6 py-5">
                <div className="flex flex-col gap-1">
                    <span className="text-xs font-bold text-slate-700 dark:text-slate-200">
                        v{item.versionNumber} / {item.totalVersions}
                    </span>
                    <div className="flex flex-wrap gap-1">
                        {item.diffIndicators.map((indicator) => (
                            <span
                                key={`${item.key}-${indicator}`}
                                className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                            >
                                {indicator}
                            </span>
                        ))}
                    </div>
                </div>
            </td>
            <td className="px-6 py-5">
                <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400 uppercase">
                    {item.template}
                </span>
            </td>
            <td className="px-6 py-5">
                {isCompleted(item.status) ? (
                    <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full w-fit ${item.result?.errors?.length > 0 ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' : 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'}`}>
                        <span className="material-symbols-outlined !text-sm">{item.result?.errors?.length > 0 ? 'error' : 'check_circle'}</span>
                        <span className="text-xs font-bold">{item.result?.errors?.length > 0 ? 'Issue Detect' : 'Passed'}</span>
                    </div>
                ) : (
                    <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 w-fit">
                        <span className="material-symbols-outlined !text-sm">cancel</span>
                        <span className="text-xs font-bold">Failed</span>
                    </div>
                )}
            </td>
            <td className="px-6 py-5">
                <div className="flex justify-end items-center gap-2 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity">
                    <button onClick={() => onRestore(item)} className="bg-primary/10 text-primary text-xs font-bold px-3 py-1.5 rounded-lg hover:bg-primary hover:text-white transition-all">
                        Open Corrected
                    </button>
                    <button
                        onClick={() => onDownload(item)}
                        className="p-1.5 text-slate-400 hover:text-primary transition-colors"
                        title="Download"
                        aria-label={`Download ${resolveFilename(item)}`}
                    >
                        <span className="material-symbols-outlined" aria-hidden="true">download</span>
                    </button>
                    <button
                        onClick={() => onRequestDelete(item)}
                        className="p-1.5 text-slate-400 hover:text-red-600 transition-colors"
                        title="Delete"
                        aria-label={`Delete ${resolveFilename(item)}`}
                    >
                        <span className="material-symbols-outlined" aria-hidden="true">delete</span>
                    </button>
                </div>
            </td>
        </tr>
    );
});

export default function History() {
    usePageTitle('Document History');
    const router = useRouter();
    const navigate = useCallback((href, options = {}) => {
        if (options?.replace) {
            router.replace(href);
            return;
        }
        router.push(href);
    }, [router]);
    const { setJob } = useDocument();
    const { data: documentsPayload, isLoading, refetch: refreshDocuments } = useDocuments({ limit: 50 });
    const [documentToDelete, setDocumentToDelete] = useState(null);
    const [isDeleting, setIsDeleting] = useState(false);
    const [deleteError, setDeleteError] = useState('');
    const [selectedIds, setSelectedIds] = useState(new Set());
    const [isDeletingBulk, setIsDeletingBulk] = useState(false);

    const history = useMemo(() => {
        const records = documentsPayload?.documents || [];
        return [...records].sort((left, right) => toTimestamp(right.timestamp) - toTimestamp(left.timestamp));
    }, [documentsPayload]);

    const versionedHistory = useMemo(() => buildVersionedHistory(history), [history]);
    const getJobRoute = (item, suffix, fallback) => (
        item?.id ? `/jobs/${encodeURIComponent(item.id)}/${suffix}` : fallback
    );

    const handleRestore = useCallback((item) => {
        setJob(item);
        navigate(getJobRoute(item, 'results', '/results'));
    }, [navigate, setJob]);

    const handleDownload = useCallback((item) => {
        setJob(item);
        navigate(getJobRoute(item, 'download', '/download'));
    }, [navigate, setJob]);

    const requestDelete = useCallback((item) => {
        setDeleteError('');
        setDocumentToDelete(item);
    }, []);

    const handleDeleteConfirm = async () => {
        if (!documentToDelete?.id || isDeleting) {
            return;
        }

        setIsDeleting(true);
        setDeleteError('');

        try {
            await deleteDocument(documentToDelete.id);
            setDocumentToDelete(null);
            setSelectedIds(prev => {
                const newSet = new Set(prev);
                newSet.delete(documentToDelete.id);
                return newSet;
            });
            await refreshDocuments();
        } catch (error) {
            setDeleteError(
                typeof error?.message === 'string'
                    ? error.message
                    : 'Failed to delete document.'
            );
        } finally {
            setIsDeleting(false);
        }
    };

    const toggleSelection = useCallback((id) => {
        setSelectedIds(prev => {
            const next = new Set(prev);
            if (next.has(id)) {
                next.delete(id);
            } else {
                next.add(id);
            }
            return next;
        });
    }, []);

    const toggleAll = () => {
        if (selectedIds.size === versionedHistory.length) {
            setSelectedIds(new Set());
        } else {
            setSelectedIds(new Set(versionedHistory.map(item => item.id).filter(Boolean)));
        }
    };

    const handleBulkDelete = async () => {
        if (selectedIds.size === 0 || isDeletingBulk) return;
        setIsDeletingBulk(true);
        setDeleteError('');
        try {
            const promises = Array.from(selectedIds).map(id => deleteDocument(id));
            await Promise.allSettled(promises);
            setSelectedIds(new Set());
            await refreshDocuments();
        } catch (error) {
            setDeleteError('Failed to delete some documents.');
        } finally {
            setIsDeletingBulk(false);
        }
    };

    const stats = {
        total: versionedHistory.length,
        valid: versionedHistory.filter((item) => isCompleted(item.status) && (!item.result?.errors || item.result.errors.length === 0)).length,
        warnings: versionedHistory.filter((item) => item.result?.warnings?.length > 0 || item.status === 'COMPLETED_WITH_WARNINGS').length,
        errors: versionedHistory.filter((item) => isFailed(item.status) || (item.result?.errors?.length > 0)).length,
    };

    return (
        <div className="bg-background-light dark:bg-background-dark font-display text-slate-900 dark:text-slate-100 min-h-screen flex flex-col">

            {/* Page Content */}
            <main className="flex flex-1 justify-center py-6 sm:py-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                <div className="layout-content-container flex flex-col w-full max-w-[1280px] px-4 sm:px-6 md:px-10">
                    {/* PageHeading */}
                    <div className="flex flex-wrap justify-between items-end gap-4 mb-8">
                        <div className="flex flex-col gap-2">
                            <h1 className="text-slate-900 dark:text-white text-2xl sm:text-3xl font-black tracking-tight">Manuscript Processing History</h1>
                            <p className="text-slate-500 dark:text-slate-400 text-base max-w-2xl">Track and manage your document versions, template compliance, and validation results.</p>
                        </div>
                        <div className="flex gap-3">
                            <Link href="/upload" className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg font-bold text-sm hover:bg-blue-700 transition-colors shadow-lg shadow-primary/20 w-full sm:w-auto justify-center">
                                <span className="material-symbols-outlined">file_upload</span>
                                <span>Process New Manuscript</span>
                            </Link>
                        </div>
                    </div>

                    {deleteError && (
                        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-900/20 dark:text-red-300">
                            {deleteError}
                        </div>
                    )}

                    {/* Stats Summary */}
                    <div className="flex flex-col gap-6">
                        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
                            <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm transition-all hover:shadow-md">
                                <p className="text-slate-500 dark:text-slate-400 text-xs font-bold uppercase tracking-wider mb-1">Total Manuscripts</p>
                                <p className="text-2xl font-black text-slate-900 dark:text-white">{stats.total}</p>
                            </div>
                            <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm transition-all hover:shadow-md">
                                <p className="text-green-600 dark:text-green-400 text-xs font-bold uppercase tracking-wider mb-1">Perfect Compliance</p>
                                <p className="text-2xl font-black text-slate-900 dark:text-white">{stats.valid}</p>
                            </div>
                            <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm transition-all hover:shadow-md">
                                <p className="text-amber-600 dark:text-amber-400 text-xs font-bold uppercase tracking-wider mb-1">With Warnings</p>
                                <p className="text-2xl font-black text-slate-900 dark:text-white">{stats.warnings}</p>
                            </div>
                            <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm transition-all hover:shadow-md">
                                <p className="text-red-600 dark:text-red-400 text-xs font-bold uppercase tracking-wider mb-1">Requires Attention</p>
                                <p className="text-2xl font-black text-slate-900 dark:text-white">{stats.errors}</p>
                            </div>
                        </div>

                        {/* History Table */}
                        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-sm">
                            <div className="border-b border-slate-200 dark:border-slate-800 px-6 py-4 flex justify-between items-center bg-slate-50/50 dark:bg-slate-900/50">
                                <h3 className="text-sm font-bold text-slate-900 dark:text-white">All Versions</h3>
                                <span className="text-xs text-slate-500">{versionedHistory.length} records found</span>
                            </div>

                            <div className="overflow-x-auto">
                                <table className="w-full text-left border-collapse">
                                    <thead>
                                        <tr className="bg-slate-50/50 dark:bg-slate-900/50 text-slate-500 dark:text-slate-400 uppercase text-[11px] font-bold tracking-widest">
                                            <th className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 w-12 text-center">
                                                <Checkbox
                                                    checked={versionedHistory.length > 0 && selectedIds.size === versionedHistory.length}
                                                    onChange={toggleAll}
                                                    disabled={isLoading || versionedHistory.length === 0}
                                                    label="Select all documents"
                                                />
                                            </th>
                                            <th className="px-6 py-4 border-b border-slate-200 dark:border-slate-800">Date / Time</th>
                                            <th className="px-6 py-4 border-b border-slate-200 dark:border-slate-800">Manuscript Name</th>
                                            <th className="px-6 py-4 border-b border-slate-200 dark:border-slate-800">Version</th>
                                            <th className="px-6 py-4 border-b border-slate-200 dark:border-slate-800">Template</th>
                                            <th className="px-6 py-4 border-b border-slate-200 dark:border-slate-800">Status</th>
                                            <th className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 text-right">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800/50">
                                        {isLoading ? (
                                            Array.from({ length: 5 }).map((_, i) => (
                                                <tr key={`skeleton-${i}`} className="animate-pulse">
                                                    <td className="px-6 py-5"><div className="w-5 h-5 rounded bg-slate-200 dark:bg-slate-700 mx-auto"></div></td>
                                                    <td className="px-6 py-5"><div className="h-4 w-28 rounded bg-slate-200 dark:bg-slate-700"></div></td>
                                                    <td className="px-6 py-5"><div className="flex items-center gap-2"><div className="w-5 h-5 rounded bg-slate-200 dark:bg-slate-700"></div><div className="h-4 w-36 rounded bg-slate-200 dark:bg-slate-700"></div></div></td>
                                                    <td className="px-6 py-5"><div className="h-4 w-16 rounded bg-slate-200 dark:bg-slate-700"></div></td>
                                                    <td className="px-6 py-5"><div className="h-5 w-14 rounded bg-slate-200 dark:bg-slate-700"></div></td>
                                                    <td className="px-6 py-5"><div className="h-6 w-20 rounded-full bg-slate-200 dark:bg-slate-700"></div></td>
                                                    <td className="px-6 py-5"><div className="flex justify-end gap-2"><div className="h-7 w-24 rounded-lg bg-slate-200 dark:bg-slate-700"></div><div className="h-7 w-7 rounded bg-slate-200 dark:bg-slate-700"></div></div></td>
                                                </tr>
                                            ))
                                        ) : versionedHistory.length === 0 ? (
                                            <tr>
                                                <td colSpan="7" className="px-6 py-12 text-center text-slate-500">
                                                    No processing history found. Start by uploading a manuscript.
                                                </td>
                                            </tr>
                                        ) : (
                                            versionedHistory.map((item) => (
                                                <HistoryRow
                                                    key={item.key}
                                                    item={item}
                                                    isSelected={selectedIds.has(item.id)}
                                                    onToggleSelection={toggleSelection}
                                                    onRestore={handleRestore}
                                                    onDownload={handleDownload}
                                                    onRequestDelete={requestDelete}
                                                />
                                            ))
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </main>

            {/* Sticky Action Bar */}
            {selectedIds.size > 0 && (
                <div className="fixed bottom-0 left-0 right-0 z-40 p-4 animate-in slide-in-from-bottom-full duration-300">
                    <div className="max-w-3xl mx-auto bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl rounded-2xl p-4 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <span className="material-symbols-outlined text-primary bg-primary/10 p-2 rounded-full">check_circle</span>
                            <div>
                                <p className="text-slate-900 dark:text-white font-bold">{selectedIds.size} item{selectedIds.size > 1 ? 's' : ''} selected</p>
                                <button onClick={() => setSelectedIds(new Set())} className="text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 text-sm hover:underline">Clear selection</button>
                            </div>
                        </div>
                        <button
                            onClick={handleBulkDelete}
                            disabled={isDeletingBulk}
                            className="bg-red-50 hover:bg-red-100 dark:bg-red-900/20 dark:hover:bg-red-900/40 text-red-600 border border-red-200 dark:border-red-900/50 font-bold py-2 px-6 rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50"
                        >
                            {isDeletingBulk ? (
                                <><span className="material-symbols-outlined animate-spin text-[18px]">progress_activity</span> Deleting...</>
                            ) : (
                                <><span className="material-symbols-outlined text-[18px]">delete</span> Delete Selected</>
                            )}
                        </button>
                    </div>
                </div>
            )}

            <DeleteConfirmDialog
                isOpen={Boolean(documentToDelete)}
                isDeleting={isDeleting}
                documentName={resolveFilename(documentToDelete)}
                onCancel={() => {
                    if (!isDeleting) {
                        setDocumentToDelete(null);
                        setDeleteError('');
                    }
                }}
                onConfirm={handleDeleteConfirm}
            />

            <Footer variant="app" />
        </div>
    );
}



