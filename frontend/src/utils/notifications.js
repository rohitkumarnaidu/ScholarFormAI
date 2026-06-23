// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

export const STORAGE_KEY = 'scholarform_notifications';

const createId = () => {
    if (typeof crypto !== 'undefined') {
        if (typeof crypto.randomUUID === 'function') {
            return crypto.randomUUID();
        }

        if (typeof crypto.getRandomValues === 'function') {
            const bytes = new Uint8Array(16);
            crypto.getRandomValues(bytes);
            return Array.from(bytes, (value) => value.toString(16).padStart(2, '0')).join('');
        }
    }

    return `notif-${Date.now()}`;
};

export const createNotification = (type, message, meta = {}) => ({
    id: createId(),
    type,
    message,
    read: false,
    timestamp: new Date().toISOString(),
    ...meta,
});

export const loadNotifications = () => {
    if (typeof window === 'undefined') return [];
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        return raw ? JSON.parse(raw) : [];
    } catch {
        return [];
    }
};

export const saveNotifications = (items) => {
    if (typeof window === 'undefined') return;
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
    } catch {
        // ignore quota errors
    }
};
