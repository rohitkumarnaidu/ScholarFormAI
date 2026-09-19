'use client';
import { useState, useEffect, useRef } from 'react';
import { useAuth } from '@/src/context/AuthContext';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { useConfirm } from '@/src/components/ConfirmDialog';
import { useDebounce } from '@/src/hooks/useDebounce';
import ErrorBoundary from '@/src/components/ErrorBoundary';
import { ArrowRight, BrainCircuit, Check, CloudOff, Code, Edit, Globe, Link, Loader2, Trash2, Brain, Network, Zap, Cpu, Wind, Route, Gauge, Server as ServerIcon, Puzzle, Cloud } from 'lucide-react';
import { 
    useBuiltinProviders, 
    useCustomProviders, 
    useCreateCustomProvider, 
    useUpdateCustomProvider, 
    useDeleteCustomProvider, 
    useDiscoverModels, 
    useTestProvider, 
    useSyncModels 
} from '@/src/hooks/useProviders';
import { useCreateApiKey, useTestApiKey } from '@/src/hooks/useApiKeys';
import Button from '@/src/components/ui/Button';

const PROVIDER_ICONS: Record<string, any> = {
    openai: Brain,
    anthropic: BrainCircuit,
    groq: Zap,
    deepseek: Network,
    openrouter: Route,
    google: Globe,
    cohere: Cpu,
    mistral: Wind,
    ollama: ServerIcon,
    nvidia: Gauge,
};

function isValidUrl(str: string) {
    try {
        const url = new URL(str);
        return url.protocol === 'http:' || url.protocol === 'https:';
    } catch { return false; }
}

function sanitizeUrl(str: string) {
    let s = str.trim();
    if (!/^https?:\/\//i.test(s)) s = 'https://' + s;
    try { return new URL(s).toString().replace(/\/+$/, ''); } catch { return str.trim(); }
}

function ProvidersPageInner() {
    const { isLoggedIn, loading } = useAuth();
    const router = useRouter();
    
    const confirm = useConfirm();
    const formRef = useRef<HTMLFormElement>(null);
    const [dirty, setDirty] = useState(false);
    const [showAddForm, setShowAddForm] = useState(false);
    const [testingId, setTestingId] = useState<string | null>(null);
    const [testResults, setTestResults] = useState<Record<string, any>>({});
    const [searchTerm, setSearchTerm] = useState('');
    const [editingProvider, setEditingProvider] = useState<any>(null);
    const [form, setForm] = useState({ name: '', base_url: '', api_key: '', models: '', is_local: false, description: '' });
    const [keyFormProvider, setKeyFormProvider] = useState<string | null>(null);
    const [keyFormValue, setKeyFormValue] = useState('');
    
    const [discovering, setDiscovering] = useState<string | null>(null);
    const [discoveredModels, setDiscoveredModels] = useState<Record<string, string[]>>({});
    const debouncedSearch = useDebounce(searchTerm, 250);

    const { data: builtinData, isLoading: builtinLoading, error: builtinError, refetch: refetchBuiltin } = useBuiltinProviders();
    const { data: customData, isLoading: customLoading, error: customError, refetch: refetchCustom } = useCustomProviders();

    const createProviderMutation = useCreateCustomProvider();
    const updateProviderMutation = useUpdateCustomProvider();
    const deleteProviderMutation = useDeleteCustomProvider();
    const discoverModelsMutation = useDiscoverModels();
    const testProviderMutation = useTestProvider();
    const syncModelsMutation = useSyncModels();
    
    const createApiKeyMutation = useCreateApiKey();
    const testApiKeyMutation = useTestApiKey();

    const providers = builtinData?.providers || [];
    const customProviders = customData || [];
    const providersLoading = builtinLoading || customLoading;
    const providersError = builtinError ? (builtinError as Error).message : customError ? (customError as Error).message : null;

    const loadProviders = () => {
        refetchBuiltin();
        refetchCustom();
    };

    const handleDiscoverModels = (providerId: string, baseUrl: string) => {
        if (discovering === providerId) return;
        setDiscovering(providerId);
        discoverModelsMutation.mutate({ providerId, baseUrl }, {
            onSuccess: (data) => {
                setDiscoveredModels(prev => ({ ...prev, [providerId]: data?.models || [] }));
                setDiscovering(null);
            },
            onError: () => {
                setDiscovering(null);
            }
        });
    };

    useEffect(() => {
        if (!loading && !isLoggedIn) router.push('/login?next=/providers');
    }, [loading, isLoggedIn, router]);

    useEffect(() => {
        if (!showAddForm) return;
        function onKeyDown(e: KeyboardEvent) {
            if (e.key === 'Escape') {
                if (dirty) {
                    confirm('Discard unsaved changes?', 'Unsaved Changes', 'Discard', 'warning').then((ok: boolean) => { if (ok) resetForm(); });
                } else {
                    resetForm();
                }
            }
        }
        document.addEventListener('keydown', onKeyDown);
        return () => document.removeEventListener('keydown', onKeyDown);
    }, [showAddForm, dirty, confirm]);

    const handleTest = (providerId: string, baseUrl: string, apiKey: string) => {
        setTestingId(providerId);
        setTestResults(prev => { const r = { ...prev }; delete r[providerId]; return r; });
        testProviderMutation.mutate({ providerId, baseUrl, apiKey }, {
            onSuccess: (data) => {
                setTestResults(prev => ({ ...prev, [providerId]: data || { status: 'error', message: `No data returned` } }));
                setTestingId(null);
            },
            onError: (err: any) => {
                setTestResults(prev => ({ ...prev, [providerId]: { status: 'error', message: err?.message || 'Connection failed — server unreachable' } }));
                setTestingId(null);
            }
        });
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        const name = form.name.trim();
        const baseUrl = sanitizeUrl(form.base_url);
        if (!name) { toast.error('Provider name is required'); return; }
        if (name.length > 100) { toast.error('Provider name must be under 100 characters'); return; }
        if (!form.base_url.trim()) { toast.error('Base URL is required'); return; }
        if (!isValidUrl(baseUrl)) { toast.error('Invalid URL — must be http:// or https://'); return; }
        
        const body = {
            name,
            base_url: baseUrl,
            api_key: form.api_key.trim() || null,
            models: form.models ? form.models.split(',').map(m => m.trim()).filter(Boolean).slice(0, 50) : [],
            is_local: form.is_local,
            description: form.description.trim() || null,
        };
        
        createProviderMutation.mutate(body, {
            onSuccess: () => {
                setShowAddForm(false);
                resetForm();
            }
        });
    };

    const handleUpdate = (e: React.FormEvent) => {
        e.preventDefault();
        if (!editingProvider) return;
        const name = form.name.trim();
        const baseUrl = sanitizeUrl(form.base_url);
        if (form.base_url.trim() && !isValidUrl(baseUrl)) { toast.error('Invalid URL — must be http:// or https://'); return; }
        if (name && name.length > 100) { toast.error('Provider name must be under 100 characters'); return; }
        
        const body: any = {};
        if (name) body.name = name;
        if (form.base_url.trim()) body.base_url = baseUrl;
        if (form.api_key) body.api_key = form.api_key.trim() || null;
        if (form.models) body.models = form.models.split(',').map(m => m.trim()).filter(Boolean).slice(0, 50);
        body.is_local = form.is_local;
        if (form.description) body.description = form.description.trim() || null;

        updateProviderMutation.mutate({ id: editingProvider.id, data: body }, {
            onSuccess: () => {
                setEditingProvider(null);
                resetForm();
            }
        });
    };

    const handleDelete = async (id: string) => {
        const confirmed = await confirm('This cannot be undone.', 'Delete Custom Provider?', 'Delete', 'danger');
        if (!confirmed) return;
        deleteProviderMutation.mutate(id);
    };

    const handleInlineKeySave = (providerId: string) => {
        const apiKey = keyFormValue.trim();
        if (!apiKey) { toast.error('API key is required'); return; }
        if (apiKey.length < 8) { toast.error('API key seems too short'); return; }
        
        createApiKeyMutation.mutate({ provider: providerId, api_key: apiKey, key_label: `${providerId} key` }, {
            onSuccess: () => {
                setKeyFormProvider(null);
                setKeyFormValue('');
                loadProviders();
                handleDiscoverModels(providerId, '');
            }
        });
    };

    const handleInlineKeyTest = (providerId: string) => {
        const apiKey = keyFormValue.trim();
        if (!apiKey) { toast.error('Enter an API key to test'); return; }
        testApiKeyMutation.mutate({ provider: providerId, apiKey }, {
            onSuccess: (data: any) => {
                if (data?.status === 'valid') toast.success('Connection successful');
                else toast.error(data?.message || 'Connection failed');
            },
            onError: () => {
                toast.error('Connection failed — server unreachable');
            }
        });
    };

    const handleUseDiscovered = (providerId: string, models: string[]) => {
        if (!models?.length) return;
        syncModelsMutation.mutate({ providerId, models });
    };

    const startEdit = (cp: any) => {
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

    const filteredProviders = [...providers, ...customProviders].filter((p: any) =>
        (p.name || '').toLowerCase().includes(debouncedSearch.toLowerCase()) ||
        (p.provider_id || p.custom_provider_id || '').toLowerCase().includes(debouncedSearch.toLowerCase()) ||
        (p.models || []).some((m: string) => m.toLowerCase().includes(debouncedSearch.toLowerCase()))
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
                        <Button onClick={() => { resetForm(); setShowAddForm(true); }} variant="primary" size="sm">
                            + Custom Provider
                        </Button>
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
                                <Button type="submit" loading={createProviderMutation.isPending || updateProviderMutation.isPending} variant="primary" size="sm">
                                    {editingProvider ? 'Update Provider' : 'Add Provider'}
                                </Button>
                                <Button type="button" onClick={() => { if (dirty) { confirm('Discard unsaved changes?', 'Unsaved Changes', 'Discard', 'warning').then((ok: boolean) => { if (ok) resetForm(); }); } else { resetForm(); } }} variant="secondary" size="sm">
                                    Cancel {dirty && <span className="ml-1.5 w-2 h-2 bg-amber-400 rounded-full inline-block" title="Unsaved changes" />}
                                </Button>
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
                        <CloudOff className="text-4xl text-red-400 mb-3" />
                        <p className="text-sm text-red-700 dark:text-red-300 mb-3">{providersError}</p>
                        <Button onClick={loadProviders} variant="danger" size="sm" className="bg-red-100 dark:bg-red-800/30 text-red-700 dark:text-red-300 hover:bg-red-200 dark:hover:bg-red-800/50">
                            Retry
                        </Button>
                    </div>
                )}
                {/* Provider Grid */}
                {!providersLoading && !providersError && (<>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {filteredProviders.map((p: any) => {
                        const isCustom = 'custom_provider_id' in p;
                        const providerId = isCustom ? p.custom_provider_id : p.provider_id;
                        const testKey = isCustom ? `custom_${providerId}` : providerId;
                        const testResult = testResults[testKey];
                        const isTesting = testingId === testKey;

                        return (
                            <div key={testKey}
                                className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 hover:shadow-md transition-shadow">
                                {/* Header */}
                                <div className="flex items-start justify-between mb-4">
                                    <div className="flex items-center gap-3">
                                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-white text-lg ${isCustom ? 'bg-violet-500' : p.key_configured ? 'bg-emerald-500' : 'bg-slate-400'}`}>
                                            {(() => {
                                                const Icon = PROVIDER_ICONS[providerId] || (isCustom ? Puzzle : Cloud);
                                                return <Icon className="w-5.5 h-5.5" />;
                                            })()}
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
                                            <Button onClick={() => startEdit(p)} variant="ghost" size="icon" className="h-8 w-8 text-slate-400 hover:text-indigo-500" title="Edit">
                                                <Edit className="w-4 h-4" />
                                            </Button>
                                            <Button onClick={() => handleDelete(providerId)} variant="ghost" size="icon" className="h-8 w-8 text-slate-400 hover:text-red-500" title="Delete">
                                                <Trash2 className="w-4 h-4" />
                                            </Button>
                                        </div>
                                    )}
                                </div>

                                {/* Details */}
                                <div className="space-y-2 text-sm mb-4">
                                    <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400">
                                        <Link className="text-[16px]" />
                                        <span className="truncate">{typeof p.base_url === 'string' ? p.base_url : ''}</span>
                                    </div>
                                    {p.models && p.models.length > 0 && (
                                        <div>
                                            <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 mb-1">
                                                <BrainCircuit className="text-[16px]" />
                                                <span>{p.models.length} model{p.models.length !== 1 ? 's' : ''}</span>
                                            </div>
                                            <div className="flex flex-wrap gap-1">
                                                {(p.models || []).slice(0, 5).map((m: string) => (
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
                                            <button onClick={() => handleDiscoverModels(providerId, typeof p.base_url === 'string' ? p.base_url : '')}
                                                disabled={discovering === providerId}
                                                className="flex items-center gap-1 text-[10px] text-slate-400 hover:text-indigo-500 transition disabled:opacity-50">
                                                {discovering === providerId ? <Loader2 className="text-[14px]" /> : <Globe className="text-[14px]" />}
                                                {discovering === providerId ? 'Discovering...' : 'Discover Models'}
                                            </button>
                                            {discoveredModels[providerId] && discoveredModels[providerId].length > 0 && (
                                                <div className="mt-2 p-2 bg-indigo-50 dark:bg-indigo-900/10 rounded-lg border border-indigo-200 dark:border-indigo-800">
                                                    <p className="text-[10px] font-medium text-indigo-600 dark:text-indigo-400 mb-1">Live API Models ({discoveredModels[providerId].length})</p>
                                                    <div className="flex flex-wrap gap-1 max-h-24 overflow-y-auto mb-2">
                                                        {discoveredModels[providerId].map(m => (
                                                            <span key={m} className="px-1.5 py-0.5 bg-white dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 rounded text-[9px] font-mono border border-indigo-200 dark:border-indigo-700">{m}</span>
                                                        ))}
                                                    </div>
                                                    <button onClick={() => handleUseDiscovered(providerId, discoveredModels[providerId])}
                                                        className="flex items-center gap-1 text-[10px] font-medium text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 transition">
                                                        <Check className="text-[12px]" />
                                                        Use in Chat
                                                    </button>
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>

                                {/* Actions */}
                                <div className="flex gap-2">
                                    <Button onClick={() => {
                                        const baseUrl = typeof p.base_url === 'string' ? p.base_url : '';
                                        handleTest(testKey, baseUrl, '');
                                    }} loading={isTesting} variant="outline" size="sm" className="flex-1 text-xs">
                                        Test Connection
                                    </Button>
                                    {!isCustom && (
                                        <Button onClick={() => {
                                            if (keyFormProvider === providerId) { setKeyFormProvider(null); setKeyFormValue(''); }
                                            else { setKeyFormProvider(providerId); setKeyFormValue(''); }
                                        }} variant="outline" size="sm"
                                            className={`text-xs ${p.key_configured ? 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300' : 'bg-indigo-50 dark:bg-indigo-900/20 border-indigo-200 dark:border-indigo-800 text-indigo-700 dark:text-indigo-300 hover:bg-indigo-100 dark:hover:bg-indigo-900/30'}`}>
                                            {p.key_configured ? 'Key Set' : 'Add Key'}
                                        </Button>
                                    )}
                                </div>

                                {/* Inline API Key Form */}
                                {!isCustom && keyFormProvider === providerId && (
                                    <div className="mt-3 p-3 bg-slate-50 dark:bg-slate-800/50 rounded-lg border border-slate-200 dark:border-slate-700 space-y-2">
                                        <p className="text-[11px] font-medium text-slate-600 dark:text-slate-400">Enter API Key for {p.name}</p>
                                        <input type="password" value={keyFormValue} onChange={e => setKeyFormValue(e.target.value)}
                                            placeholder="sk-..."
                                            className="w-full px-2.5 py-1.5 text-xs border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white font-mono focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                                            autoFocus
                                            onKeyDown={e => { if (e.key === 'Enter') handleInlineKeySave(providerId); }} />
                                        <div className="flex gap-1.5">
                                            <Button onClick={() => handleInlineKeySave(providerId)} loading={createApiKeyMutation.isPending} variant="primary" size="sm"
                                                className="flex-1 h-7 text-[10px] px-2">Save Key</Button>
                                            <Button onClick={() => handleInlineKeyTest(providerId)} loading={testApiKeyMutation.isPending} disabled={!keyFormValue.trim()} variant="secondary" size="sm"
                                                className="flex-1 h-7 text-[10px] px-2">Test</Button>
                                            <Button onClick={() => { setKeyFormProvider(null); setKeyFormValue(''); }} variant="ghost" size="sm"
                                                className="h-7 text-[10px] px-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300">Cancel</Button>
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
                                                {testResult.models_found.map((m: string) => (
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
                        <CloudOff className="text-5xl text-slate-300 dark:text-slate-600 mb-4" />
                        <p className="text-slate-500 dark:text-slate-400">No providers match your search.</p>
                    </div>
                )}
                </>)}
                {/* Contributor Section */}
                <div className="mt-8 p-6 bg-gradient-to-r from-indigo-50 to-blue-50 dark:from-indigo-900/20 dark:to-blue-900/20 rounded-xl border border-indigo-200 dark:border-indigo-800">
                    <div className="flex items-start gap-4">
                        <div className="w-12 h-12 rounded-xl bg-indigo-100 dark:bg-indigo-500/20 flex items-center justify-center shrink-0">
                            <Code className="text-2xl text-indigo-600 dark:text-indigo-400" />
                        </div>
                        <div>
                            <h3 className="font-semibold text-lg text-slate-900 dark:text-white mb-1">Open Source Contributor?</h3>
                            <p className="text-sm text-slate-600 dark:text-slate-400 mb-3">
                                Set provider API keys in your <code className="px-1.5 py-0.5 bg-indigo-100 dark:bg-indigo-900/30 rounded text-indigo-700 dark:text-indigo-300 font-mono text-xs">backend/.env</code> file to run all features locally without adding keys via the UI.
                            </p>
                            <a href="/contributing" className="inline-flex items-center gap-1 text-sm font-medium text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300">
                                View Contributor Guide
                                <ArrowRight className="text-[16px]" />
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
