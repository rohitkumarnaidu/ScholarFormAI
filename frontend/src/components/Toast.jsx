'use client';
import { useState, createContext, useContext, useCallback } from 'react';

const ToastContext = createContext(null);

export function useToast() {
    return useContext(ToastContext);
}

export function ToastProvider({ children }) {
    const [toasts, setToasts] = useState([]);

    const addToast = useCallback((message, type = 'success', duration = 4000) => {
        const id = Date.now() + Math.random();
        setToasts(prev => [...prev, { id, message, type }]);
        if (duration > 0) {
            setTimeout(() => {
                setToasts(prev => prev.filter(t => t.id !== id));
            }, duration);
        }
    }, []);

    const removeToast = useCallback((id) => {
        setToasts(prev => prev.filter(t => t.id !== id));
    }, []);

    const success = useCallback((msg, dur) => addToast(msg, 'success', dur), [addToast]);
    const error = useCallback((msg, dur) => addToast(msg, 'error', dur), [addToast]);
    const info = useCallback((msg, dur) => addToast(msg, 'info', dur), [addToast]);

    const COLORS = {
        success: 'bg-emerald-50 dark:bg-emerald-900/30 border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300',
        error: 'bg-red-50 dark:bg-red-900/30 border-red-200 dark:border-red-800 text-red-700 dark:text-red-300',
        info: 'bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-300',
    };

    return (
        <ToastContext.Provider value={{ addToast, removeToast, success, error, info }}>
            {children}
            <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 max-w-sm">
                {toasts.map(t => (
                    <div key={t.id}
                        className={`flex items-start gap-3 px-4 py-3 rounded-xl border shadow-lg transition-all animate-slide-up ${COLORS[t.type] || COLORS.info}`}
                    >
                        <span className="material-symbols-outlined text-[18px] mt-0.5 shrink-0">
                            {t.type === 'success' ? 'check_circle' : t.type === 'error' ? 'error' : 'info'}
                        </span>
                        <p className="text-sm flex-1">{t.message}</p>
                        <button onClick={() => removeToast(t.id)}
                            className="text-current opacity-60 hover:opacity-100 transition">
                            <span className="material-symbols-outlined text-[16px]">close</span>
                        </button>
                    </div>
                ))}
            </div>
            <style
            dangerouslySetInnerHTML={{
                __html: `
                    @keyframes slide-up {
                        from { opacity: 0; transform: translateY(16px); }
                        to { opacity: 1; transform: translateY(0); }
                    }
                    .animate-slide-up { animation: slide-up 0.25s ease-out; }
                `,
            }}
            />
        </ToastContext.Provider>
    );
}
