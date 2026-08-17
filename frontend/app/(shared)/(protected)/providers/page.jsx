'use client';
import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '@/src/context/AuthContext';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { useConfirm } from '@/src/components/ConfirmDialog';
import { useDebounce } from '@/src/hooks/useDebounce';
import { fetchWithRetry } from '@/src/utils/fetchWithRetry';
import ErrorBoundary from '@/src/components/ErrorBoundary';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

const PROVIDER_ICONS = {
    openai: 'psychiatry',
    anthropic: 'psychology',
    groq: 'bolt',
    deepseek: 'neurology',
    openrouter: 'alt_route',
    google: 'google',
    cohere: 'cohere',
    mistral: 'air',
    ollama: 'dns',
    nvidia: 'speed',
};

function isValidUrl(str) {
    try {
        const url = new URL(str);
        return url.protocol === 'http:' || url.protocol === 'https:';
    } catch { return false; }
}

function sanitizeUrl(str) {
    let s = str.trim();
    if (!/^https?:\/\//i.test(s)) s = 'https://' + s;
    try { return new URL(s).toString().replace(/\/+$/, ''); } catch { return str.trim(); }
}

function ProvidersPageInner() {
    const { user, isLoggedIn, loading } = useAuth();
    const router = useRouter();
    
    const confirm = useConfirm();
    const formRef = useRef(null);
    const [dirty, setDirty] = useState(false);
    const [providers, setProviders] = useState([]);
    const [customProviders, setCustomProviders] = useState([]);
    const [showAddForm, setShowAddForm] = useState(false);
    const [testingId, setTestingId] = useState(null);
    const [testResults, setTestResults] = useState({});
    const [searchTerm, setSearchTerm] = useState('');
    const [editingProvider, setEditingProvider] = useState(null);
    const [form, setForm] = useState({ name: '', base_url: '', api_key: '', models: '', is_local: false, description: '' });
    const [keyFormProvider, setKeyFormProvider] = useState(null);
    const [keyFormValue, setKeyFormValue] = useState('');
    const [keyFormTesting, setKeyFormTesting] = useState(false);
    const [discovering, setDiscovering] = useState(null);
    const [discoveredModels, setDiscoveredModels] = useState({});
    const [providersLoading, setProvidersLoading] = useState(false);
    const [providersError, setProvidersError] = useState(null);
    const debouncedSearch = useDebounce(searchTerm, 250);

    const handleDiscoverModels = useCallback(async (providerId, baseUrl) => {
        if (discovering === providerId) return;
        setDiscovering(providerId);
        try {
            const params = new URLSearchParams();
            if (baseUrl) params.set('base_url', baseUrl);
            const url = `${API_BASE}/api/v1/providers/${providerId}/models${params.toString() ? '?' + params.toString() : ''}`;
            const res = await fetchWithRetry(url, {
                headers: { Authorization: `Bearer ${user?.access_token || ''}` },
            });
            if (res.ok) {
                const data = await res.json();
                setDiscoveredModels(prev => ({ ...prev, [providerId]: data.models || [] }));
                if (data.models?.length > 0) toast.success(`Found ${data.models.length} models for ${providerId}`);
                else toast.info('No models discovered');
            } else {
                toast.error('Failed to discover models');
            }
        } catch (e) {
            toast.error('Failed to discover models — network error');
        }
        setDiscovering(null);
    }, [user, discovering]);

    useEffect(() => {
        if (!loading && !isLoggedIn) router.push('/login?next=/providers');
    }, [loading, isLoggedIn, router]);

    const loadProviders = useCallback(async () => {
        setProvidersLoading(true);
        setProvidersError(null);
        try {
            const [builtinRes, customRes] = await Promise.all([
                fetchWithRetry(`${API_BASE}/api/v1/providers`, {
                    headers: { Authorization: `Bearer ${user?.access_token || ''}` },
                }),
                fetchWithRetry(`${API_BASE}/api/v1/providers/custom`, {
                    headers: { Authorization: `Bearer ${user?.access_token || ''}` },
                }),
            ]);
            if (builtinRes.ok) {
                const data = await builtinRes.json();
                setProviders(data.providers || []);
            } else {
                setProvidersError(`Failed to load providers (HTTP ${builtinRes.status})`);
            }
            if (customRes.ok) {
                const data = await customRes.json();
                setCustomProviders(data);
            }
        } catch (e) {
            setProvidersError('Failed to load providers — check your connection');
            toast.error('Failed to load providers — check your connection');
        }
        setProvidersLoading(false);
    }, [user]);

    useEffect(() => {
        if (isLoggedIn) loadProviders();
    }, [isLoggedIn, loadProviders]);

    useEffect(() => {
        if (!isLoggedIn) return;
        let mounted = true;
        function onFocus() { if (mounted) loadProviders(); }
        window.addEventListener('focus', onFocus);
        return () => { mounted = false; window.removeEventListener('focus', onFocus); };
    }, [isLoggedIn, loadProviders]);

    useEffect(() => {
        if (!showAddForm) return;
        function onKeyDown(e) {
            if (e.key === 'Escape') {
                if (dirty) {
                    confirm('Discard unsaved changes?', 'Unsaved Changes', 'Discard', 'warning').then(ok => { if (ok) resetForm(); });
                } else {
                    resetForm();
                }
            }
        }
        document.addEventListener('keydown', onKeyDown);
        return () => document.removeEventListener('keydown', onKeyDown);
    }, [showAddForm, dirty, confirm]);

    const handleTest = useCallback(async (providerId, baseUrl, apiKey) => {
        setTestingId(providerId);
        setTestResults(prev => { const r = { ...prev }; delete r[providerId]; return r; });
        const params = new URLSearchParams({ provider_id: providerId });
        if (baseUrl) params.set('base_url', baseUrl);
        if (apiKey) params.set('api_key', apiKey);
        try {
            const res = await fetchWithRetry(`${API_BASE}/api/v1/providers/test?${params}`, {
                method: 'POST',
                headers: { Authorization: `Bearer ${user?.access_token || ''}` },
            }, 2);
            const data = res.ok ? await res.json() : null;
            if (res.status === 429) {
                toast.info('Rate limited — retrying with backoff');
            }
            setTestResults(prev => ({ ...prev, [providerId]: data || { status: 'error', message: `HTTP ${res.status}: ${res.statusText}` } }));
        } catch (e) {
            setTestResults(prev => ({ ...prev, [providerId]: { status: 'error', message: 'Connection failed — server unreachable' } }));
        }
        setTestingId(null);
    }, [user]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        const name = form.name.trim();
        const baseUrl = sanitizeUrl(form.base_url);
        if (!name) { toast.error('Provider name is required'); return; }
        if (name.length > 100) { toast.error('Provider name must be under 100 characters'); return; }
        if (!form.base_url.trim()) { toast.error('Base URL is required'); return; }
        if (!isValidUrl(baseUrl)) { toast.error('Invalid URL — must be http:// or https://'); return; }
        try {
            const body = {
                name,
                base_url: baseUrl,
                api_key: form.api_key.trim() || null,
                models: form.models ? form.models.split(',').map(m => m.trim()).filter(Boolean).slice(0, 50) : [],
                is_local: form.is_local,
                description: form.description.trim() || null,
            };
            const res = await fetchWithRetry(`${API_BASE}/api/v1/providers/custom`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${user?.access_token || ''}` },
                body: JSON.stringify(body),
            });
            if (res.ok) {
                toast.success(`Provider "${form.name}" added`);
                    setShowAddForm(false);
                    resetForm();
                    loadProviders();
            } else {
                const data = await res.json().catch(() => ({}));
                toast.error(data.detail || 'Failed to add provider');
            }
        } catch (e) { toast.error('Failed to add provider'); }
    };

    const handleUpdate = async (e) => {
        e.preventDefault();
        if (!editingProvider) return;
        const name = form.name.trim();
        const baseUrl = sanitizeUrl(form.base_url);
        if (form.base_url.trim() && !isValidUrl(baseUrl)) { toast.error('Invalid URL — must be http:// or https://'); return; }
        if (name && name.length > 100) { toast.error('Provider name must be under 100 characters'); return; }
        try {
            const body = {};
            if (name) body.name = name;
            if (form.base_url.trim()) body.base_url = baseUrl;
            if (form.api_key) body.api_key = form.api_key.trim() || null;
            if (form.models) body.models = form.models.split(',').map(m => m.trim()).filter(Boolean).slice(0, 50);
            body.is_local = form.is_local;
            if (form.description) body.description = form.description.trim() || null;

            const res = await fetchWithRetry(`${API_BASE}/api/v1/providers/custom/${editingProvider.id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${user?.access_token || ''}` },
                body: JSON.stringify(body),
            });
            if (res.ok) {
                    toast.success('Provider updated');
                    setEditingProvider(null);
                    resetForm();
                    loadProviders();
            } else {
                const data = await res.json().catch(() => ({}));
                toast.error(data.detail || 'Failed to update');
            }
        } catch (e) { toast.error('Failed to update provider'); }
    };

    const handleDelete = async (id) => {
        const confirmed = await confirm('This cannot be undone.', 'Delete Custom Provider?', 'Delete', 'danger');
        if (!confirmed) return;
        try {
            const res = await fetchWithRetry(`${API_BASE}/api/v1/providers/custom/${id}`, {
                method: 'DELETE',
                headers: { Authorization: `Bearer ${user?.access_token || ''}` },
            });
            if (res.ok) {
                loadProviders();
                toast.success('Provider deleted');
            } else {
                toast.error('Failed to delete provider');
            }
        } catch (e) { toast.error('Failed to delete — network error'); }
    };

    const handleInlineKeySave = async (providerId) => {
        const apiKey = keyFormValue.trim();
        if (!apiKey) { toast.error('API key is required'); return; }
        if (apiKey.length < 8) { toast.error('API key seems too short'); return; }
        try {
            const res = await fetchWithRetry(`${API_BASE}/api/v1/keys`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${user?.access_token || ''}` },
                body: JSON.stringify({ provider: providerId, api_key: apiKey, key_label: `${providerId} key` }),
            });
            if (res.ok) {
                toast.success(`API key saved for ${providerId}`);
                setKeyFormProvider(null);
                setKeyFormValue('');
                loadProviders();
                handleDiscoverModels(providerId, '');
            } else {
                const data = await res.json().catch(() => ({}));
                toast.error(data.detail || 'Failed to save API key');
            }
        } catch (e) { toast.error('Failed to save API key — network error'); }
    };

    const handleInlineKeyTest = async (providerId) => {
        const apiKey = keyFormValue.trim();
        if (!apiKey) { toast.error('Enter an API key to test'); return; }
        setKeyFormTesting(true);
        try {
            const res = await fetchWithRetry(`${API_BASE}/api/v1/keys/test`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${user?.access_token || ''}` },
                body: JSON.stringify({ provider: providerId, api_key: apiKey }),
            }, 2);
            const data = res.ok ? await res.json() : null;
            if (data?.status === 'valid') toast.success('Connection successful');
            else toast.error(data?.message || 'Connection failed');
        } catch (e) { toast.error('Connection failed — server unreachable'); }
        setKeyFormTesting(false);
    };

    const handleUseDiscovered = async (providerId, models) => {
        if (!models?.length) return;
        try {
            const res = await fetchWithRetry(`${API_BASE}/api/v1/providers/${providerId}/models/sync`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${user?.access_token || ''}` },
                body: JSON.stringify({ models }),
            });
            if (res.ok) {
                toast.success(`${models.length} model${models.length !== 1 ? 's' : ''} synced — now available in chat`);
            } else {
                toast.error('Failed to sync models');
            }
        } catch (e) { toast.error('Failed to sync models — network error'); }
    };

    const startEdit = (cp) => {
        setEditingProvider(cp);
        setForm({
            name: cp.name || '',
            base_url: cp.base_url || '',
            api_key: '',
            models: (cp.models || []).join(', '),
            is_local: cp.is_local || false,
            description: cp.description || '',
        });
        setShowAddForm(true);
    };

    const resetForm = () => {
        setForm({ name: '', base_url: '', api_key: '', models: '', is_local: false, description: '' });
        setEditingProvider(null);
        setShowAddForm(false);
        setDirty(false);
    };

    const filteredProviders = providers.filter(p =>
        p.name.toLowerCase().includes(debouncedSearch.toLowerCase()) ||
        p.provider_id?.toLowerCase().includes(debouncedSearch.toLowerCase()) ||
        p.models?.some(m => m.toLowerCase().includes(debouncedSearch.toLowerCase()))
    );

    if (loading) return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-900 py-8">
            <div className="max-w-6xl mx-auto px-4">
                <div className="mb-8">
                    <div className="h-9 w-48 bg-slate-200 dark:bg-slate-700 rounded animate-pulse mb-2" />
                    <div className="h-5 w-72 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {[1,2,3,4,5,6].map(i => (
                        <div key={i} className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
                            <div className="flex items-start gap-3 mb-4">
                                <div className="w-10 h-10 rounded-lg bg-slate-200 dark:bg-slate-700 animate-pulse" />
                                <div className="flex-1">
                                    <div className="h-5 w-28 bg-slate-200 dark:bg-slate-700 rounded animate-pulse mb-1" />
                                    <div className="h-4 w-20 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
                                </div>
                            </div>
                            <div className="space-y-2 mb-4">
                                <div className="h-4 w-full bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
                                <div className="h-4 w-3/4 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
                            </div>
                            <div className="h-9 w-full bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-900 py-8">
            <div className="max-w-6xl mx-auto px-4">
                {/* Header */}
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-8 gap-4">
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900 dark:text-white">Providers</h1>
                        <p className="text-slate-600 dark:text-slate-400 mt-1">
                            Configure AI model providers, API keys, and custom endpoints.
                        </p>
                    </div>
                    <div className="flex gap-3">
                        <a href="/api-keys" className="px-4 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition text-sm font-medium">
                            Manage Keys
                        </a>
                        <button onClick={() => { resetForm(); setShowAddForm(true); }}
                            className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition text-sm font-medium">
                            + Custom Provider
                        </button>
                    </div>
                </div>

                {/* Search */}
                <div className="mb-6">
                    <input type="text" value={searchTerm} onChange={e => setSearchTerm(e.target.value)}
                        placeholder="Search providers or models..."
                        className="w-full max-w-md px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500" />
                </div>

                {/* Add/Edit Form */}
                {showAddForm && (
                    <div className="mb-8 p-6 bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700">
                        <h2 className="text-xl font-semibold mb-4 text-slate-900 dark:text-white">
                            {editingProvider ? `Edit: ${editingProvider.name}` : 'Add Custom Provider'}
                        </h2>
                        <form onSubmit={editingProvider ? handleUpdate : handleSubmit} ref={formRef} className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Name *</label>
                                    <input type="text" value={form.name} onChange={e => { setForm({ ...form, name: e.target.value }); setDirty(true); }}
                                        placeholder="My Local LLM"
                                        className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white" />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Base URL *</label>
                                    <input type="url" value={form.base_url} onChange={e => { setForm({ ...form, base_url: e.target.value }); setDirty(true); }}
                                        placeholder="http://localhost:8000/v1"
                                        className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white font-mono text-sm" />
                                </div>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">API Key (optional for local models)</label>
                                <input type="password" value={form.api_key} onChange={e => { setForm({ ...form, api_key: e.target.value }); setDirty(true); }}
                                    placeholder={editingProvider ? '(leave blank to keep existing)' : 'sk-...'}
                                    className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white font-mono text-sm" />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Models (comma-separated)</label>
                                <input type="text" value={form.models} onChange={e => { setForm({ ...form, models: e.target.value }); setDirty(true); }}
                                    placeholder="gpt-4o-mini, llama-3.1-8b, codestral"
                                    className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white font-mono text-sm" />
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Description</label>
                                    <input type="text" value={form.description} onChange={e => { setForm({ ...form, description: e.target.value }); setDirty(true); }}
                                        placeholder="My local vLLM server"
                                        className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white text-sm" />
                                </div>
                                <div className="flex items-center pt-6">
                                    <label className="flex items-center gap-3 cursor-pointer">
                                        <input type="checkbox" checked={form.is_local} onChange={e => { setForm({ ...form, is_local: e.target.checked }); setDirty(true); }}
                                            className="w-4 h-4 text-indigo-600 border-slate-300 rounded focus:ring-indigo-500" />
                                        <span className="text-sm text-slate-700 dark:text-slate-300">Local model (no API key needed)</span>
                                    </label>
                                </div>
                            </div>
                            <div className="flex gap-3">
                                <button type="submit" className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition text-sm font-medium">
                                    {editingProvider ? 'Update Provider' : 'Add Provider'}
                                </button>
                                <button type="button" onClick={() => { if (dirty) { confirm('Discard unsaved changes?', 'Unsaved Changes', 'Discard', 'warning').then(ok => { if (ok) resetForm(); }); } else { resetForm(); } }}
                                    className="px-4 py-2 bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-300 dark:hover:bg-slate-600 transition text-sm">
                                    Cancel {dirty && <span className="ml-1.5 w-2 h-2 bg-amber-400 rounded-full inline-block" title="Unsaved changes" />}
                                </button>
                            </div>
                        </form>
                    </div>
                )}

                {/* Loading / Error States */}
                {providersLoading && (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-4">
                        {[1,2,3,4,5,6].map(i => (
                            <div key={i} className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
                                <div className="flex items-start gap-3 mb-4">
                                    <div className="w-10 h-10 rounded-lg bg-slate-200 dark:bg-slate-700 animate-pulse" />
                                    <div className="flex-1">
                                        <div className="h-5 w-28 bg-slate-200 dark:bg-slate-700 rounded animate-pulse mb-1" />
                                        <div className="h-4 w-20 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
                                    </div>
                                </div>
                                <div className="space-y-2 mb-4">
                                    <div className="h-4 w-full bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
                                    <div className="h-4 w-3/4 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
                                </div>
                                <div className="h-9 w-full bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
                            </div>
                        ))}
                    </div>
                )}
                {!providersLoading && providersError && (
                    <div className="mb-6 p-6 bg-red-50 dark:bg-red-900/20 rounded-xl border border-red-200 dark:border-red-800 text-center">
                        <span className="material-symbols-outlined text-4xl text-red-400 mb-3">cloud_off</span>
                        <p className="text-sm text-red-700 dark:text-red-300 mb-3">{providersError}</p>
                        <button onClick={loadProviders}
                            className="px-4 py-2 bg-red-100 dark:bg-red-800/30 text-red-700 dark:text-red-300 rounded-lg hover:bg-red-200 dark:hover:bg-red-800/50 transition text-sm font-medium">
                            Retry
                        </button>
                    </div>
                )}
                {/* Provider Grid */}
                {!providersLoading && !providersError && (<>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {filteredProviders.map((p) => {
                        const isCustom = p.is_custom;
                        const testKey = isCustom ? `custom_${p.custom_provider_id}` : p.provider_id;
                        const testResult = testResults[testKey];
                        const isTesting = testingId === testKey;

                        return (
                            <div key={p.provider_id}
                                className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 hover:shadow-md transition-shadow">
                                {/* Header */}
                                <div className="flex items-start justify-between mb-4">
                                    <div className="flex items-center gap-3">
                                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-white text-lg ${isCustom ? 'bg-violet-500' : p.key_configured ? 'bg-emerald-500' : 'bg-slate-400'}`}>
                                            <span className="material-symbols-outlined text-[22px]">
                                                {PROVIDER_ICONS[p.provider_id] || (isCustom ? 'extension' : 'cloud')}
                                            </span>
                                        </div>
                                        <div>
                                            <h3 className="font-semibold text-slate-900 dark:text-white">{p.name}</h3>
                                            <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full ${isCustom ? 'bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300' : p.key_configured ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300' : 'bg-slate-100 dark:bg-slate-700 text-slate-500'}`}>
                                                <span className={`w-1.5 h-1.5 rounded-full ${isCustom ? 'bg-violet-500' : p.key_configured ? 'bg-emerald-500' : 'bg-slate-400'}`} />
                                                {isCustom ? 'Custom' : p.key_configured ? 'Configured' : 'Not Configured'}
                                            </span>
                                        </div>
                                    </div>
                                    {isCustom && (
                                        <div className="flex gap-1">
                                            <button onClick={() => startEdit(customProviders.find(c => c.id === p.custom_provider_id))}
                                                className="p-1.5 text-slate-400 hover:text-indigo-500 hover:bg-slate-100 dark:hover:bg-slate-700 rounded transition"
                                                title="Edit">
                                                <span className="material-symbols-outlined text-[18px]">edit</span>
                                            </button>
                                            <button onClick={() => handleDelete(p.custom_provider_id)}
                                                className="p-1.5 text-slate-400 hover:text-red-500 hover:bg-slate-100 dark:hover:bg-slate-700 rounded transition"
                                                title="Delete">
                                                <span className="material-symbols-outlined text-[18px]">delete</span>
                                            </button>
                                        </div>
                                    )}
                                </div>

                                {/* Details */}
                                <div className="space-y-2 text-sm mb-4">
                                    <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400">
                                        <span className="material-symbols-outlined text-[16px]">link</span>
                                        <span className="truncate">{typeof p.base_url === 'string' ? p.base_url : ''}</span>
                                    </div>
                                    {p.models && p.models.length > 0 && (
                                        <div>
                                            <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 mb-1">
                                                <span className="material-symbols-outlined text-[16px]">model_training</span>
                                                <span>{p.models.length} model{p.models.length !== 1 ? 's' : ''}</span>
                                            </div>
                                            <div className="flex flex-wrap gap-1">
                                                {(p.models || []).slice(0, 5).map(m => (
                                                    <span key={m} className="px-2 py-0.5 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded text-[10px] font-mono">
                                                        {m}
                                                    </span>
                                                ))}
                                                {(p.models || []).length > 5 && (
                                                    <span className="px-2 py-0.5 text-slate-400 text-[10px]">+{p.models.length - 5}</span>
                                                )}
                                            </div>
                                        </div>
                                    )}
                                    {!isCustom && (
                                        <div className="mt-2">
                                            <button onClick={() => handleDiscoverModels(p.provider_id, typeof p.base_url === 'string' ? p.base_url : '')}
                                                disabled={discovering === p.provider_id}
                                                className="flex items-center gap-1 text-[10px] text-slate-400 hover:text-indigo-500 transition disabled:opacity-50">
                                                <span className="material-symbols-outlined text-[14px]">{discovering === p.provider_id ? 'progress_activity' : 'travel_explore'}</span>
                                                {discovering === p.provider_id ? 'Discovering...' : 'Discover Models'}
                                            </button>
                                            {discoveredModels[p.provider_id] && discoveredModels[p.provider_id].length > 0 && (
                                                <div className="mt-2 p-2 bg-indigo-50 dark:bg-indigo-900/10 rounded-lg border border-indigo-200 dark:border-indigo-800">
                                                    <p className="text-[10px] font-medium text-indigo-600 dark:text-indigo-400 mb-1">Live API Models ({discoveredModels[p.provider_id].length})</p>
                                                    <div className="flex flex-wrap gap-1 max-h-24 overflow-y-auto mb-2">
                                                        {discoveredModels[p.provider_id].map(m => (
                                                            <span key={m} className="px-1.5 py-0.5 bg-white dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 rounded text-[9px] font-mono border border-indigo-200 dark:border-indigo-700">{m}</span>
                                                        ))}
                                                    </div>
                                                    <button onClick={() => handleUseDiscovered(p.provider_id, discoveredModels[p.provider_id])}
                                                        className="flex items-center gap-1 text-[10px] font-medium text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 transition">
                                                        <span className="material-symbols-outlined text-[12px]">check</span>
                                                        Use in Chat
                                                    </button>
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>

                                {/* Actions */}
                                <div className="flex gap-2">
                                    <button onClick={() => {
                                        const baseUrl = typeof p.base_url === 'string' ? p.base_url : '';
                                        handleTest(testKey, baseUrl, '');
                                    }} disabled={isTesting}
                                        className={`flex-1 py-2 text-xs font-medium rounded-lg border transition ${isTesting ? 'bg-slate-100 dark:bg-slate-700 text-slate-400' : 'bg-white dark:bg-slate-700 border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-600'}`}>
                                        {isTesting ? 'Testing...' : 'Test Connection'}
                                    </button>
                                    {!isCustom && (
                                        <button onClick={() => {
                                            if (keyFormProvider === p.provider_id) { setKeyFormProvider(null); setKeyFormValue(''); }
                                            else { setKeyFormProvider(p.provider_id); setKeyFormValue(''); }
                                        }}
                                            className={`py-2 px-3 text-xs font-medium rounded-lg border transition text-center ${p.key_configured ? 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300' : 'bg-indigo-50 dark:bg-indigo-900/20 border-indigo-200 dark:border-indigo-800 text-indigo-700 dark:text-indigo-300 hover:bg-indigo-100 dark:hover:bg-indigo-900/30'}`}>
                                            {p.key_configured ? 'Key Set' : 'Add Key'}
                                        </button>
                                    )}
                                </div>

                                {/* Inline API Key Form */}
                                {!isCustom && keyFormProvider === p.provider_id && (
                                    <div className="mt-3 p-3 bg-slate-50 dark:bg-slate-800/50 rounded-lg border border-slate-200 dark:border-slate-700 space-y-2">
                                        <p className="text-[11px] font-medium text-slate-600 dark:text-slate-400">Enter API Key for {p.name}</p>
                                        <input type="password" value={keyFormValue} onChange={e => setKeyFormValue(e.target.value)}
                                            placeholder="sk-..."
                                            className="w-full px-2.5 py-1.5 text-xs border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white font-mono focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                                            autoFocus
                                            onKeyDown={e => { if (e.key === 'Enter') handleInlineKeySave(p.provider_id); }} />
                                        <div className="flex gap-1.5">
                                            <button onClick={() => handleInlineKeySave(p.provider_id)}
                                                className="flex-1 py-1.5 text-[10px] font-medium bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition">Save Key</button>
                                            <button onClick={() => handleInlineKeyTest(p.provider_id)} disabled={keyFormTesting || !keyFormValue.trim()}
                                                className="flex-1 py-1.5 text-[10px] font-medium bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-600 transition disabled:opacity-50">{keyFormTesting ? 'Testing...' : 'Test'}</button>
                                            <button onClick={() => { setKeyFormProvider(null); setKeyFormValue(''); }}
                                                className="py-1.5 px-2 text-[10px] font-medium text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition">Cancel</button>
                                        </div>
                                    </div>
                                )}

                                {/* Test Result */}
                                {testResult && (
                                    <div className={`mt-3 p-3 rounded-lg text-xs ${testResult.status === 'valid' ? 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800' : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800'}`}>
                                        <div className="flex items-center gap-2">
                                            <span className={`w-2 h-2 rounded-full ${testResult.status === 'valid' ? 'bg-emerald-500' : 'bg-red-500'}`} />
                                            <span className="font-medium">{testResult.status === 'valid' ? 'Connected' : testResult.status === 'error' ? 'Error' : 'Failed'}</span>
                                            <span className="text-slate-400">({testResult.response_time_ms}ms)</span>
                                        </div>
                                        <p className="mt-1 text-slate-500 dark:text-slate-400">{testResult.message}</p>
                                        {testResult.models_found && testResult.models_found.length > 0 && (
                                            <div className="mt-2 flex flex-wrap gap-1">
                                                {testResult.models_found.map(m => (
                                                    <span key={m} className="px-1.5 py-0.5 bg-slate-100 dark:bg-slate-700 rounded text-[10px]">{m}</span>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>

                {/* Empty State */}
                {filteredProviders.length === 0 && (
                    <div className="p-12 text-center bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700">
                        <span className="material-symbols-outlined text-5xl text-slate-300 dark:text-slate-600 mb-4">cloud_off</span>
                        <p className="text-slate-500 dark:text-slate-400">No providers match your search.</p>
                    </div>
                )}
                </>)}
                {/* Contributor Section */}
                <div className="mt-8 p-6 bg-gradient-to-r from-indigo-50 to-blue-50 dark:from-indigo-900/20 dark:to-blue-900/20 rounded-xl border border-indigo-200 dark:border-indigo-800">
                    <div className="flex items-start gap-4">
                        <div className="w-12 h-12 rounded-xl bg-indigo-100 dark:bg-indigo-500/20 flex items-center justify-center shrink-0">
                            <span className="material-symbols-outlined text-2xl text-indigo-600 dark:text-indigo-400">code</span>
                        </div>
                        <div>
                            <h3 className="font-semibold text-lg text-slate-900 dark:text-white mb-1">Open Source Contributor?</h3>
                            <p className="text-sm text-slate-600 dark:text-slate-400 mb-3">
                                Set provider API keys in your <code className="px-1.5 py-0.5 bg-indigo-100 dark:bg-indigo-900/30 rounded text-indigo-700 dark:text-indigo-300 font-mono text-xs">backend/.env</code> file to run all features locally without adding keys via the UI.
                            </p>
                            <a href="/contributing" className="inline-flex items-center gap-1 text-sm font-medium text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300">
                                View Contributor Guide
                                <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default function ProvidersPage() {
    return <ErrorBoundary><ProvidersPageInner /></ErrorBoundary>;
}
