'use client';
import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/src/context/AuthContext';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { useConfirm } from '@/src/components/ConfirmDialog';
import { useDebounce } from '@/src/hooks/useDebounce';
import { fetchWithRetry } from '@/src/utils/fetchWithRetry';
import ErrorBoundary from '@/src/components/ErrorBoundary';
import { Key, Lock, Trash2 } from 'lucide-react';
import DynamicIcon from '@/src/components/ui/DynamicIcon';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

const PROVIDERS = [
    { id: 'openai', name: 'OpenAI', icon: 'psychiatry', color: 'bg-emerald-500' },
    { id: 'anthropic', name: 'Anthropic', icon: 'psychology', color: 'bg-orange-500' },
    { id: 'deepseek', name: 'DeepSeek', icon: 'neurology', color: 'bg-blue-500' },
    { id: 'groq', name: 'Groq', icon: 'bolt', color: 'bg-yellow-500' },
    { id: 'google', name: 'Google AI', icon: 'google', color: 'bg-red-500' },
    { id: 'cohere', name: 'Cohere', icon: 'cohere', color: 'bg-purple-500' },
    { id: 'mistral', name: 'Mistral', icon: 'air', color: 'bg-indigo-500' },
    { id: 'openrouter', name: 'OpenRouter', icon: 'alt_route', color: 'bg-cyan-500' },
    { id: 'nvidia', name: 'NVIDIA NIM', icon: 'speed', color: 'bg-lime-500' },
    { id: 'ollama', name: 'Ollama', icon: 'dns', color: 'bg-slate-500' },
];

function ApiKeysPageInner() {
    const { user, isLoggedIn, loading } = useAuth();
    const router = useRouter();
    
    const confirm = useConfirm();
    const [keys, setKeys] = useState([]);
    const [showForm, setShowForm] = useState(false);
    const [newKey, setNewKey] = useState({ provider: 'openai', api_key: '', key_label: '' });
    const [searchTerm, setSearchTerm] = useState('');
    const [testing, setTesting] = useState(null);
    const [testResult, setTestResult] = useState(null);
    const debouncedSearch = useDebounce(searchTerm, 250);

    useEffect(() => {
        if (!loading && !isLoggedIn) router.push('/login?next=/api-keys');
    }, [loading, isLoggedIn, router]);

    const fetchKeys = useCallback(async () => {
        try {
            const res = await fetchWithRetry(`${API_BASE}/api/v1/keys`, {
                headers: { Authorization: `Bearer ${user?.access_token || ''}` },
            });
            if (res.ok) setKeys(await res.json());
        } catch (e) {
            toast.error('Failed to load API keys — check your connection');
        }
    }, [user?.access_token]);

    useEffect(() => {
        if (isLoggedIn) fetchKeys();
    }, [isLoggedIn, fetchKeys]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        const apiKey = newKey.api_key.trim();
        if (!apiKey) { toast.error('API key is required'); return; }
        if (apiKey.length < 8) { toast.error('API key seems too short — must be at least 8 characters'); return; }
        try {
            const res = await fetchWithRetry(`${API_BASE}/api/v1/keys`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${user?.access_token || ''}` },
                body: JSON.stringify(newKey),
            });
            if (res.ok) {
                toast.success('API key added successfully');
                setShowForm(false);
                setNewKey({ provider: 'openai', api_key: '', key_label: '' });
                setTestResult(null);
                fetchKeys();
            } else {
                const data = await res.json().catch(() => ({}));
                toast.error(data.detail || 'Failed to add API key');
            }
        } catch (e) { toast.error('Failed to add API key — network error'); }
    };

    const handleDelete = async (keyId, label) => {
        const confirmed = await confirm('This cannot be undone. All usage tracking for this key will stop.', `Delete "${label}"?`, 'Delete', 'danger');
        if (!confirmed) return;
        try {
            const res = await fetchWithRetry(`${API_BASE}/api/v1/keys/${keyId}`, {
                method: 'DELETE',
                headers: { Authorization: `Bearer ${user?.access_token || ''}` },
            });
            if (res.ok) { fetchKeys(); toast.success('API key deleted'); }
            else { toast.error('Failed to delete API key'); }
        } catch (e) { toast.error('Failed to delete — network error'); }
    };

    const handleTest = async (provider, apiKey) => {
        if (!apiKey) { toast.error('Enter an API key first'); return; }
        setTesting(provider);
        setTestResult(null);
        try {
            const res = await fetchWithRetry(`${API_BASE}/api/v1/keys/test`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${user?.access_token || ''}` },
                body: JSON.stringify({ provider, api_key: apiKey }),
            }, 2);
            const data = res.ok ? await res.json() : null;
            if (res.status === 429) toast.info('Rate limited — retrying with backoff');
            setTestResult(data || { status: 'error', message: `HTTP ${res.status}` });
        } catch (e) {
            setTestResult({ status: 'error', message: 'Connection failed — server unreachable' });
        }
        setTesting(null);
    };

    const filteredKeys = keys.filter(k =>
        k.provider.toLowerCase().includes(debouncedSearch.toLowerCase()) ||
        (k.key_label || '').toLowerCase().includes(debouncedSearch.toLowerCase())
    );

    const providerMeta = (id) => PROVIDERS.find(p => p.id === id) || { name: id, icon: 'key', color: 'bg-slate-500' };

    if (loading) return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-900 py-8">
            <div className="max-w-4xl mx-auto px-4">
                <div className="mb-8"><div className="h-9 w-32 bg-slate-200 dark:bg-slate-700 rounded animate-pulse mb-2" /><div className="h-5 w-64 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" /></div>
                <div className="space-y-4">
                    {[1,2,3].map(i => (
                        <div key={i} className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
                            <div className="flex items-center gap-3"><div className="w-10 h-10 rounded-lg bg-slate-200 dark:bg-slate-700 animate-pulse" /><div className="flex-1"><div className="h-5 w-32 bg-slate-200 dark:bg-slate-700 rounded animate-pulse mb-1" /><div className="h-4 w-48 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" /></div></div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-900 py-8">
            <div className="max-w-4xl mx-auto px-4">
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-8 gap-4">
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900 dark:text-white">API Keys</h1>
                        <p className="text-slate-600 dark:text-slate-400 mt-1">
                            Manage your LLM provider API keys. Keys are encrypted at rest.
                        </p>
                    </div>
                    <div className="flex gap-3">
                        <a href="/providers" className="px-4 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition text-sm font-medium">
                            Provider Dashboard
                        </a>
                        <button onClick={() => { setShowForm(!showForm); setTestResult(null); }}
                            className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition text-sm font-medium">
                            {showForm ? 'Cancel' : '+ Add Key'}
                        </button>
                    </div>
                </div>

                {keys.length > 0 && (
                    <div className="mb-6">
                        <input type="text" value={searchTerm} onChange={e => setSearchTerm(e.target.value)}
                            placeholder="Search by provider or label..."
                            className="w-full max-w-md px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500" />
                    </div>
                )}

                {showForm && (
                    <form onSubmit={handleSubmit} className="mb-8 p-6 bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700">
                        <h2 className="text-xl font-semibold mb-4 text-slate-900 dark:text-white">Add New API Key</h2>
                        <div className="grid grid-cols-1 md:grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Provider</label>
                                <select value={newKey.provider} onChange={e => setNewKey({ ...newKey, provider: e.target.value })}
                                    className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white">
                                    {PROVIDERS.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Label (optional)</label>
                                <input type="text" value={newKey.key_label} onChange={e => setNewKey({ ...newKey, key_label: e.target.value })}
                                    placeholder="My OpenAI Key"
                                    className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white" />
                            </div>
                        </div>
                        <div className="mb-4">
                            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">API Key</label>
                            <input type="password" value={newKey.api_key} onChange={e => setNewKey({ ...newKey, api_key: e.target.value })}
                                placeholder="sk-..."
                                className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white font-mono text-sm" />
                        </div>
                        <div className="flex gap-3 flex-wrap">
                            <button type="submit" className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition text-sm font-medium">Save Key</button>
                            <button type="button" onClick={() => handleTest(newKey.provider, newKey.api_key)}
                                disabled={testing || !newKey.api_key}
                                className="px-4 py-2 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-600 transition text-sm font-medium disabled:opacity-50">
                                {testing === newKey.provider ? 'Testing...' : 'Test Connection'}
                            </button>
                        </div>
                        {testResult && (
                            <div className={`mt-4 p-3 rounded-lg text-sm flex items-start gap-3 ${testResult.status === 'valid' ? 'bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300' : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300'}`}>
                                <span className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${testResult.status === 'valid' ? 'bg-emerald-500' : 'bg-red-500'}`} />
                                <div>
                                    <span className="font-medium">{testResult.status === 'valid' ? 'Connected' : testResult.status === 'error' ? 'Error' : 'Failed'}</span>
                                    <span className="text-slate-400 ml-2 text-xs">({testResult.response_time_ms}ms)</span>
                                    {testResult.message && <p className="mt-0.5 text-slate-500 dark:text-slate-400">{testResult.message}</p>}
                                </div>
                            </div>
                        )}
                    </form>
                )}

                <div className="space-y-3">
                    {filteredKeys.length === 0 ? (
                        <div className="p-12 text-center bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700">
                            <Key className="text-5xl text-slate-300 dark:text-slate-600 mb-4" />
                            <p className="text-slate-500 dark:text-slate-400">
                                {keys.length === 0 ? 'No API keys configured yet.' : 'No keys match your search.'}
                            </p>
                            {keys.length === 0 && (
                                <button onClick={() => setShowForm(true)} className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition text-sm font-medium">
                                    + Add Your First Key
                                </button>
                            )}
                        </div>
                    ) : filteredKeys.map(k => {
                        const meta = providerMeta(k.provider);
                        return (
                            <div key={k.id} className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 hover:shadow-sm transition-shadow">
                                <div className="flex items-start justify-between gap-4">
                                    <div className="flex items-center gap-3 min-w-0">
                                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-white text-lg shrink-0 ${meta.color}`}>
                                            <DynamicIcon name={meta.icon} className="w-5.5 h-5.5" />
                                        </div>
                                        <div className="min-w-0">
                                            <h3 className="font-semibold text-slate-900 dark:text-white truncate">{k.key_label || meta.name}</h3>
                                            <div className="flex items-center gap-2 mt-0.5">
                                                <span className="text-xs text-slate-500 dark:text-slate-400 font-mono">{k.key_preview}</span>
                                                <span className="text-[10px] text-slate-400">·</span>
                                                <span className="text-xs text-slate-500">{meta.name}</span>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-3 shrink-0">
                                        {k.total_requests > 0 && (
                                            <span className="text-[11px] text-slate-400 whitespace-nowrap">{k.total_requests.toLocaleString()} req</span>
                                        )}
                                        <span className={`px-2 py-0.5 text-[10px] font-medium rounded-full ${k.is_active ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300' : 'bg-slate-100 dark:bg-slate-700 text-slate-500'}`}>
                                            {k.is_active ? 'Active' : 'Inactive'}
                                        </span>
                                        <span className="text-[10px] text-slate-400 hidden sm:inline">{k.rate_limit_per_minute}/min</span>
                                        <button onClick={() => handleDelete(k.id, k.key_label || meta.name)}
                                            className="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition" title="Delete key">
                                            <Trash2 className="text-[18px]" />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>

                <div className="mt-8 p-6 bg-gradient-to-r from-indigo-50 to-blue-50 dark:from-indigo-900/20 dark:to-blue-900/20 rounded-xl border border-indigo-200 dark:border-indigo-800">
                    <div className="flex items-start gap-4">
                        <div className="w-12 h-12 rounded-xl bg-indigo-100 dark:bg-indigo-500/20 flex items-center justify-center shrink-0">
                            <Lock className="text-2xl text-indigo-600 dark:text-indigo-400" />
                        </div>
                        <div>
                            <h3 className="font-semibold text-lg text-slate-900 dark:text-white mb-1">Enterprise-Grade Security</h3>
                            <p className="text-sm text-slate-600 dark:text-slate-400 mb-3">
                                Your API keys are encrypted using <strong>AES-256-GCM</strong> before storage. We never log, expose, or share full key values. Rate limits and usage quotas are enforced per key.
                            </p>
                            <div className="flex flex-wrap gap-4 text-xs text-slate-500 dark:text-slate-400">
                                {PROVIDERS.map(p => (
                                    <span key={p.id} className="flex items-center gap-1">
                                        <span className={`w-1.5 h-1.5 rounded-full ${p.color}`} />
                                        {p.name}
                                    </span>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default function ApiKeysPage() {
    return <ErrorBoundary><ApiKeysPageInner /></ErrorBoundary>;
}
