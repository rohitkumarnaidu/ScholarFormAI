'use client';
import { useState, useEffect, useRef } from 'react';
import { fetchWithRetry } from '@/utils/fetchWithRetry';
import { Brain, Check, ChevronDown, Loader2 } from 'lucide-react';
import DynamicIcon from '@/src/components/ui/DynamicIcon';

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

const ModelSelector = ({ selectedModel, onModelChange, userToken }) => {
    const [providers, setProviders] = useState([]);
    const [isOpen, setIsOpen] = useState(false);
    const [loading, setLoading] = useState(false);
    const dropdownRef = useRef(null);

    useEffect(() => {
        const fetchProviders = async () => {
            setLoading(true);
            try {
                const res = await fetchWithRetry(`${API_BASE}/api/v1/providers`, {
                    headers: { Authorization: `Bearer ${userToken || ''}` },
                });
                if (res.ok) {
                    const data = await res.json();
                    setProviders(data.providers || []);
                }
            } catch (e) { /* ignore */ }
            setLoading(false);
        };
        if (userToken) fetchProviders();
    }, [userToken]);

    useEffect(() => {
        const handleClickOutside = (e) => {
            if (dropdownRef.current && !dropdownRef.current.contains(e.target)) setIsOpen(false);
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const allModels = providers.flatMap(p =>
        (p.models || []).map(m => ({
            model: m,
            providerName: p.name,
            providerId: p.provider_id,
            isConfigured: p.key_configured || p.is_custom,
            icon: p.is_custom ? 'extension' : (PROVIDER_ICONS[p.provider_id] || 'cloud'),
        }))
    );

    const configuredModels = allModels.filter(m => m.isConfigured);
    const unconfiguredModels = allModels.filter(m => !m.isConfigured);

    const currentModelInfo = allModels.find(m => m.model === selectedModel);

    const handleSelect = (model) => {
        onModelChange(model);
        setIsOpen(false);
    };

    return (
        <div className="relative" ref={dropdownRef}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-1.5 px-2 py-1 text-xs rounded-md bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700 transition-colors"
                title={selectedModel ? `Using: ${selectedModel}` : 'Select model'}
            >
                <Brain className="text-[16px]" />
                <span className="max-w-[120px] truncate">{currentModelInfo?.model || selectedModel || 'Auto'}</span>
                {loading ? (
                    <Loader2 className="text-[16px] animate-spin" />
                ) : (
                    <ChevronDown className="text-[16px]" />
                )}
            </button>

            {isOpen && (
                <div className="absolute right-0 top-full mt-1 w-72 bg-white dark:bg-zinc-900 rounded-xl shadow-xl border border-zinc-200 dark:border-zinc-700 z-50 max-h-80 overflow-y-auto">
                    <div className="p-2 border-b border-zinc-100 dark:border-zinc-800">
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500 px-2 py-1">Model</p>
                    </div>

                    {configuredModels.length > 0 && (
                        <>
                            <div className="px-3 pt-2 pb-1">
                                <p className="text-[10px] font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">Available</p>
                            </div>
                            {configuredModels.map((m, i) => (
                                <button key={`${m.providerId}-${m.model}-${i}`}
                                    onClick={() => handleSelect(m.model)}
                                    className={`w-full flex items-center gap-2 px-3 py-2 text-xs text-left hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors ${selectedModel === m.model ? 'bg-indigo-50 dark:bg-indigo-500/10' : ''}`}>
                                    <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${m.isConfigured ? 'bg-emerald-500' : 'bg-slate-300'}`} />
                                    <span className="flex-1 truncate">{m.model}</span>
                                    <span className="flex items-center gap-1 text-[10px] text-zinc-400 shrink-0">
                                        <DynamicIcon name={m.icon} className="w-3 h-3" />
                                        {m.providerName}
                                    </span>
                                    {selectedModel === m.model && (
                                        <Check className="text-[14px] text-indigo-600 shrink-0" />
                                    )}
                                </button>
                            ))}
                        </>
                    )}

                    {unconfiguredModels.length > 0 && (
                        <>
                            <div className="px-3 pt-3 pb-1 border-t border-zinc-100 dark:border-zinc-800">
                                <p className="text-[10px] font-semibold uppercase tracking-wider text-zinc-400">Requires Key</p>
                            </div>
                            {unconfiguredModels.map((m, i) => (
                                <button key={`unconfig-${m.providerId}-${m.model}-${i}`}
                                    onClick={() => handleSelect(m.model)}
                                    disabled
                                    className="w-full flex items-center gap-2 px-3 py-2 text-xs text-left text-zinc-400 cursor-not-allowed opacity-60">
                                    <span className="w-1.5 h-1.5 rounded-full shrink-0 bg-slate-300" />
                                    <span className="flex-1 truncate">{m.model}</span>
                                    <span className="flex items-center gap-1 text-[10px]">
                                        <DynamicIcon name={m.icon} className="w-3 h-3" />
                                        {m.providerName}
                                    </span>
                                </button>
                            ))}
                        </>
                    )}

                    {allModels.length === 0 && (
                        <div className="p-4 text-center text-xs text-zinc-500">
                            <p>No models available.</p>
                            <a href="/providers" className="text-indigo-500 hover:underline mt-1 inline-block">Configure Providers</a>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default ModelSelector;
