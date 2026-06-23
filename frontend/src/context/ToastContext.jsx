// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { createContext, useContext, useState, useCallback, useRef, useEffect } from 'react';

const ToastContext = createContext();

export const useToast = () => useContext(ToastContext);

let toastId = 0;

export function ToastProvider({ children }) {
    const [toasts, setToasts] = useState([]);
    const timers = useRef({});

    const dismiss = useCallback((id) => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
        clearTimeout(timers.current[id]);
        delete timers.current[id];
    }, []);

    const showToast = useCallback(({ type = 'info', message, duration = 5000 }) => {
        const id = ++toastId;
        setToasts((prev) => [...prev.slice(-4), { id, type, message, duration }]); // max 5
        timers.current[id] = setTimeout(() => dismiss(id), duration);
        return id;
    }, [dismiss]);

    const addToast = useCallback((message, type = 'info', duration = 5000) => (
        showToast({ message, type, duration })
    ), [showToast]);

    // Cleanup on unmount
    useEffect(() => {
        const t = timers.current;
        return () => Object.values(t).forEach(clearTimeout);
    }, []);

    return (
        <ToastContext.Provider value={{ showToast, addToast, dismiss }}>
            {children}
            <ToastContainer toasts={toasts} dismiss={dismiss} />
        </ToastContext.Provider>
    );
}

/* ── Visual Toast Container ── */

const ICON_MAP = {
    success: { icon: 'check_circle', color: 'text-emerald-500', bg: 'bg-emerald-50 dark:bg-emerald-900/20', border: 'border-emerald-200 dark:border-emerald-800' },
    error: { icon: 'error', color: 'text-red-500', bg: 'bg-red-50 dark:bg-red-900/20', border: 'border-red-200 dark:border-red-800' },
    warning: { icon: 'warning', color: 'text-amber-500', bg: 'bg-amber-50 dark:bg-amber-900/20', border: 'border-amber-200 dark:border-amber-800' },
    info: { icon: 'info', color: 'text-blue-500', bg: 'bg-blue-50 dark:bg-blue-900/20', border: 'border-blue-200 dark:border-blue-800' },
};

function ToastContainer({ toasts, dismiss }) {
    if (toasts.length === 0) return null;
    return (
        <div className="fixed bottom-6 right-6 z-[9999] flex flex-col gap-3 pointer-events-none" aria-live="polite">
            {toasts.map((toast) => (
                <ToastItem key={toast.id} toast={toast} dismiss={dismiss} />
            ))}
        </div>
    );
}

function ToastItem({ toast, dismiss }) {
    const { icon, color, bg, border } = ICON_MAP[toast.type] || ICON_MAP.info;
    const [progress, setProgress] = useState(100);

    useEffect(() => {
        const start = Date.now();
        const step = () => {
            const elapsed = Date.now() - start;
            const pct = Math.max(0, 100 - (elapsed / toast.duration) * 100);
            setProgress(pct);
            if (pct > 0) requestAnimationFrame(step);
        };
        const raf = requestAnimationFrame(step);
        return () => cancelAnimationFrame(raf);
    }, [toast.duration]);

    return (
        <div
            className={`pointer-events-auto flex items-start gap-3 px-4 py-3 rounded-xl border shadow-lg backdrop-blur-sm ${bg} ${border} animate-in slide-in-from-bottom-4 duration-300 max-w-sm`}
            role="alert"
        >
            <span className={`material-symbols-outlined ${color} mt-0.5 shrink-0`}>{icon}</span>
            <p className="text-sm text-slate-700 dark:text-slate-200 flex-1">{toast.message}</p>
            <button
                onClick={() => dismiss(toast.id)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors shrink-0"
                aria-label="Dismiss"
            >
                <span className="material-symbols-outlined text-lg">close</span>
            </button>
            {/* Progress bar */}
            <div className="absolute bottom-0 left-0 right-0 h-0.5 overflow-hidden rounded-b-xl">
                <div
                    className={`h-full ${toast.type === 'success' ? 'bg-emerald-400' : toast.type === 'error' ? 'bg-red-400' : toast.type === 'warning' ? 'bg-amber-400' : 'bg-blue-400'} transition-none`}
                    style={{ width: `${progress}%` }}
                />
            </div>
        </div>
    );
}
