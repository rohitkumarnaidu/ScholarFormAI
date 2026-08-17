// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import usePageTitle from '@/src/hooks/usePageTitle';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import MetricsCard from '@/src/components/MetricsCard';
import HealthStatusIndicator from '@/src/components/HealthStatusIndicator';
import Skeleton from '@/src/components/ui/Skeleton';
import { getMetricsDb, getMetricsHealth, getMetricsDashboard } from '@/src/services/api';
import { useAuth } from '@/src/context/AuthContext';
import { Activity, Badge, Bot, Info, Key, LineChart, RefreshCw, Server, Shield, User, Users } from 'lucide-react';

// ── Role Telemetry helpers ───────────────────────────────────
function TelemetryRow({ label, value, mono = false, highlight = false }) {
    return (
        <div className="flex items-start justify-between gap-4 py-3 border-b border-slate-100 dark:border-slate-800 last:border-0">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider shrink-0 pt-0.5">{label}</span>
            <span className={`text-sm font-medium text-right break-all leading-relaxed ${mono ? 'font-mono' : ''} ${highlight ? 'text-primary font-bold' : 'text-slate-900 dark:text-white'}`}>
                {value ?? <span className="text-slate-400 italic">not set</span>}
            </span>
        </div>
    );
}

function RoleBadge({ role }) {
    const isAdmin = role === 'admin';
    return (
        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider border ${isAdmin
            ? 'bg-purple-50 dark:bg-purple-900/20 text-purple-700 dark:text-purple-400 border-purple-200 dark:border-purple-800'
            : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-700'
            }`}>
            {isAdmin ? <Shield className="text-[14px]" /> : <User className="text-[14px]" />}
            {role || 'user'}
        </span>
    );
}

export default function AdminDashboard() {
    usePageTitle('Admin Dashboard');
    const router = useRouter();
    const { user } = useAuth();
    const [dbMetrics, setDbMetrics] = useState(null);
    const [healthData, setHealthData] = useState(null);
    const [dashboardData, setDashboardData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [snapshotTime, setSnapshotTime] = useState(null);

    const applyMetricsResults = ([db, health, dashboard]) => {
        const nextDbMetrics = db.status === 'fulfilled' ? db.value : null;
        const nextHealthData = health.status === 'fulfilled' ? health.value : null;
        const nextDashboardData = dashboard.status === 'fulfilled' ? dashboard.value : null;
        const unavailableCount = [nextDbMetrics, nextHealthData, nextDashboardData].filter((v) => !v).length;

        setDbMetrics(nextDbMetrics);
        setHealthData(nextHealthData);
        setDashboardData(nextDashboardData);
        setSnapshotTime(new Date());

        if (unavailableCount === 0) { setError(''); return; }
        setError(unavailableCount === 3 ? 'Metrics services are currently unavailable.' : 'Some metrics are currently unavailable.');
    };

    useEffect(() => {
        const loadAll = async () => {
            setLoading(true);
            setError('');
            const results = await Promise.allSettled([getMetricsDb(), getMetricsHealth(), getMetricsDashboard()]);
            applyMetricsResults(results);
            setLoading(false);
        };
        loadAll();
    }, []);

    const refreshMetrics = async () => {
        setLoading(true);
        const results = await Promise.allSettled([getMetricsDb(), getMetricsHealth(), getMetricsDashboard()]);
        applyMetricsResults(results);
        setLoading(false);
    };

    // Admin role guard
    const appRole = user?.app_metadata?.role;
    const metaRole = user?.user_metadata?.role;
    const isAdmin = appRole === 'admin' || metaRole === 'admin';

    useEffect(() => {
        if (user && !isAdmin) router.replace('/dashboard');
    }, [isAdmin, router, user]);

    if (user && !isAdmin) return null;

    // ── Role telemetry data ───────────────────────────────
    const sessionIssued = user?.iat ? new Date(user.iat * 1000).toLocaleString() : null;
    const sessionExpires = user?.exp ? new Date(user.exp * 1000).toLocaleString() : null;
    const authProvider = user?.app_metadata?.provider || user?.app_metadata?.providers?.[0] || 'password';
    const emailConfirmed = user?.email_confirmed_at ? new Date(user.email_confirmed_at).toLocaleString() : 'Not confirmed';
    const lastSignIn = user?.last_sign_in_at ? new Date(user.last_sign_in_at).toLocaleString() : null;

    return (
        <div className="min-h-screen bg-background-light dark:bg-background-dark animate-in fade-in duration-500">
            <main className="max-w-7xl mx-auto px-4 py-8">
                {/* ── Header ─────────────────────────────── */}
                <div className="flex items-center justify-between mb-8">
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900 dark:text-white flex items-center gap-3">
                            <Activity className="text-primary text-4xl" />
                            Admin Dashboard
                        </h1>
                        <p className="text-slate-600 dark:text-slate-400 mt-1">System health, metrics, and AI performance monitoring</p>
                        {snapshotTime && (
                            <p className="text-xs text-slate-400 dark:text-slate-600 mt-0.5">
                                Last refreshed: {snapshotTime.toLocaleTimeString()}
                            </p>
                        )}
                    </div>
                    <button onClick={refreshMetrics} disabled={loading}
                        className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-lg font-medium transition-colors disabled:opacity-50 shadow-md shadow-primary/20 active:scale-95 min-h-[44px]">
                        <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                        Refresh
                    </button>
                </div>

                {error && (
                    <div className="p-4 mb-6 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 text-amber-700 dark:text-amber-400 text-sm">
                        {error}
                    </div>
                )}

                {/* ── Service Health ─────────────────────── */}
                <section className="mb-8">
                    <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                        <Server className="text-green-500" />
                        Service Health
                    </h2>
                    <div className="grid grid-cols-1 md:grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                        <HealthStatusIndicator
                            status={dbMetrics?.status || 'unknown'}
                            label="Database (Supabase)"
                            details={dbMetrics ? `${dbMetrics.document_count ?? 0} documents stored` : 'Loading...'}
                        />
                        <HealthStatusIndicator
                            status={healthData?.status || 'unknown'}
                            label="System Readiness"
                            details={healthData?.details || 'Checking...'}
                        />
                        <HealthStatusIndicator
                            status={healthData?.aiServicesStatus || 'unknown'}
                            label="AI Services"
                            details={healthData?.aiServicesDetails || 'Checking...'}
                        />
                        <HealthStatusIndicator
                            status={healthData?.grobidStatus || 'unknown'}
                            label="GROBID Parser"
                            details={healthData?.grobidDetails || 'Checking...'}
                        />
                    </div>
                </section>

                {/* ── Key Metrics ────────────────────────── */}
                <section className="mb-8">
                    <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                        <LineChart className="text-primary" />
                        Key Metrics
                    </h2>
                    <div className="grid grid-cols-1 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 stagger-children">
                        <MetricsCard title="Total Documents" value={dbMetrics?.document_count ?? '—'} icon="description" color="primary" isLoading={loading} />
                        <MetricsCard title="Processing Success" value={typeof dashboardData?.successRatePct === 'number' ? `${dashboardData.successRatePct.toFixed(1)}%` : '—'} icon="check_circle" color="green" subtitle="Completion rate" isLoading={loading} />
                        <MetricsCard title="Avg Confidence" value={typeof dashboardData?.avgConfidencePct === 'number' ? `${dashboardData.avgConfidencePct.toFixed(1)}%` : '—'} icon="psychology" color="purple" subtitle="Quality score average" isLoading={loading} />
                        <MetricsCard title="Error Rate" value={typeof dashboardData?.errorRatePct === 'number' ? `${dashboardData.errorRatePct.toFixed(1)}%` : '—'} icon="error_outline" color={dashboardData?.errorRatePct > 5 ? 'red' : 'amber'} subtitle="Across recorded calls" isLoading={loading} />
                    </div>
                </section>

                {/* ── AI Performance ─────────────────────── */}
                {dashboardData && (
                    <section className="mb-8">
                        <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                            <Bot className="text-purple-500" />
                            AI Performance
                        </h2>
                        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm">
                            <div className="grid grid-cols-1 md:grid-cols-1 md:grid-cols-3 gap-6">
                                <div>
                                    <p className="text-sm text-slate-500 dark:text-slate-400 mb-1">Model</p>
                                    <p className="text-lg font-semibold text-slate-900 dark:text-white">{dashboardData.modelLabel || 'N/A'}</p>
                                </div>
                                <div>
                                    <p className="text-sm text-slate-500 dark:text-slate-400 mb-1">Total Processed</p>
                                    <p className="text-lg font-semibold text-slate-900 dark:text-white">{dashboardData.totalProcessed ?? 0}</p>
                                </div>
                                <div>
                                    <p className="text-sm text-slate-500 dark:text-slate-400 mb-1">Avg Processing Time</p>
                                    <p className="text-lg font-semibold text-slate-900 dark:text-white">
                                        {typeof dashboardData.avgProcessingTimeSeconds === 'number' ? `${dashboardData.avgProcessingTimeSeconds.toFixed(2)}s` : 'N/A'}
                                    </p>
                                </div>
                            </div>
                            <div className="mt-6 pt-6 border-t border-slate-200 dark:border-slate-700 grid grid-cols-1 md:grid-cols-1 md:grid-cols-2 gap-6">
                                <div>
                                    <p className="text-sm text-slate-500 dark:text-slate-400 mb-1">Automation Level</p>
                                    <p className="text-lg font-semibold text-slate-900 dark:text-white">{dashboardData.automationLevel || 'Unknown'}</p>
                                </div>
                                <div>
                                    <p className="text-sm text-slate-500 dark:text-slate-400 mb-1">Fallback Rate</p>
                                    <p className="text-lg font-semibold text-slate-900 dark:text-white">
                                        {typeof dashboardData.fallbackRatePct === 'number' ? `${dashboardData.fallbackRatePct.toFixed(1)}%` : 'N/A'}
                                    </p>
                                </div>
                            </div>
                            {dashboardData.abTesting && (
                                <div className="mt-6 pt-6 border-t border-slate-200 dark:border-slate-700">
                                    <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">A/B Testing Results</h3>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        {Object.entries(dashboardData.abTesting).map(([variant, stats]) => (
                                            <div key={variant} className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-100 dark:border-slate-700">
                                                <p className="text-xs font-medium text-slate-500 uppercase">{variant}</p>
                                                <p className="text-lg font-bold text-slate-900 dark:text-white">{typeof stats === 'object' ? JSON.stringify(stats) : stats}</p>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    </section>
                )}

                {/* ── Role Telemetry ─────────────────────── */}
                <section className="mb-8">
                    <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                        <Users className="text-purple-500" />
                        Admin Role Telemetry
                    </h2>
                    <div className="grid grid-cols-1 md:grid-cols-1 md:grid-cols-2 gap-4">
                        {/* Identity card */}
                        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm">
                            <div className="flex items-center gap-3 mb-4">
                                <div className="p-2.5 bg-purple-50 dark:bg-purple-900/20 rounded-xl">
                                    <Badge className="text-purple-600 dark:text-purple-400" />
                                </div>
                                <div>
                                    <h3 className="font-bold text-slate-900 dark:text-white text-sm">Identity &amp; Role</h3>
                                    <p className="text-xs text-slate-500 dark:text-slate-400">Resolved from JWT claims</p>
                                </div>
                            </div>
                            <div className="flex flex-col">
                                <TelemetryRow label="Email" value={user?.email} />
                                <TelemetryRow label="User ID" value={user?.id?.slice(0, 16) + '…'} mono />
                                <TelemetryRow label="app_metadata.role" value={appRole} highlight={!!appRole} />
                                <TelemetryRow label="user_metadata.role" value={metaRole} highlight={!!metaRole} />
                                <div className="pt-3 flex items-center justify-between">
                                    <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Effective role</span>
                                    <RoleBadge role={isAdmin ? 'admin' : (appRole || metaRole || 'user')} />
                                </div>
                            </div>
                        </div>

                        {/* Session card */}
                        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm">
                            <div className="flex items-center gap-3 mb-4">
                                <div className="p-2.5 bg-blue-50 dark:bg-blue-900/20 rounded-xl">
                                    <Key className="text-blue-600 dark:text-blue-400" />
                                </div>
                                <div>
                                    <h3 className="font-bold text-slate-900 dark:text-white text-sm">Session &amp; Auth</h3>
                                    <p className="text-xs text-slate-500 dark:text-slate-400">Active JWT session details</p>
                                </div>
                            </div>
                            <div className="flex flex-col">
                                <TelemetryRow label="Auth Provider" value={authProvider} />
                                <TelemetryRow label="Email Confirmed" value={emailConfirmed} />
                                <TelemetryRow label="Last Sign-in" value={lastSignIn} />
                                <TelemetryRow label="Token Issued" value={sessionIssued} mono />
                                <TelemetryRow label="Token Expires" value={sessionExpires} mono />
                            </div>
                        </div>
                    </div>

                    {/* Access log notice */}
                    <div className="mt-4 p-4 rounded-xl bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-900/30 flex items-start gap-3">
                        <Info className="text-amber-500 text-xl shrink-0 mt-0.5" />
                        <p className="text-xs text-amber-700 dark:text-amber-400 leading-relaxed">
                            <strong>Audit notice:</strong> This page is restricted to <code className="font-mono bg-amber-100 dark:bg-amber-900/40 px-1 rounded">admin</code>-role accounts.
                            All access attempts are blocked client-side via role guard. Ensure server-side route protection is also enforced at the API layer.
                        </p>
                    </div>
                </section>

                {/* Skeletons while loading */}
                {loading && !dbMetrics && !healthData && (
                    <div className="animate-in fade-in duration-500">
                        <section className="mb-8">
                            <Skeleton className="h-6 w-40 mb-4" />
                            <div className="grid grid-cols-1 md:grid-cols-1 md:grid-cols-3 gap-4">
                                {[1, 2, 3].map(i => <Skeleton key={i} className="h-24 w-full" rounded="rounded-xl" />)}
                            </div>
                        </section>
                        <section className="mb-8">
                            <Skeleton className="h-6 w-32 mb-4" />
                            <div className="grid grid-cols-1 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                                {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-32 w-full" rounded="rounded-xl" />)}
                            </div>
                        </section>
                    </div>
                )}
            </main>
        </div>
    );
}
