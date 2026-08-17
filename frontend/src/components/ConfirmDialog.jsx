'use client';
import { useState, useEffect, createContext, useContext, useCallback, useRef } from 'react';
import ConfirmDialog from './ui/ConfirmDialog';

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

    

    return (
        <ConfirmContext.Provider value={confirm}>
            {children}
            <ConfirmDialog
                open={state.open}
                title={state.title}
                description={state.message}
                confirmLabel={state.confirmLabel}
                cancelLabel="Cancel"
                danger={state.variant === 'danger'}
                onConfirm={handleConfirm}
                onCancel={handleCancel}
            />
        </ConfirmContext.Provider>
    );
}
