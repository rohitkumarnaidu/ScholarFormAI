// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/src/context/AuthContext';
import { useRouter } from 'next/navigation';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

const PROVIDERS = [
    { id: 'openai', name: 'OpenAI', color: 'bg-green-500' },
    { id: 'anthropic', name: 'Anthropic', color: 'bg-orange-500' },
    { id: 'deepseek', name: 'DeepSeek', color: 'bg-blue-500' },
    { id: 'groq', name: 'Groq', color: 'bg-yellow-500' },
    { id: 'google', name: 'Google AI', color: 'bg-red-500' },
    { id: 'cohere', name: 'Cohere', color: 'bg-purple-500' },
    { id: 'mistral', name: 'Mistral', color: 'bg-indigo-500' },
];

export default function ApiKeysPage() {
    const { user, isLoggedIn, loading } = useAuth();
    const router = useRouter();
    const [keys, setKeys] = useState([]);
    const [, setProviders] = useState({});
    const [showForm, setShowForm] = useState(false);
    const [newKey, setNewKey] = useState({ provider: 'openai', api_key: '', key_label: '' });
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [testing, setTesting] = useState(null);
    const [testResult, setTestResult] = useState(null);

    useEffect(() => {
        if (!loading && !isLoggedIn) {
            router.push('/login?next=/api-keys');
        }
    }, [loading, isLoggedIn, router]);

    useEffect(() => {
        if (isLoggedIn) {
            fetchKeys();
            fetchProviders();
        }
    }, [isLoggedIn, fetchKeys]);

    const fetchKeys = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE}/api/v1/keys`, {
                headers: { Authorization: `Bearer ${user?.access_token || ''}` },
            });
            if (res.ok) setKeys(await res.json());
        } catch (e) {
            setError('Failed to load API keys');
        }
    }, [user?.access_token]);

    const fetchProviders = async () => {
        try {
            const res = await fetch(`${API_BASE}/api/v1/keys/providers`);
            if (res.ok) setProviders(await res.json());
        } catch (e) { /* ignore */ }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');

        if (!newKey.api_key.trim()) {
            setError('API key is required');
            return;
        }

        try {
            const res = await fetch(`${API_BASE}/api/v1/keys`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${user?.access_token || ''}`,
                },
                body: JSON.stringify(newKey),
            });

            if (res.ok) {
                setSuccess('API key added successfully');
                setShowForm(false);
                setNewKey({ provider: 'openai', api_key: '', key_label: '' });
                fetchKeys();
            } else {
                const data = await res.json();
                setError(data.detail || 'Failed to add API key');
            }
        } catch (e) {
            setError('Failed to add API key');
        }
    };

    const handleDelete = async (keyId) => {
        if (!confirm('Delete this API key? This cannot be undone.')) return;
        try {
            const res = await fetch(`${API_BASE}/api/v1/keys/${keyId}`, {
                method: 'DELETE',
                headers: { Authorization: `Bearer ${user?.access_token || ''}` },
            });
            if (res.ok) fetchKeys();
        } catch (e) {
            setError('Failed to delete API key');
        }
    };

    const handleTest = async (provider, apiKey) => {
        setTesting(provider);
        setTestResult(null);
        try {
            const res = await fetch(`${API_BASE}/api/v1/keys/test`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${user?.access_token || ''}`,
                },
                body: JSON.stringify({ provider, api_key: apiKey }),
            });
            if (res.ok) setTestResult(await res.json());
        } catch (e) {
            setTestResult({ status: 'error', message: 'Connection failed' });
        }
        setTesting(null);
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="animate-spin h-8 w-8 border-4 border-indigo-500 border-t-transparent rounded-full" />
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8 px-4">
            <div className="max-w-4xl mx-auto">
                <div className="flex items-center justify-between mb-8">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">API Keys</h1>
                        <p className="text-gray-600 dark:text-gray-400 mt-1">
                            Manage your LLM provider API keys for faster, unlimited access.
                        </p>
                    </div>
                    <button
                        onClick={() => setShowForm(!showForm)}
                        className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition"
                    >
                        {showForm ? 'Cancel' : '+ Add Key'}
                    </button>
                </div>

                {error && (
                    <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300">
                        {error}
                    </div>
                )}
                {success && (
                    <div className="mb-4 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg text-green-700 dark:text-green-300">
                        {success}
                    </div>
                )}

                {showForm && (
                    <form onSubmit={handleSubmit} className="mb-8 p-6 bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
                        <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">Add New API Key</h2>

                        <div className="mb-4">
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Provider</label>
                            <select
                                value={newKey.provider}
                                onChange={(e) => setNewKey({ ...newKey, provider: e.target.value })}
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                            >
                                {PROVIDERS.map((p) => (
                                    <option key={p.id} value={p.id}>{p.name}</option>
                                ))}
                            </select>
                        </div>

                        <div className="mb-4">
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Label (optional)</label>
                            <input
                                type="text"
                                value={newKey.key_label}
                                onChange={(e) => setNewKey({ ...newKey, key_label: e.target.value })}
                                placeholder="My OpenAI Key"
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                            />
                        </div>

                        <div className="mb-4">
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">API Key</label>
                            <input
                                type="password"
                                value={newKey.api_key}
                                onChange={(e) => setNewKey({ ...newKey, api_key: e.target.value })}
                                placeholder="sk-..."
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono"
                            />
                        </div>

                        <div className="flex gap-3">
                            <button type="submit" className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition">
                                Save Key
                            </button>
                            <button
                                type="button"
                                onClick={() => handleTest(newKey.provider, newKey.api_key)}
                                disabled={testing || !newKey.api_key}
                                className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition disabled:opacity-50"
                            >
                                {testing ? 'Testing...' : 'Test Connection'}
                            </button>
                        </div>

                        {testResult && (
                            <div className={`mt-4 p-3 rounded-lg ${testResult.status === 'valid' ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300' : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300'}`}>
                                <strong>{testResult.status === 'valid' ? '✅ Connected' : '❌ Failed'}</strong>
                                <span className="ml-2 text-sm">{testResult.message}</span>
                                <span className="ml-2 text-xs text-gray-500">({testResult.response_time_ms}ms)</span>
                            </div>
                        )}
                    </form>
                )}

                <div className="space-y-4">
                    {keys.length === 0 ? (
                        <div className="p-8 text-center bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
                            <p className="text-gray-500 dark:text-gray-400">No API keys configured yet.</p>
                            <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">Add your provider keys to unlock faster processing and higher rate limits.</p>
                        </div>
                    ) : (
                        keys.map((key) => (
                            <div key={key.id} className="p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                        <div className={`w-3 h-3 rounded-full ${PROVIDERS.find((p) => p.id === key.provider)?.color || 'bg-gray-500'}`} />
                                        <div>
                                            <p className="font-medium text-gray-900 dark:text-white">{key.key_label || key.provider}</p>
                                            <p className="text-sm text-gray-500 dark:text-gray-400 font-mono">{key.key_preview}</p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-4">
                                        <div className="text-right">
                                            <p className="text-sm text-gray-500 dark:text-gray-400">{key.total_requests.toLocaleString()} requests</p>
                                            <p className="text-xs text-gray-400 dark:text-gray-500">{key.rate_limit_per_minute}/min · {key.daily_quota.toLocaleString()}/day</p>
                                        </div>
                                        <span className={`px-2 py-1 text-xs rounded-full ${key.is_active ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300' : 'bg-gray-100 dark:bg-gray-700 text-gray-500'}`}>
                                            {key.is_active ? 'Active' : 'Inactive'}
                                        </span>
                                        <button
                                            onClick={() => handleDelete(key.id)}
                                            className="p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition"
                                            title="Delete key"
                                        >
                                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                            </svg>
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>

                <div className="mt-8 p-6 bg-blue-50 dark:bg-blue-900/20 rounded-xl border border-blue-200 dark:border-blue-800">
                    <h3 className="font-semibold text-blue-900 dark:text-blue-200 mb-2">Supported Providers</h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        {PROVIDERS.map((p) => (
                            <div key={p.id} className="flex items-center gap-2">
                                <div className={`w-2 h-2 rounded-full ${p.color}`} />
                                <span className="text-sm text-blue-800 dark:text-blue-300">{p.name}</span>
                            </div>
                        ))}
                    </div>
                    <p className="text-xs text-blue-600 dark:text-blue-400 mt-3">
                        Your keys are encrypted and stored securely. We never expose full key values.
                    </p>
                </div>
            </div>
        </div>
    );
}
