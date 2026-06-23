// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import usePageTitle from '@/src/hooks/usePageTitle';
import { useEffect, useState, useCallback } from 'react';
import { useTheme } from '@/src/context/ThemeContext';
import Footer from '@/src/components/Footer';
import { useAuth } from '@/src/context/AuthContext';
import { getUserTier, getRemainingQuota } from '@/src/lib/planTier';
import { SettingsSchema } from '@/src/lib/schemas';
import { z } from 'zod';
import { useToast } from '@/src/context/ToastContext';
import { ConfirmDialog } from '@/src/components/ui';
import { fetchWithAuth } from '@/src/services/api.core';

const SETTINGS_KEY = 'scholarform_settings';

const defaultSettings = {
    defaultTemplate: 'IEEE',
    defaultPageSize: 'Letter',
    defaultFastMode: false,
    defaultExportFormat: 'docx',
    emailNotifications: true,
    darkMode: false,
};

const loadSettings = () => {
    if (typeof window === 'undefined') return { ...defaultSettings };
    try {
        const raw = localStorage.getItem(SETTINGS_KEY);
        return raw ? { ...defaultSettings, ...JSON.parse(raw) } : { ...defaultSettings };
    } catch {
        return { ...defaultSettings };
    }
};

export default function SettingsPage() {
    usePageTitle('Settings');
    const { theme, setTheme } = useTheme();
    const { user } = useAuth();
    const { addToast } = useToast();
    const searchParams = typeof window !== 'undefined' ? new URLSearchParams(window.location.search) : null;
    const initialTab = searchParams?.get('tab') || 'general';
    const [activeTab, setActiveTab] = useState(initialTab);
    const [settings, setSettings] = useState(loadSettings);
    const [saved, setSaved] = useState(false);
    const [error, setError] = useState('');
    const [billingLoading, setBillingLoading] = useState(false);
    const [cancelDialogOpen, setCancelDialogOpen] = useState(false);

    const tier = getUserTier(user);
    const { used, limit } = getRemainingQuota(user, user?.uploads_count || 0);

    const handleCheckout = async () => {
        setBillingLoading(true);
        setError('');
        try {
            const data = await fetchWithAuth('/api/v1/billing/create-checkout-session', {
                method: 'POST',
            });
            
            if (data?.url) {
                window.location.href = data.url;
            } else {
                throw new Error('No checkout URL returned');
            }
        } catch (err) {
            setError(err.message || 'Error processing billing request');
        } finally {
            setBillingLoading(false);
        }
    };

    const handleCustomerPortal = async () => {
        setBillingLoading(true);
        setError('');
        try {
            const data = await fetchWithAuth('/api/v1/billing/customer-portal', {
                method: 'POST',
            });
            
            if (data?.url) {
                window.location.href = data.url;
            } else {
                throw new Error('No portal URL returned');
            }
        } catch (err) {
            setError(err.message || 'Error accessing customer portal');
        } finally {
            setBillingLoading(false);
        }
    };

    const handleCancelSubscriptionClick = () => {
        setCancelDialogOpen(true);
    };

    const confirmCancelSubscription = async () => {
        setCancelDialogOpen(false);
        setBillingLoading(true);
        setError('');
        try {
            await fetchWithAuth('/api/v1/billing/cancel-subscription', {
                method: 'POST',
            });
            
            addToast('Your subscription has been cancelled successfully.', 'success');
            // Ideally trigger user refresh here
        } catch (err) {
            setError(err.message || 'Error cancelling subscription');
        } finally {
            setBillingLoading(false);
        }
    };

    const update = (key, value) => {
        setSettings((prev) => ({ ...prev, [key]: value }));
        setSaved(false);
    };

    const handleSave = useCallback(() => {
        try {
            // Validate settings with Zod
            SettingsSchema.parse(settings);

            localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
            setSaved(true);
            setError('');
            setTimeout(() => setSaved(false), 3000);
        } catch (err) {
            if (err instanceof z.ZodError) {
                setError(err.errors[0].message);
            } else {
                setError(err.message || 'Failed to save settings');
            }
            setSaved(false);
            setTimeout(() => setError(''), 3000);
        }
    }, [settings]);

    const handleReset = () => {
        const resetState = { ...defaultSettings, darkMode: theme === 'dark' };
        setSettings(resetState);
        localStorage.removeItem(SETTINGS_KEY);
        setSaved(false);
    };

    useEffect(() => {
        setSettings((prev) => ({ ...prev, darkMode: theme === 'dark' }));
    }, [theme]);

    useEffect(() => {
        const handleKeyDown = (e) => {
            if ((e.ctrlKey || e.metaKey) && (e.key.toLowerCase() === 's' || e.key === 'Enter')) {
                e.preventDefault();
                handleSave();
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [handleSave]);

    const Toggle = ({ checked, onChange }) => (
        <button
            role="switch"
            aria-checked={checked}
            onClick={() => onChange(!checked)}
            className={`relative inline-flex h-7 w-12 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 ${checked ? 'bg-primary' : 'bg-slate-200 dark:bg-slate-600'}`}
        >
            <span className={`pointer-events-none inline-block h-6 w-6 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${checked ? 'translate-x-5' : 'translate-x-0'}`} />
        </button>
    );

    return (
        <div className="min-h-screen bg-background-light dark:bg-background-dark animate-in fade-in duration-500 flex flex-col">
            <main className="max-w-3xl mx-auto px-4 py-8">
                <div className="mb-8">
                    <h1 className="text-3xl font-bold text-slate-900 dark:text-white flex items-center gap-3">
                        <span className="material-symbols-outlined text-primary text-4xl">settings</span>
                        Settings
                    </h1>
                    <p className="text-slate-600 dark:text-slate-400 mt-2">Configure your preferences and manage your plan.</p>
                </div>

                {/* Tabs */}
                <div 
                    role="tablist"
                    aria-label="Settings sections" 
                    className="flex border-b border-slate-200 dark:border-slate-800 mb-8"
                >
                    <button
                        role="tab"
                        aria-selected={activeTab === 'general'}
                        aria-controls="general-panel"
                        id="tab-general"
                        onClick={() => setActiveTab('general')}
                        className={`pb-4 px-4 text-sm font-medium transition-colors border-b-2 focus:outline-none focus:text-primary ${activeTab === 'general' ? 'border-primary text-primary' : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-300'}`}
                    >
                        General
                    </button>
                    <button
                        role="tab"
                        aria-selected={activeTab === 'billing'}
                        aria-controls="billing-panel"
                        id="tab-billing"
                        onClick={() => setActiveTab('billing')}
                        className={`pb-4 px-4 text-sm font-medium transition-colors border-b-2 focus:outline-none focus:text-primary ${activeTab === 'billing' ? 'border-primary text-primary' : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-300'}`}
                    >
                        Billing & Plan
                    </button>
                </div>

                {activeTab === 'general' ? (
                <div id="general-panel" role="tabpanel" aria-labelledby="tab-general">
                {/* Upload Preferences */}
                <section className="bg-glass-surface backdrop-blur-xl border border-glass-border  shadow-xl shadow-primary/5 mb-6">
                    <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                        <span className="material-symbols-outlined text-primary">upload_file</span>
                        Upload Preferences
                    </h2>
                    <div className="space-y-4">
                        {[
                            { label: 'Default Template', key: 'defaultTemplate', options: ['IEEE', 'Springer', 'APA', 'Nature', 'Vancouver', 'none'] },
                            { label: 'Default Page Size', key: 'defaultPageSize', options: ['Letter', 'A4', 'Legal'] },
                            { label: 'Default Export Format', key: 'defaultExportFormat', options: ['docx', 'pdf'] },
                        ].map(({ label, key, options }) => (
                            <div key={key}>
                                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">{label}</label>
                                <select value={settings[key]} onChange={(e) => update(key, e.target.value)}
                                    className="w-full p-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-primary outline-none transition-colors">
                                    {options.map(o => <option key={o} value={o}>{o === 'none' ? 'None (Auto-detect)' : o}</option>)}
                                </select>
                            </div>
                        ))}

                        <div className="flex items-center justify-between p-3 rounded-lg border border-glass-border bg-white/5 dark:bg-white/5">
                            <div className="flex flex-col">
                                <div className="flex items-center gap-2">
                                    <span className="material-symbols-outlined text-amber-500">bolt</span>
                                    <span className="text-sm font-bold text-slate-900 dark:text-white">Fast Mode Default</span>
                                </div>
                                <span className="text-[10px] text-slate-500 pl-8">Skip AI reasoning for faster processing</span>
                            </div>
                            <Toggle checked={settings.defaultFastMode} onChange={(v) => update('defaultFastMode', v)} />
                        </div>
                    </div>
                </section>

                {/* Account Settings */}
                <section className="bg-glass-surface backdrop-blur-xl border border-glass-border  shadow-xl shadow-primary/5 mb-6">
                    <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                        <span className="material-symbols-outlined text-primary">person</span>
                        Account
                    </h2>
                    <div className="flex items-center justify-between p-3 rounded-lg border border-glass-border bg-white/5 dark:bg-white/5">
                        <div className="flex items-center gap-2">
                            <span className="material-symbols-outlined text-slate-500">email</span>
                            <span className="text-sm font-bold text-slate-900 dark:text-white">Email Notifications</span>
                        </div>
                        <Toggle checked={settings.emailNotifications} onChange={(v) => update('emailNotifications', v)} />
                    </div>
                    <div className="flex items-center justify-between p-3 rounded-lg border border-glass-border bg-white/5 dark:bg-white/5 mt-3">
                        <div className="flex items-center gap-2">
                            <span className="material-symbols-outlined text-slate-500">dark_mode</span>
                            <span className="text-sm font-bold text-slate-900 dark:text-white">Dark Mode</span>
                        </div>
                        <Toggle
                            checked={settings.darkMode}
                            onChange={(v) => {
                                update('darkMode', v);
                                setTheme(v ? 'dark' : 'light');
                            }}
                        />
                    </div>
                </section>

                {/* API Key (Future) */}
                <section className="bg-glass-surface backdrop-blur-xl border border-glass-border  shadow-xl shadow-primary/5 mb-6 opacity-60 pointer-events-none select-none">
                    <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-2 flex items-center gap-2">
                        <span className="material-symbols-outlined text-primary">key</span>
                        API Key Management
                        <span className="text-xs px-2 py-0.5 bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-400 rounded-full">Coming Soon</span>
                    </h2>
                    <p className="text-sm text-slate-500 dark:text-slate-400">Generate and manage API keys for programmatic access to ScholarForm AI.</p>
                </section>

                {/* Feedback Banners */}
                {saved && (
                    <div className="mb-6 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4 flex items-center text-green-700 dark:text-green-400 animate-in fade-in slide-in-from-bottom-2 duration-300">
                        <span className="material-symbols-outlined mr-2">check_circle</span>
                        <span className="font-medium text-sm">Settings saved ✓</span>
                    </div>
                )}
                {error && (
                    <div className="mb-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 flex items-center text-red-700 dark:text-red-400 animate-in fade-in slide-in-from-bottom-2 duration-300">
                        <span className="material-symbols-outlined mr-2">error</span>
                        <span className="font-medium text-sm">{error}</span>
                    </div>
                )}

                <div className="flex items-center justify-between">
                    <button onClick={handleReset}
                        className="px-4 py-2 text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors active:scale-95">
                        Reset to Defaults
                    </button>
                    <button onClick={handleSave}
                        disabled={saved}
                        title="Save Changes (Ctrl+S or Ctrl+Enter)"
                        className="px-6 py-3 bg-primary hover:bg-primary-hover text-white font-bold rounded-xl shadow-lg shadow-primary/25 transition-all flex items-center gap-2 active:scale-95 disabled:opacity-50">
                        <span className="material-symbols-outlined">save</span>
                        Save Settings
                    </button>
                </div>
                </div>
                ) : (
                <div id="billing-panel" role="tabpanel" aria-labelledby="tab-billing" className="space-y-6 animate-in fade-in duration-300">
                    <section className="bg-glass-surface backdrop-blur-xl border border-glass-border shadow-xl shadow-primary/5 p-6 rounded-xl">
                        <div className="flex items-center justify-between mb-6">
                            <div>
                                <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-1">Your Plan</h2>
                                <p className="text-slate-500 dark:text-slate-400 text-sm">Manage your subscription and billing details.</p>
                            </div>
                            <span className={`px-3 py-1 text-sm font-semibold rounded-full ${tier === 'pro' ? 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300' : 'bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300'}`}>
                                {tier === 'pro' ? 'Pro Plan' : 'Free Plan'}
                            </span>
                        </div>

                        <div className="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-4 border border-slate-200 dark:border-slate-800 mb-6">
                            <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200 mb-2">Usage Highlights</h3>
                            <div className="flex justify-between items-center text-sm">
                                <span className="text-slate-600 dark:text-slate-400">Uploads Status</span>
                                <span className="font-medium text-slate-900 dark:text-white">
                                    {limit === Infinity ? 'Unlimited' : `${used || 0} of ${limit} used today`}
                                </span>
                            </div>
                            {limit !== Infinity && (
                                <div className="w-full bg-slate-200 dark:bg-slate-800 rounded-full h-1.5 mt-3">
                                    <div className="bg-primary h-1.5 rounded-full" style={{ width: `${Math.min(((used || 0) / limit) * 100, 100)}%` }}></div>
                                </div>
                            )}
                        </div>

                        {tier === 'free' ? (
                            <div className="flex flex-col gap-3">
                                <button 
                                    onClick={handleCheckout} 
                                    disabled={billingLoading}
                                    className="w-full py-3 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white font-bold rounded-xl shadow-md transition-all disabled:opacity-70 flex justify-center items-center"
                                >
                                    {billingLoading ? <span className="material-symbols-outlined animate-spin mr-2">progress_activity</span> : null}
                                    Upgrade to Pro
                                </button>
                                <p className="text-xs text-center text-slate-500">You will be redirected to Stripe for secure checkout.</p>
                            </div>
                        ) : (
                            <div className="flex flex-col sm:flex-row gap-3">
                                <button 
                                    onClick={handleCustomerPortal} 
                                    disabled={billingLoading}
                                    className="flex-1 py-3 bg-primary hover:bg-blue-700 text-white font-bold rounded-xl shadow-md transition-all disabled:opacity-70 flex justify-center items-center"
                                >
                                    {billingLoading ? <span className="material-symbols-outlined animate-spin mr-2">progress_activity</span> : null}
                                    Manage Subscription
                                </button>
                                <button 
                                    onClick={handleCancelSubscriptionClick} 
                                    disabled={billingLoading}
                                    className="flex-1 py-3 bg-red-50 hover:bg-red-100 text-red-600 dark:bg-red-900/20 dark:hover:bg-red-900/40 dark:text-red-400 font-bold rounded-xl border border-red-200 dark:border-red-800 transition-all disabled:opacity-70 flex justify-center items-center"
                                >
                                    Cancel Subscription
                                </button>
                            </div>
                        )}
                    </section>
                </div>
                )}
                <ConfirmDialog 
                    isOpen={cancelDialogOpen}
                    title="Cancel Subscription"
                    message="Are you sure you want to cancel your Pro subscription? You will lose access to Pro features at the end of your billing cycle."
                    confirmLabel="Yes, Cancel Subscription"
                    cancelLabel="No, Keep Pro"
                    onConfirm={confirmCancelSubscription}
                    onCancel={() => setCancelDialogOpen(false)}
                    isDestructive={true}
                />
            </main>
            <Footer />
        </div>
    );
}
