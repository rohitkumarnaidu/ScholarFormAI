// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import usePageTitle from '@/src/hooks/usePageTitle';
import { useState, useEffect, useCallback, useRef } from 'react';
import { loadNotifications, saveNotifications } from '@/src/utils/notifications';

// ── Notification preference keys in localStorage ─────────────
const PREFS_KEY = 'scholarform_notif_prefs';

const DEFAULT_PREFS = {
    processingAlerts: true,
    errorAlerts: true,
    systemUpdates: true,
    weeklyDigest: false,
    soundEnabled: false,
};

function loadPrefs() {
    if (typeof window === 'undefined') return DEFAULT_PREFS;
    try {
        const raw = localStorage.getItem(PREFS_KEY);
        return raw ? { ...DEFAULT_PREFS, ...JSON.parse(raw) } : DEFAULT_PREFS;
    } catch {
        return DEFAULT_PREFS;
    }
}

function savePrefs(prefs) {
    if (typeof window === 'undefined') return;
    try { localStorage.setItem(PREFS_KEY, JSON.stringify(prefs)); } catch { /* ignore */ }
}

const PREF_ITEMS = [
    {
        key: 'processingAlerts',
        label: 'Manuscript Processing Alerts',
        desc: 'Get notified when formatting or AI processing completes',
        icon: 'description',
        color: 'text-primary',
    },
    {
        key: 'errorAlerts',
        label: 'Error & Failure Alerts',
        desc: 'Receive alerts when a job fails or encounters an error',
        icon: 'error_outline',
        color: 'text-red-500',
    },
    {
        key: 'systemUpdates',
        label: 'System Updates',
        desc: 'Platform announcements, new templates, and feature releases',
        icon: 'campaign',
        color: 'text-blue-500',
    },
    {
        key: 'weeklyDigest',
        label: 'Weekly Digest',
        desc: 'Summary of your activity and usage stats delivered weekly',
        icon: 'calendar_month',
        color: 'text-purple-500',
    },
    {
        key: 'soundEnabled',
        label: 'Sound Notifications',
        desc: 'Play a subtle sound when a new notification arrives',
        icon: 'notifications_active',
        color: 'text-amber-500',
    },
];

// ── Main page ────────────────────────────────────────────────
export default function NotificationsPage() {
    usePageTitle('Notifications');
    const [notifications, setNotifications] = useState([]);
    const [prefs, setPrefs] = useState(DEFAULT_PREFS);
    const [prefsSaved, setPrefsSaved] = useState(false);
    const [undoState, setUndoState] = useState(null);
    const undoTimeoutRef = useRef(null);

    useEffect(() => {
        setNotifications(loadNotifications());
        setPrefs(loadPrefs());
    }, []);

    // Persist notifications
    useEffect(() => { saveNotifications(notifications); }, [notifications]);

    // ── Notification actions ───────────────────────────────
    const markAsRead = useCallback((id) => setNotifications((prev) => prev.map((n) => n.id === id ? { ...n, read: true } : n)), []);
    const markAllRead = useCallback(() => {
        setNotifications((prev) => {
            if (!prev.some(n => !n.read)) return prev;
            setUndoState(prev);
            if (undoTimeoutRef.current) clearTimeout(undoTimeoutRef.current);
            undoTimeoutRef.current = setTimeout(() => setUndoState(null), 5000);
            return prev.map(n => ({ ...n, read: true }));
        });
    }, []);
    const handleUndo = useCallback(() => {
        if (undoState) { setNotifications(undoState); setUndoState(null); clearTimeout(undoTimeoutRef.current); }
    }, [undoState]);
    const deleteNotification = useCallback((id) => setNotifications((prev) => prev.filter((n) => n.id !== id)), []);
    const clearAll = useCallback(() => setNotifications([]), []);
    const unreadCount = notifications.filter((n) => !n.read).length;

    // ── Preference actions ─────────────────────────────────
    const togglePref = (key) => {
        setPrefs(prev => {
            const next = { ...prev, [key]: !prev[key] };
            savePrefs(next);
            return next;
        });
        // Flash saved indicator briefly
        setPrefsSaved(true);
        setTimeout(() => setPrefsSaved(false), 1500);
    };

    // ── Helpers ────────────────────────────────────────────
    const typeIcon = (type) => {
        const map = {
            success: ['check_circle', 'text-green-500'],
            error: ['error', 'text-red-500'],
            info: ['info', 'text-blue-500'],
            warning: ['warning', 'text-amber-500'],
        };
        const [icon, color] = map[type] || map.info;
        return <span className={`material-symbols-outlined ${color}`}>{icon}</span>;
    };

    const formatTime = (ts) => {
        try {
            const diff = Date.now() - new Date(ts);
            if (diff < 60000) return 'Just now';
            if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
            if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
            return new Date(ts).toLocaleDateString();
        } catch { return ''; }
    };

    return (
        <div className="min-h-screen bg-background-light dark:bg-background-dark animate-in fade-in duration-500 flex flex-col">
            <main className="max-w-3xl mx-auto px-4 py-8 w-full flex flex-col gap-10">

                {/* ── Header ───────────────────────────────── */}
                <div className="flex items-center justify-between gap-4">
                    <h1 className="text-3xl font-bold text-slate-900 dark:text-white flex items-center gap-3">
                        <span className="material-symbols-outlined text-primary text-4xl">notifications</span>
                        Notifications
                        {unreadCount > 0 && (
                            <span className="px-2 py-0.5 text-sm bg-red-500 text-white rounded-full font-medium">{unreadCount}</span>
                        )}
                    </h1>
                    <div className="flex gap-2 shrink-0">
                        {unreadCount > 0 && (
                            <button onClick={markAllRead}
                                className="text-sm px-3 py-2 text-primary hover:bg-primary/10 rounded-lg transition-colors min-h-[44px]">
                                Mark all read
                            </button>
                        )}
                        {notifications.length > 0 && (
                            <button onClick={clearAll}
                                className="text-sm px-3 py-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors min-h-[44px]">
                                Clear all
                            </button>
                        )}
                    </div>
                </div>

                {/* ── Undo banner ───────────────────────────── */}
                {undoState && (
                    <div className="flex items-center justify-between p-4 bg-slate-800 text-white rounded-lg shadow-lg animate-in slide-in-from-top-2 duration-300">
                        <span className="text-sm font-medium">All notifications marked as read.</span>
                        <button onClick={handleUndo}
                            className="text-sm font-bold text-blue-400 hover:text-blue-300 transition-colors uppercase tracking-wide">
                            Undo
                        </button>
                    </div>
                )}

                {/* ── Notification list ─────────────────────── */}
                <section>
                    {notifications.length === 0 ? (
                        <div className="text-center py-16">
                            <span className="material-symbols-outlined text-6xl text-slate-300 dark:text-slate-600">notifications_none</span>
                            <p className="text-slate-500 dark:text-slate-400 mt-4 text-lg">No notifications yet</p>
                            <p className="text-slate-400 dark:text-slate-500 text-sm mt-1">You&apos;ll see processing updates and system alerts here.</p>
                        </div>
                    ) : (
                        <ul className="space-y-2" role="list" aria-label="Notifications">
                            {notifications.map((n) => (
                                <li key={n.id}
                                    className={`flex items-start gap-3 p-4 rounded-xl border transition-all cursor-pointer hover:shadow-md ${n.read ? 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800' : 'bg-primary/5 border-primary/20'}`}
                                    onClick={() => markAsRead(n.id)}>
                                    <div className="mt-0.5">{typeIcon(n.type)}</div>
                                    <div className="flex-1 min-w-0">
                                        <p className={`text-sm ${n.read ? 'text-slate-600 dark:text-slate-400' : 'text-slate-900 dark:text-white font-medium'}`}>{n.message}</p>
                                        <p className="text-xs text-slate-400 mt-1">{formatTime(n.timestamp)}</p>
                                    </div>
                                    <button onClick={(e) => { e.stopPropagation(); deleteNotification(n.id); }}
                                        className="text-slate-400 hover:text-red-500 transition-colors p-1 rounded min-w-[36px] min-h-[36px] flex items-center justify-center"
                                        aria-label="Delete notification">
                                        <span className="material-symbols-outlined text-lg">close</span>
                                    </button>
                                </li>
                            ))}
                        </ul>
                    )}
                </section>

                {/* ── Notification Preferences ──────────────── */}
                <section className="flex flex-col gap-4">
                    <div className="flex items-center justify-between gap-2">
                        <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                            <span className="material-symbols-outlined text-slate-500 dark:text-slate-400 text-2xl">tune</span>
                            Notification Preferences
                        </h2>
                        {prefsSaved && (
                            <span className="text-xs font-semibold text-green-500 flex items-center gap-1 animate-in fade-in duration-200">
                                <span className="material-symbols-outlined text-base">check_circle</span>
                                Saved
                            </span>
                        )}
                    </div>
                    <p className="text-sm text-slate-500 dark:text-slate-400 -mt-2">
                        Choose which events trigger notifications. Changes are saved automatically.
                    </p>

                    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl divide-y divide-slate-100 dark:divide-slate-800 shadow-sm">
                        {PREF_ITEMS.map(({ key, label, desc, icon, color }) => (
                            <div key={key} className="flex items-center justify-between p-5 gap-4">
                                <div className="flex items-center gap-4 min-w-0">
                                    <div className={`p-2 rounded-lg bg-slate-50 dark:bg-slate-800 shrink-0 ${color}`}>
                                        <span className="material-symbols-outlined text-xl">{icon}</span>
                                    </div>
                                    <div className="min-w-0">
                                        <p className="font-semibold text-slate-800 dark:text-white text-sm">{label}</p>
                                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 leading-relaxed">{desc}</p>
                                    </div>
                                </div>
                                <button
                                    onClick={() => togglePref(key)}
                                    role="switch"
                                    aria-checked={prefs[key]}
                                    aria-label={label}
                                    className={`relative inline-flex h-7 w-12 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 ${prefs[key] ? 'bg-primary' : 'bg-slate-200 dark:bg-slate-700'}`}
                                >
                                    <span className={`pointer-events-none inline-block h-6 w-6 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${prefs[key] ? 'translate-x-5' : 'translate-x-0'}`} />
                                </button>
                            </div>
                        ))}
                    </div>

                    <p className="text-xs text-slate-400 dark:text-slate-600 text-center">
                        Preferences are stored locally in your browser.
                    </p>
                </section>
            </main>
        </div>
    );
}
