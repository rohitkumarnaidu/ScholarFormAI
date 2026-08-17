'use client';
import { useState, useEffect } from 'react';
import { useAuth } from '@/src/context/AuthContext';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { fetchWithRetry } from '@/src/utils/fetchWithRetry';
import ErrorBoundary from '@/src/components/ErrorBoundary';
import { BarChart, Coins, Gauge, Key, LineChart, PieChart } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

function ApiKeysUsageInner() {
    const { user, isLoggedIn, loading } = useAuth();
    const router = useRouter();
    
    const [usage, setUsage] = useState({});
    const [keys, setKeys] = useState([]);
    const [hours, setHours] = useState(24);

    useEffect(() => {
        if (!loading && !isLoggedIn) router.push('/login?next=/api-keys/usage');
    }, [loading, isLoggedIn, router]);

    useEffect(() => {
        if (!isLoggedIn) return;

        const fetchUsage = async () => {
            try {
                const res = await fetchWithRetry(`${API_BASE}/api/v1/keys/usage?hours=${hours}`, {
                    headers: { Authorization: `Bearer ${user?.access_token || ''}` },
                });
                if (res.ok) setUsage(await res.json());
            } catch (e) {
                toast.error('Failed to load usage data');
            }
        };

        const fetchKeys = async () => {
            try {
                const res = await fetchWithRetry(`${API_BASE}/api/v1/keys`, {
                    headers: { Authorization: `Bearer ${user?.access_token || ''}` },
                });
                if (res.ok) setKeys(await res.json());
            } catch (e) { /* ignore */ }
        };

        fetchUsage();
        fetchKeys();
    }, [isLoggedIn, hours, user?.access_token]);

    const totalRequests = Object.values(usage).reduce((sum, u) => sum + u.total_requests, 0);
    const totalTokens = Object.values(usage).reduce((sum, u) => sum + u.total_tokens, 0);

    if (loading) return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-900 py-8">
            <div className="max-w-4xl mx-auto px-4">
                <div className="mb-8"><div className="h-9 w-48 bg-slate-200 dark:bg-slate-700 rounded animate-pulse mb-2" /><div className="h-5 w-64 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" /></div>
                <div className="grid grid-cols-1 md:grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                    {[1,2,3].map(i => <div key={i} className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6"><div className="h-4 w-24 bg-slate-200 dark:bg-slate-700 rounded animate-pulse mb-2" /><div className="h-8 w-20 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" /></div>)}
                </div>
                <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6"><div className="h-6 w-40 bg-slate-200 dark:bg-slate-700 rounded animate-pulse mb-4" />{[1,2,3].map(i => <div key={i} className="h-12 bg-slate-200 dark:bg-slate-700 rounded animate-pulse mb-2" />)}</div>
            </div>
        </div>
    );

    const TIME_OPTIONS = [
        { value: 1, label: 'Last Hour' },
        { value: 24, label: 'Last 24 Hours' },
        { value: 168, label: 'Last 7 Days' },
        { value: 720, label: 'Last 30 Days' },
    ];

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-900 py-8">
            <div className="max-w-4xl mx-auto px-4">
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-8 gap-4">
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900 dark:text-white">Usage Analytics</h1>
                        <p className="text-slate-600 dark:text-slate-400 mt-1">Monitor API key consumption, rate limits, and provider performance.</p>
                    </div>
                    <div className="flex gap-3">
                        <a href="/api-keys" className="px-4 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition text-sm font-medium">
                            Manage Keys
                        </a>
                        <select value={hours} onChange={e => setHours(Number(e.target.value))}
                            className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500">
                            {TIME_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                        </select>
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                    <div className="p-6 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700">
                        <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400 mb-2">
                            <BarChart className="text-[18px]" />
                            <span>Total Requests</span>
                        </div>
                        <p className="text-3xl font-bold text-slate-900 dark:text-white">{totalRequests.toLocaleString()}</p>
                    </div>
                    <div className="p-6 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700">
                        <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400 mb-2">
                            <Coins className="text-[18px]" />
                            <span>Total Tokens</span>
                        </div>
                        <p className="text-3xl font-bold text-slate-900 dark:text-white">{totalTokens.toLocaleString()}</p>
                    </div>
                    <div className="p-6 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700">
                        <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400 mb-2">
                            <Key className="text-[18px]" />
                            <span>Active Keys</span>
                        </div>
                        <p className="text-3xl font-bold text-slate-900 dark:text-white">{keys.filter(k => k.is_active).length} / {keys.length}</p>
                    </div>
                </div>

                <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden mb-8">
                    <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
                        <h2 className="text-lg font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                            <PieChart className="text-[20px] text-indigo-500" />
                            Usage by Provider
                        </h2>
                    </div>
                    {Object.keys(usage).length === 0 ? (
                        <div className="p-12 text-center">
                            <LineChart className="text-5xl text-slate-300 dark:text-slate-600 mb-4" />
                            <p className="text-slate-500 dark:text-slate-400">No usage data available for this period.</p>
                            <p className="text-sm text-slate-400 dark:text-slate-500 mt-1">Usage tracking starts after your first API call.</p>
                        </div>
                    ) : (
                        <div className="divide-y divide-slate-200 dark:divide-slate-700">
                            {Object.entries(usage).map(([provider, data]) => {
                                const maxReq = Math.max(...Object.values(usage).map(u => u.total_requests), 1);
                                const pct = (data.total_requests / maxReq) * 100;
                                return (
                                    <div key={provider} className="px-6 py-4">
                                        <div className="flex items-center justify-between mb-2">
                                            <p className="font-medium text-slate-900 dark:text-white capitalize flex items-center gap-2">
                                                <span className="w-2 h-2 rounded-full bg-indigo-500" />
                                                {provider}
                                            </p>
                                            <div className="text-right">
                                                <p className="font-medium text-slate-900 dark:text-white">{data.total_requests.toLocaleString()} req</p>
                                                <p className="text-xs text-slate-400">{data.total_tokens.toLocaleString()} tokens · {data.avg_response_time_ms}ms avg</p>
                                            </div>
                                        </div>
                                        <div className="w-full bg-slate-100 dark:bg-slate-700 rounded-full h-2">
                                            <div className="bg-gradient-to-r from-indigo-400 to-indigo-600 h-2 rounded-full transition-all duration-500" style={{ width: `${Math.max(2, pct)}%` }} />
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>

                <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
                    <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
                        <h2 className="text-lg font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                            <Gauge className="text-[20px] text-indigo-500" />
                            Rate Limit Status
                        </h2>
                    </div>
                    {keys.length === 0 ? (
                        <div className="p-8 text-center text-slate-500 dark:text-slate-400">
                            <p>No keys configured. <a href="/api-keys" className="text-indigo-500 hover:underline">Add API keys</a></p>
                        </div>
                    ) : (
                        <div className="divide-y divide-slate-200 dark:divide-slate-700">
                            {keys.map(key => {
                                const usagePct = Math.min(100, (key.total_requests / Math.max(key.daily_quota, 1)) * 100);
                                return (
                                    <div key={key.id} className="px-6 py-4">
                                        <div className="flex items-center justify-between mb-2">
                                            <div className="flex items-center gap-2">
                                                <span className={`w-2 h-2 rounded-full ${key.is_active ? 'bg-emerald-500' : 'bg-slate-400'}`} />
                                                <p className="font-medium text-slate-900 dark:text-white capitalize">{key.provider}</p>
                                                {key.key_label && <span className="text-xs text-slate-400">({key.key_label})</span>}
                                            </div>
                                            <span className="text-xs text-slate-400">{key.total_requests.toLocaleString()} total requests</span>
                                        </div>
                                        <div className="grid grid-cols-1 sm:grid-cols-1 md:grid-cols-3 gap-4 text-xs text-slate-500 dark:text-slate-400 mb-2">
                                            <span>{key.rate_limit_per_minute}/min</span>
                                            <span>{key.rate_limit_per_hour}/hour</span>
                                            <span>{key.daily_quota.toLocaleString()}/day</span>
                                        </div>
                                        <div className="w-full bg-slate-100 dark:bg-slate-700 rounded-full h-2">
                                            <div className={`h-2 rounded-full transition-all duration-500 ${usagePct > 80 ? 'bg-red-500' : usagePct > 50 ? 'bg-amber-500' : 'bg-emerald-500'}`}
                                                style={{ width: `${Math.max(1, usagePct)}%` }} />
                                        </div>
                                        <p className="text-[10px] text-slate-400 mt-1">{usagePct.toFixed(1)}% of daily quota used</p>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default function ApiKeysUsagePage() {
    return <ErrorBoundary><ApiKeysUsageInner /></ErrorBoundary>;
}
