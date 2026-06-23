// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import { useState, useEffect } from 'react';
import { useAuth } from '@/src/context/AuthContext';
import { useRouter } from 'next/navigation';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

export default function ApiKeysUsagePage() {
    const { user, isLoggedIn, loading } = useAuth();
    const router = useRouter();
    const [usage, setUsage] = useState({});
    const [keys, setKeys] = useState([]);
    const [hours, setHours] = useState(24);
    const [error, setError] = useState('');

    useEffect(() => {
        if (!loading && !isLoggedIn) {
            router.push('/login?next=/api-keys/usage');
        }
    }, [loading, isLoggedIn, router]);

    useEffect(() => {
        if (!isLoggedIn) return;

        const fetchUsage = async () => {
            try {
                const res = await fetch(`${API_BASE}/api/v1/keys/usage?hours=${hours}`, {
                    headers: { Authorization: `Bearer ${user?.access_token || ''}` },
                });
                if (res.ok) setUsage(await res.json());
            } catch (e) {
                setError('Failed to load usage data');
            }
        };

        const fetchKeys = async () => {
            try {
                const res = await fetch(`${API_BASE}/api/v1/keys`, {
                    headers: { Authorization: `Bearer ${user?.access_token || ''}` },
                });
                if (res.ok) setKeys(await res.json());
            } catch (e) { /* ignore */ }
        };

        fetchUsage();
        fetchKeys();
    }, [isLoggedIn, hours, user?.access_token]);

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="animate-spin h-8 w-8 border-4 border-indigo-500 border-t-transparent rounded-full" />
            </div>
        );
    }

    const totalRequests = Object.values(usage).reduce((sum, u) => sum + u.total_requests, 0);
    const totalTokens = Object.values(usage).reduce((sum, u) => sum + u.total_tokens, 0);

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8 px-4">
            <div className="max-w-4xl mx-auto">
                <div className="flex items-center justify-between mb-8">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">API Key Usage</h1>
                        <p className="text-gray-600 dark:text-gray-400 mt-1">Monitor your API key consumption and rate limits.</p>
                    </div>
                    <select
                        value={hours}
                        onChange={(e) => setHours(Number(e.target.value))}
                        className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    >
                        <option value={1}>Last 1 hour</option>
                        <option value={24}>Last 24 hours</option>
                        <option value={168}>Last 7 days</option>
                        <option value={720}>Last 30 days</option>
                    </select>
                </div>

                {error && (
                    <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300">
                        {error}
                    </div>
                )}

                {/* Summary Cards */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                    <div className="p-6 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
                        <p className="text-sm text-gray-500 dark:text-gray-400">Total Requests</p>
                        <p className="text-3xl font-bold text-gray-900 dark:text-white mt-1">{totalRequests.toLocaleString()}</p>
                    </div>
                    <div className="p-6 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
                        <p className="text-sm text-gray-500 dark:text-gray-400">Total Tokens</p>
                        <p className="text-3xl font-bold text-gray-900 dark:text-white mt-1">{totalTokens.toLocaleString()}</p>
                    </div>
                    <div className="p-6 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
                        <p className="text-sm text-gray-500 dark:text-gray-400">Active Keys</p>
                        <p className="text-3xl font-bold text-gray-900 dark:text-white mt-1">{keys.filter((k) => k.is_active).length}</p>
                    </div>
                </div>

                {/* Per-Provider Breakdown */}
                <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
                    <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Usage by Provider</h2>
                    </div>
                    {Object.keys(usage).length === 0 ? (
                        <div className="p-8 text-center text-gray-500 dark:text-gray-400">
                            No usage data available for this period.
                        </div>
                    ) : (
                        <div className="divide-y divide-gray-200 dark:divide-gray-700">
                            {Object.entries(usage).map(([provider, data]) => (
                                <div key={provider} className="px-6 py-4 flex items-center justify-between">
                                    <div>
                                        <p className="font-medium text-gray-900 dark:text-white capitalize">{provider}</p>
                                        <p className="text-sm text-gray-500 dark:text-gray-400">
                                            Avg response: {data.avg_response_time_ms}ms
                                        </p>
                                    </div>
                                    <div className="text-right">
                                        <p className="font-medium text-gray-900 dark:text-white">{data.total_requests.toLocaleString()} requests</p>
                                        <p className="text-sm text-gray-500 dark:text-gray-400">{data.total_tokens.toLocaleString()} tokens</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Rate Limit Status */}
                <div className="mt-8 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
                    <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Rate Limit Status</h2>
                    </div>
                    <div className="divide-y divide-gray-200 dark:divide-gray-700">
                        {keys.map((key) => (
                            <div key={key.id} className="px-6 py-4">
                                <div className="flex items-center justify-between mb-2">
                                    <p className="font-medium text-gray-900 dark:text-white capitalize">{key.provider}</p>
                                    <p className="text-sm text-gray-500 dark:text-gray-400">{key.total_requests.toLocaleString()} total</p>
                                </div>
                                <div className="space-y-2">
                                    <div>
                                        <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mb-1">
                                            <span>Per minute: {key.rate_limit_per_minute}</span>
                                            <span>Per hour: {key.rate_limit_per_hour}</span>
                                            <span>Daily: {key.daily_quota.toLocaleString()}</span>
                                        </div>
                                        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                                            <div
                                                className="bg-indigo-500 h-2 rounded-full transition-all"
                                                style={{ width: `${Math.min(100, (key.total_requests / key.daily_quota) * 100)}%` }}
                                            />
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
