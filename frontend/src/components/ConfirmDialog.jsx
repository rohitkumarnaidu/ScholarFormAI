"use client";
import React, { createContext, useContext, useState, useRef } from 'react';
import ConfirmDialog from './ui/ConfirmDialog';

const ConfirmContext = createContext();

export function ConfirmProvider({ children }) {
    const [open, setOpen] = useState(false);
    const [options, setOptions] = useState({ title: '', description: '', confirmLabel: '', variant: '' });
    const resolver = useRef();

    const confirm = (description, title = 'Confirm', confirmLabel = 'Confirm', variant = 'default') => {
        setOptions({ title, description, confirmLabel, variant });
        setOpen(true);
        return new Promise((resolve) => {
            resolver.current = resolve;
        });
    };

    const handleConfirm = () => {
        setOpen(false);
        if (resolver.current) resolver.current(true);
    };

    const handleCancel = () => {
        setOpen(false);
        if (resolver.current) resolver.current(false);
    };

    return (
        <ConfirmContext.Provider value={confirm}>
            {children}
            <ConfirmDialog 
                open={open} 
                title={options.title} 
                description={options.description} 
                confirmLabel={options.confirmLabel} 
                onConfirm={handleConfirm} 
                onCancel={handleCancel} 
                variant={options.variant} 
            />
        </ConfirmContext.Provider>
    );
}

export function useConfirm() {
    const context = useContext(ConfirmContext);
    if (!context) throw new Error('useConfirm must be used within ConfirmProvider');
    return context;
}
