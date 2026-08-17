'use client';
import usePageTitle from '@/src/hooks/usePageTitle';
import { Puzzle, Server } from 'lucide-react';

const PROVIDERS_CONFIG = [
    { name: 'OpenAI', env: 'OPENAI_API_KEY', url: 'https://platform.openai.com/api-keys' },
    { name: 'Anthropic', env: 'ANTHROPIC_API_KEY', url: 'https://console.anthropic.com/settings/keys' },
    { name: 'Groq', env: 'GROQ_API_KEY', url: 'https://console.groq.com/keys' },
    { name: 'DeepSeek', env: 'DEEPSEEK_API_KEY', url: 'https://platform.deepseek.com/api_keys' },
    { name: 'NVIDIA NIM', env: 'NVIDIA_API_KEY', url: 'https://build.nvidia.com/' },
    { name: 'OpenRouter', env: 'OPENROUTER_API_KEY', url: 'https://openrouter.ai/keys' },
    { name: 'Google AI', env: 'GOOGLE_API_KEY', url: 'https://aistudio.google.com/app/apikey' },
    { name: 'Cohere', env: 'COHERE_API_KEY', url: 'https://dashboard.cohere.com/api-keys' },
    { name: 'Mistral', env: 'MISTRAL_API_KEY', url: 'https://console.mistral.ai/api-keys/' },
];

const MODEL_ENV_VARS = [
    { var: 'NVIDIA_MODEL', default: 'meta/llama-3.3-70b-instruct', note: 'NVIDIA NIM model name' },
    { var: 'GROQ_MODEL', default: 'llama3-8b-8192', note: 'Default Groq model' },
    { var: 'OPENROUTER_MODEL', default: 'openai/gpt-4o-mini', note: 'Default OpenRouter model' },
    { var: 'OLLAMA_BASE_URL', default: 'http://localhost:11434', note: 'Ollama server URL' },
    { var: 'GROQ_API_BASE', default: 'https://api.groq.com/openai/v1', note: 'Groq API endpoint' },
    { var: 'OPENROUTER_API_BASE', default: 'https://openrouter.ai/api/v1', note: 'OpenRouter endpoint' },
];

export default function ContributingPage() {
    usePageTitle('Contributing');
    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-900 py-8">
            <div className="max-w-4xl mx-auto px-4">
                <div className="mb-8">
                    <h1 className="text-3xl font-bold text-slate-900 dark:text-white">Contributor Guide</h1>
                    <p className="text-slate-600 dark:text-slate-400 mt-2">
                        Set up ScholarForm AI locally for development or self-hosting.
                    </p>
                </div>

                {/* Quick Start */}
                <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6 mb-6">
                    <h2 className="text-xl font-semibold text-slate-900 dark:text-white mb-4">Quick Start</h2>
                    <div className="space-y-3">
                        <div className="flex items-start gap-3">
                            <span className="w-6 h-6 rounded-full bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">1</span>
                            <div>
                                <p className="font-medium text-slate-900 dark:text-white">Clone and install</p>
                                <pre className="mt-1 p-3 bg-slate-900 dark:bg-slate-950 text-slate-100 rounded-lg text-sm overflow-x-auto">git clone https://github.com/rohitkumarnaidu/ScholarForm AI.git
cd scholarform-ai/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt</pre>
                            </div>
                        </div>
                        <div className="flex items-start gap-3">
                            <span className="w-6 h-6 rounded-full bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">2</span>
                            <div>
                                <p className="font-medium text-slate-900 dark:text-white">Configure environment</p>
                                <pre className="mt-1 p-3 bg-slate-900 dark:bg-slate-950 text-slate-100 rounded-lg text-sm overflow-x-auto">cp .env.example .env
# Edit .env and add your API keys</pre>
                            </div>
                        </div>
                        <div className="flex items-start gap-3">
                            <span className="w-6 h-6 rounded-full bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">3</span>
                            <div>
                                <p className="font-medium text-slate-900 dark:text-white">Run the app</p>
                                <pre className="mt-1 p-3 bg-slate-900 dark:bg-slate-950 text-slate-100 rounded-lg text-sm overflow-x-auto"># Backend
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install && npm run dev</pre>
                            </div>
                        </div>
                    </div>
                </div>

                {/* API Key Configuration */}
                <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6 mb-6">
                    <h2 className="text-xl font-semibold text-slate-900 dark:text-white mb-4">API Key Configuration</h2>
                    <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">
                        Add any of these to your <code className="px-2 py-0.5 bg-slate-100 dark:bg-slate-700 rounded text-xs font-mono">backend/.env</code> file.
                        Set at least one provider key to use AI features.
                    </p>
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-slate-200 dark:border-slate-700">
                                    <th className="text-left py-2 px-3 text-slate-700 dark:text-slate-300 font-medium">Provider</th>
                                    <th className="text-left py-2 px-3 text-slate-700 dark:text-slate-300 font-medium">Env Variable</th>
                                    <th className="text-left py-2 px-3 text-slate-700 dark:text-slate-300 font-medium">Get Key</th>
                                </tr>
                            </thead>
                            <tbody>
                                {PROVIDERS_CONFIG.map(p => (
                                    <tr key={p.env} className="border-b border-slate-100 dark:border-slate-700/50">
                                        <td className="py-2.5 px-3 text-slate-900 dark:text-white font-medium">{p.name}</td>
<td className="py-2.5 px-3">
                            <code className="px-2 py-0.5 bg-slate-100 dark:bg-slate-700 rounded text-xs font-mono text-indigo-600 dark:text-indigo-400">{p.env}</code>
                        </td>
                        <td className="py-2.5 px-3">
                            <a href={p.url} target="_blank" rel="noopener noreferrer"
                                className="text-indigo-600 dark:text-indigo-400 hover:underline text-xs">
                                {new URL(p.url).hostname} &nearr;
                            </a>
                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Model Configuration */}
                <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6 mb-6">
                    <h2 className="text-xl font-semibold text-slate-900 dark:text-white mb-4">Model Configuration</h2>
                    <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">
                        Configure which models the app uses by default:
                    </p>
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-slate-200 dark:border-slate-700">
                                    <th className="text-left py-2 px-3 text-slate-700 dark:text-slate-300 font-medium">Variable</th>
                                    <th className="text-left py-2 px-3 text-slate-700 dark:text-slate-300 font-medium">Default</th>
                                    <th className="text-left py-2 px-3 text-slate-700 dark:text-slate-300 font-medium">Note</th>
                                </tr>
                            </thead>
                            <tbody>
                                {MODEL_ENV_VARS.map(m => (
                                    <tr key={m.var} className="border-b border-slate-100 dark:border-slate-700/50">
                                        <td className="py-2.5 px-3">
                                            <code className="px-2 py-0.5 bg-slate-100 dark:bg-slate-700 rounded text-xs font-mono text-indigo-600 dark:text-indigo-400">{m.var}</code>
                                        </td>
                                        <td className="py-2.5 px-3 font-mono text-xs text-slate-600 dark:text-slate-400">{m.default}</td>
                                        <td className="py-2.5 px-3 text-slate-500 dark:text-slate-400 text-xs">{m.note}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Local Models */}
                <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6 mb-6">
                    <h2 className="text-xl font-semibold text-slate-900 dark:text-white mb-4">Running Local Models</h2>
                    <div className="space-y-4 text-sm text-slate-600 dark:text-slate-400">
                        <div className="flex items-start gap-3">
                            <Server className="text-[20px] text-indigo-500 mt-0.5" />
                            <div>
                                <p className="font-medium text-slate-900 dark:text-white mb-1">Ollama</p>
                                <p>Install <a href="https://ollama.ai/download" target="_blank" rel="noopener noreferrer" className="text-indigo-600 dark:text-indigo-400 hover:underline">Ollama</a>, pull a model, and it&apos;s automatically available as the Tier 4 fallback.</p>
                                <pre className="mt-2 p-3 bg-slate-900 dark:bg-slate-950 text-slate-100 rounded-lg text-xs">ollama pull deepseek-r1
# Set OLLAMA_BASE_URL=http://localhost:11434 in .env</pre>
                            </div>
                        </div>
                        <div className="flex items-start gap-3">
                            <Puzzle className="text-[20px] text-indigo-500 mt-0.5" />
                            <div>
                                <p className="font-medium text-slate-900 dark:text-white mb-1">vLLM / LM Studio / Custom Endpoints</p>
                                <p>Add any OpenAI-compatible endpoint as a custom provider via the Providers page in the app.</p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Architecture */}
                <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
                    <h2 className="text-xl font-semibold text-slate-900 dark:text-white mb-4">Provider Fallback Architecture</h2>
                    <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">
                        When an AI request is made, ScholarForm AI tries providers in this order:
                    </p>
                    <div className="space-y-3">
                        {[
                            { tier: 1, name: 'NVIDIA NIM', desc: 'Fastest inference, requires NVIDIA_API_KEY' },
                            { tier: 2, name: 'Groq', desc: 'Fast open-source models, requires GROQ_API_KEY' },
                            { tier: 3, name: 'OpenRouter', desc: 'Unified API to many models, requires OPENROUTER_API_KEY' },
                            { tier: 4, name: 'Ollama (Local)', desc: 'Local inference with DeepSeek or any local model' },
                        ].map(t => (
                            <div key={t.tier} className="flex items-center gap-4 p-3 bg-slate-50 dark:bg-slate-900/50 rounded-lg">
                                <span className="w-8 h-8 rounded-full bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 flex items-center justify-center text-sm font-bold shrink-0">T{t.tier}</span>
                                <div>
                                    <p className="font-medium text-slate-900 dark:text-white text-sm">{t.name}</p>
                                    <p className="text-xs text-slate-500 dark:text-slate-400">{t.desc}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                    <p className="mt-4 text-xs text-slate-500 dark:text-slate-400">
                        Users can also bring their own API keys. When a user key exists for a provider, it takes priority over the env var. Custom providers added via the UI are available for model selection in the chat interface.
                    </p>
                </div>
            </div>
        </div>
    );
}
