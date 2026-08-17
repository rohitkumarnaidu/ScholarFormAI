import React, { memo, useState, useCallback, useEffect, useRef } from 'react';
import ConfirmDialog from '../ui/ConfirmDialog';

import { cn } from '@/src/lib/utils';
import { ArrowLeftRight, CheckCircle, Download, Trash2 } from 'lucide-react';

const BatchActions = memo(function BatchActions({
    selectedIds = [],
    onDelete,
    onExport,
    onCompare,
    onDeselectAll,
}) {
    const [showConfirm, setShowConfirm] = useState(false);
    const [animatingIn, setAnimatingIn] = useState(false);
    const prevCount = useRef(0);
    const count = selectedIds.length;

    useEffect(() => {
        if (count > 0 && prevCount.current === 0) {
            setAnimatingIn(true);
            const timer = setTimeout(() => setAnimatingIn(false), 300);
            return () => clearTimeout(timer);
        }
        prevCount.current = count;
    }, [count]);

    const handleDeleteClick = useCallback(() => {
        setShowConfirm(true);
    }, []);

    const handleConfirmDelete = useCallback(() => {
        setShowConfirm(false);
        onDelete?.();
    }, [onDelete]);

    const handleCancelDelete = useCallback(() => {
        setShowConfirm(false);
    }, []);

    const handleExport = useCallback(() => {
        onExport?.();
    }, [onExport]);

    const handleCompare = useCallback(() => {
        onCompare?.();
    }, [onCompare]);

    const handleDeselectAll = useCallback(() => {
        onDeselectAll?.();
    }, [onDeselectAll]);

    if (count === 0) return null;

    return (
        <>
            <div
                className={cn(
                    'fixed bottom-0 left-0 right-0 z-40 p-4',
                    animatingIn ? 'animate-in slide-in-from-bottom-full duration-300' : ''
                )}
            >
                <div className="max-w-3xl mx-auto bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl rounded-2xl p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <CheckCircle className="text-primary bg-primary/10 p-2 rounded-full" />
                        <div>
                            <p className="text-slate-900 dark:text-white font-bold text-sm">
                                {count} item{count !== 1 ? 's' : ''} selected
                            </p>
                            <button
                                onClick={handleDeselectAll}
                                className="text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 text-xs hover:underline"
                            >
                                Deselect all
                            </button>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={handleCompare}
                            disabled={count < 2}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 font-semibold text-xs transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                            title={count < 2 ? 'Select at least 2 items to compare' : 'Compare selected'}
                        >
                            <ArrowLeftRight className="text-[16px]" />
                            Compare
                        </button>
                        <button
                            onClick={handleExport}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 font-semibold text-xs transition-colors"
                        >
                            <Download className="text-[16px]" />
                            Export
                        </button>
                        <button
                            onClick={handleDeleteClick}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-50 hover:bg-red-100 dark:bg-red-900/20 dark:hover:bg-red-900/40 text-red-600 border border-red-200 dark:border-red-900/50 font-semibold text-xs transition-colors"
                        >
                            <Trash2 className="text-[16px]" />
                            Delete
                        </button>
                    </div>
                </div>
            </div>

            <ConfirmDialog
                open={showConfirm}
                title={`Delete ${count} item${count !== 1 ? 's' : ''}?`}
                description="This action cannot be undone. The selected documents will be permanently removed."
                confirmLabel="Delete"
                variant="danger"
                onConfirm={handleConfirmDelete}
                onCancel={handleCancelDelete}
            />
        </>
    );
});

BatchActions.displayName = 'BatchActions';

export default BatchActions;
