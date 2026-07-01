'use client';
import { useState, useEffect, createContext, useContext, useCallback, useRef } from 'react';

const ConfirmContext = createContext(null);

export function useConfirm() {
    return useContext(ConfirmContext);
}

export function ConfirmProvider({ children }) {
    const [state, setState] = useState({ open: false, title: '', message: '', confirmLabel: 'Delete', variant: 'danger' });
    const resolveRef = useRef(null);

    const confirm = useCallback((message, title = 'Confirm', confirmLabel = 'Delete', variant = 'danger') => {
        return new Promise((resolve) => {
            resolveRef.current = resolve;
            setState({ open: true, title, message, confirmLabel, variant });
        });
    }, []);

    const handleConfirm = useCallback(() => {
        resolveRef.current?.(true);
        setState(prev => ({ ...prev, open: false }));
    }, []);

    const handleCancel = useCallback(() => {
        resolveRef.current?.(false);
        setState(prev => ({ ...prev, open: false }));
    }, []);

    const handleKeyDown = useCallback((e) => {
        if (e.key === 'Escape') handleCancel();
    }, [handleCancel]);

    useEffect(() => {
        if (state.open) {
            document.addEventListener('keydown', handleKeyDown);
            return () => document.removeEventListener('keydown', handleKeyDown);
        }
    }, [state.open, handleKeyDown]);

    const variantStyles = {
        danger: 'bg-red-600 hover:bg-red-700 focus:ring-red-500/30',
        warning: 'bg-amber-600 hover:bg-amber-700 focus:ring-amber-500/30',
        info: 'bg-indigo-600 hover:bg-indigo-700 focus:ring-indigo-500/30',
    };

    return (
        <ConfirmContext.Provider value={confirm}>
            {children}
            {state.open && (
                <div className="fixed inset-0 z-50 flex items-center justify-center">
                    <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={handleCancel} />
                    <div className="relative bg-white dark:bg-gray-800 rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700 p-6 w-full max-w-sm mx-4 animate-scale-in" role="dialog" aria-modal="true">
                        <div className="flex items-start gap-3 mb-4">
                            <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${state.variant === 'danger' ? 'bg-red-100 dark:bg-red-900/30' : state.variant === 'warning' ? 'bg-amber-100 dark:bg-amber-900/30' : 'bg-indigo-100 dark:bg-indigo-900/30'}`}>
                                <span className={`material-symbols-outlined text-[22px] ${state.variant === 'danger' ? 'text-red-600 dark:text-red-400' : state.variant === 'warning' ? 'text-amber-600 dark:text-amber-400' : 'text-indigo-600 dark:text-indigo-400'}`}>
                                    {state.variant === 'danger' ? 'delete_forever' : state.variant === 'warning' ? 'warning' : 'info'}
                                </span>
                            </div>
                            <div className="flex-1 min-w-0">
                                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{state.title}</h3>
                                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{state.message}</p>
                            </div>
                        </div>
                        <div className="flex gap-3 justify-end">
                            <button onClick={handleCancel} className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition focus:outline-none focus:ring-2 focus:ring-gray-400/30" autoFocus>Cancel</button>
                            <button onClick={handleConfirm} className={`px-4 py-2 text-sm font-medium text-white rounded-lg transition focus:outline-none focus:ring-2 ${variantStyles[state.variant] || variantStyles.danger}`}>{state.confirmLabel}</button>
                        </div>
                    </div>
                </div>
            )}
            <style
            dangerouslySetInnerHTML={{
                __html: `
                    @keyframes scale-in {
                        from { opacity: 0; transform: scale(0.95); }
                        to { opacity: 1; transform: scale(1); }
                    }
                    .animate-scale-in { animation: scale-in 0.15s ease-out; }
                `,
            }}
            />
        </ConfirmContext.Provider>
    );
}
