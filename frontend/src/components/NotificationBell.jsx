// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useNotifications } from '@/context/NotificationContext';

export default function NotificationBell() {
    const [isOpen, setIsOpen] = useState(false);
    const dropdownRef = useRef(null);
    const router = useRouter();
    const { notifications, unreadCount, markAsRead, markAllAsRead } = useNotifications();

    useEffect(() => {
        const handleClick = (e) => {
            if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
                setIsOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClick);
        return () => document.removeEventListener('mousedown', handleClick);
    }, []);

    const recentItems = notifications.slice(0, 5);

    const formatTime = (ts) => {
        try {
            const diff = Date.now() - new Date(ts).getTime();
            if (diff < 60000) return 'Just now';
            if (diff < 3600000) return `${Math.floor(diff / 60000)}m`;
            if (diff < 86400000) return `${Math.floor(diff / 3600000)}h`;
            return `${Math.floor(diff / 86400000)}d`;
        } catch {
            return '';
        }
    };

    return (
        <div className="relative" ref={dropdownRef}>
            <button
                onClick={() => setIsOpen((open) => !open)}
                className="relative h-10 w-10 inline-flex items-center justify-center rounded-xl text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-white/10 transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
                aria-label={unreadCount > 0 ? `Notifications – ${unreadCount} unread` : 'Notifications'}
                aria-expanded={isOpen}
                aria-haspopup="menu"
            >
                <span className="material-symbols-outlined">notifications</span>
                {unreadCount > 0 && (
                    <span
                        role="status"
                        aria-label={`${unreadCount} unread notification${unreadCount > 1 ? 's' : ''}`}
                        className="absolute -top-0.5 -right-0.5 w-5 h-5 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center animate-pulse"
                    >
                        {unreadCount > 9 ? '9+' : unreadCount}
                    </span>
                )}
            </button>

            {isOpen && (
                <div
                    className="absolute right-0 top-full mt-2 w-80 bg-white rounded-xl border border-slate-200 dark:border-white/10 shadow-2xl z-50 overflow-hidden"
                    role="menu"
                    aria-label="Notifications menu"
                >
                    <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-white/10 ">
                        <p className="text-sm font-semibold text-slate-900 dark:text-white">Notifications</p>
                        {unreadCount > 0 && (
                            <button onClick={() => markAllAsRead()} className="text-xs text-primary hover:underline">
                                Mark all as read
                            </button>
                        )}
                    </div>

                    {recentItems.length === 0 ? (
                        <div className="px-4 py-8 text-center">
                            <span className="material-symbols-outlined text-3xl text-slate-300 dark:text-slate-600">notifications_none</span>
                            <p className="text-sm text-slate-500 dark:text-slate-400 mt-2">No notifications</p>
                        </div>
                    ) : (
                        <ul
                            className="max-h-72 overflow-y-auto divide-y divide-slate-100 dark:divide-white/10"
                            role="list"
                            aria-label="Recent notifications"
                            aria-live="polite"
                            aria-atomic="false"
                        >
                            {recentItems.map((n) => (
                                <li
                                    key={n.id}
                                    role="menuitem"
                                    onClick={() => markAsRead(n.id)}
                                    className={`px-4 py-3 cursor-pointer hover:bg-slate-50 dark:hover:bg-white/10 transition-colors ${!n.read_at ? 'bg-blue-50/50 dark:bg-white/5 ' : ''}`}
                                >
                                    <p className={`text-sm ${n.read_at ? 'text-slate-500' : 'text-slate-900 dark:text-blue-300 font-medium'} line-clamp-2`}>
                                        {n.body || n.message}
                                    </p>
                                    <p className="text-xs text-slate-400 mt-1">{formatTime(n.created_at || n.timestamp)}</p>
                                </li>
                            ))}
                        </ul>
                    )}

                    <div className="border-t border-slate-200 dark:border-white/10 px-4 py-2">
                        <button
                            onClick={() => { setIsOpen(false); router.push('/notifications'); }}
                            className="w-full text-center text-sm text-primary font-medium py-1 hover:underline focus:outline-none focus:ring-2 focus:ring-primary rounded"
                            aria-label="View all notifications"
                        >
                            View all notifications
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
