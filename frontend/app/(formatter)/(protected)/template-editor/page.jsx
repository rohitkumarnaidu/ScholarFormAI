// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import usePageTitle from '@/src/hooks/usePageTitle';
import { useEffect, useState, useCallback } from 'react';
import Footer from '@/src/components/Footer';
import { getCustomTemplates, saveCustomTemplate } from '@/src/services/api';
import { useToast } from '@/src/context/ToastContext';
import { useAuth } from '@/src/context/AuthContext';

const CUSTOM_TEMPLATES_KEY = 'scholarform_custom_templates';

const DEFAULT_SETTINGS = {
    name: '',
    fontFamily: 'Times New Roman',
    fontSize: 12,
    marginTop: 1,
    marginBottom: 1,
    marginLeft: 1,
    marginRight: 1,
    lineSpacing: 1.5,
    headerText: '',
    footerText: '',
};

const templateToYaml = (template) => {
    const safeString = (value) => `"${String(value || '').replace(/"/g, '\\"')}"`;

    return [
        `id: ${safeString(template.id)}`,
        `name: ${safeString(template.name)}`,
        `createdAt: ${safeString(template.createdAt)}`,
        'settings:',
        `  fontFamily: ${safeString(template.settings.fontFamily)}`,
        `  fontSize: ${Number(template.settings.fontSize)}`,
        '  margins:',
        `    top: ${Number(template.settings.margins.top)}`,
        `    bottom: ${Number(template.settings.margins.bottom)}`,
        `    left: ${Number(template.settings.margins.left)}`,
        `    right: ${Number(template.settings.margins.right)}`,
        `  lineSpacing: ${Number(template.settings.lineSpacing)}`,
        `  headerText: ${safeString(template.settings.headerText)}`,
        `  footerText: ${safeString(template.settings.footerText)}`,
    ].join('\n');
};

const readLocalTemplates = () => {
    try {
        const saved = JSON.parse(localStorage.getItem(CUSTOM_TEMPLATES_KEY) || '[]');
        return Array.isArray(saved) ? saved : [];
    } catch {
        return [];
    }
};

const normalizeTemplateCollection = (payload) => {
    if (Array.isArray(payload)) {
        return payload;
    }
    if (Array.isArray(payload?.templates)) {
        return payload.templates;
    }
    if (Array.isArray(payload?.data)) {
        return payload.data;
    }
    return [];
};

export default function TemplateEditor() {
    usePageTitle('Template Editor');
    const { loading: authLoading } = useAuth();
    const [settings, setSettings] = useState(DEFAULT_SETTINGS);
    const [savedTemplates, setSavedTemplates] = useState([]);
    const [saving, setSaving] = useState(false);
    const { addToast } = useToast();

    useEffect(() => {
        const localTemplates = readLocalTemplates();
        setSavedTemplates(localTemplates);

        // Wait for auth to finish loading before calling the API.
        // Without this guard, the request fires before the Supabase session
        // is read from localStorage, resulting in a 401 (no Bearer token).
        if (authLoading) return;

        let isMounted = true;

        const syncTemplatesFromApi = async () => {
            try {
                const payload = await getCustomTemplates();
                const apiTemplates = normalizeTemplateCollection(payload);
                if (!isMounted || apiTemplates.length === 0) {
                    return;
                }
                setSavedTemplates(apiTemplates);
                localStorage.setItem(CUSTOM_TEMPLATES_KEY, JSON.stringify(apiTemplates));
            } catch (error) {
                console.info('Template list API unavailable. Using local templates.', error);
            }
        };

        syncTemplatesFromApi();

        return () => {
            isMounted = false;
        };
    }, [authLoading]);

    const updateSetting = (key, value) => {
        setSettings((prev) => ({
            ...prev,
            [key]: value,
        }));
    };

    const saveTemplateLocal = (template) => {
        setSavedTemplates((previousTemplates) => {
            const next = [template, ...previousTemplates];
            localStorage.setItem(CUSTOM_TEMPLATES_KEY, JSON.stringify(next));
            return next;
        });
    };

    const exportTemplateYaml = (template) => {
        const yamlContent = templateToYaml(template);
        const blob = new Blob([yamlContent], { type: 'text/yaml;charset=utf-8' });
        const url = window.URL.createObjectURL(blob);
        const anchor = document.createElement('a');
        anchor.href = url;
        const safeName = String(template.name || 'custom-template')
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, '-')
            .replace(/^-+|-+$/g, '');
        anchor.download = `${safeName || 'custom-template'}.yaml`;
        document.body.appendChild(anchor);
        anchor.click();
        document.body.removeChild(anchor);
        setTimeout(() => window.URL.revokeObjectURL(url), 1000);
    };

    const handleSaveTemplate = useCallback(async () => {
        setSaving(true);
        const timestamp = new Date().toISOString();
        const templateName = settings.name?.trim() || `Custom Template ${savedTemplates.length + 1}`;
        const template = {
            id: timestamp,
            name: templateName,
            settings: {
                fontFamily: settings.fontFamily,
                fontSize: Number(settings.fontSize),
                margins: {
                    top: Number(settings.marginTop),
                    bottom: Number(settings.marginBottom),
                    left: Number(settings.marginLeft),
                    right: Number(settings.marginRight),
                },
                lineSpacing: Number(settings.lineSpacing),
                headerText: settings.headerText,
                footerText: settings.footerText,
            },
            createdAt: timestamp,
        };

        try {
            await saveCustomTemplate(template);
            saveTemplateLocal(template);
            addToast(`Saved "${templateName}" to cloud successfully.`, 'success');
        } catch (error) {
            saveTemplateLocal(template);
            addToast(`Saved "${templateName}" locally (API unavailable).`, 'warning');
            console.warn('Template API save failed. Falling back to localStorage.', error);
        }

        setSettings((prev) => ({
            ...DEFAULT_SETTINGS,
            fontFamily: prev.fontFamily,
            fontSize: prev.fontSize,
            lineSpacing: prev.lineSpacing,
        }));
        setSaving(false);
    }, [settings, savedTemplates.length, addToast]);

    useEffect(() => {
        const handleKeyDown = (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
                e.preventDefault();
                if (!saving) {
                    handleSaveTemplate();
                }
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [handleSaveTemplate, saving]);

    return (
        <div className="bg-background-light dark:bg-background-dark text-slate-900 dark:text-slate-100 min-h-screen flex flex-col font-display">
            
            <main className="max-w-5xl mx-auto w-full px-4 sm:px-6 py-6 sm:py-8 flex-1">
                <div className="mb-8">
                    <h1 className="text-2xl sm:text-3xl font-black text-slate-900 dark:text-white">Template Editor</h1>
                    <p className="text-slate-500 dark:text-slate-400 mt-2">
                        Create and save a custom formatting template for your manuscript workflow.
                    </p>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <section className="lg:col-span-2 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm space-y-5">
                        <h2 className="text-lg font-bold text-slate-900 dark:text-white">Formatting Settings</h2>

                        <div>
                            <label className="block text-sm font-semibold mb-2">Template Name</label>
                            <input
                                value={settings.name}
                                onChange={(e) => updateSetting('name', e.target.value)}
                                className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                                placeholder="My Journal Style"
                            />
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-semibold mb-2">Font Family</label>
                                <select
                                    value={settings.fontFamily}
                                    onChange={(e) => updateSetting('fontFamily', e.target.value)}
                                    className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                                >
                                    <option>Times New Roman</option>
                                    <option>Arial</option>
                                    <option>Calibri</option>
                                    <option>Georgia</option>
                                    <option>Cambria</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-semibold mb-2">Font Size (pt)</label>
                                <input
                                    type="number"
                                    min="8"
                                    max="18"
                                    value={settings.fontSize}
                                    onChange={(e) => updateSetting('fontSize', e.target.value)}
                                    className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                                />
                            </div>
                        </div>

                        <div>
                            <h3 className="text-sm font-semibold mb-2">Margins (inches)</h3>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                <input
                                    type="number"
                                    step="0.1"
                                    min="0.25"
                                    value={settings.marginTop}
                                    onChange={(e) => updateSetting('marginTop', e.target.value)}
                                    className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                                    placeholder="Top"
                                />
                                <input
                                    type="number"
                                    step="0.1"
                                    min="0.25"
                                    value={settings.marginBottom}
                                    onChange={(e) => updateSetting('marginBottom', e.target.value)}
                                    className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                                    placeholder="Bottom"
                                />
                                <input
                                    type="number"
                                    step="0.1"
                                    min="0.25"
                                    value={settings.marginLeft}
                                    onChange={(e) => updateSetting('marginLeft', e.target.value)}
                                    className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                                    placeholder="Left"
                                />
                                <input
                                    type="number"
                                    step="0.1"
                                    min="0.25"
                                    value={settings.marginRight}
                                    onChange={(e) => updateSetting('marginRight', e.target.value)}
                                    className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                                    placeholder="Right"
                                />
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-semibold mb-2">Line Spacing</label>
                                <input
                                    type="number"
                                    step="0.1"
                                    min="1"
                                    max="3"
                                    value={settings.lineSpacing}
                                    onChange={(e) => updateSetting('lineSpacing', e.target.value)}
                                    className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                                />
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-semibold mb-2">Header Text</label>
                            <input
                                value={settings.headerText}
                                onChange={(e) => updateSetting('headerText', e.target.value)}
                                className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                                placeholder="Optional running header"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-semibold mb-2">Footer Text</label>
                            <input
                                value={settings.footerText}
                                onChange={(e) => updateSetting('footerText', e.target.value)}
                                className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                                placeholder="Optional footer"
                            />
                        </div>

                        <button
                            onClick={handleSaveTemplate}
                            disabled={saving}
                            className="w-full md:w-auto px-5 py-2.5 rounded-lg bg-primary text-white font-bold hover:bg-blue-700 transition-colors"
                        >
                            {saving ? 'Saving...' : 'Save Custom Template'}
                        </button>
                    </section>

                    <aside className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm">
                        <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-4">Saved Templates</h2>
                        {savedTemplates.length === 0 ? (
                            <p className="text-sm text-slate-500 dark:text-slate-400">No custom templates saved yet.</p>
                        ) : (
                            <div className="space-y-3 max-h-[500px] overflow-y-auto">
                                {savedTemplates.map((savedTemplate) => (
                                    <div key={savedTemplate.id} className="rounded-lg border border-slate-200 dark:border-slate-700 p-3">
                                        <p className="font-semibold text-sm">{savedTemplate.name}</p>
                                        <p className="text-xs text-slate-500 mt-1">
                                            {savedTemplate.settings.fontFamily}, {savedTemplate.settings.fontSize}pt, {savedTemplate.settings.lineSpacing} spacing
                                        </p>
                                        <button
                                            onClick={() => exportTemplateYaml(savedTemplate)}
                                            className="mt-3 inline-flex items-center gap-1 text-xs font-bold text-primary hover:underline"
                                        >
                                            <span className="material-symbols-outlined text-[14px]">download</span>
                                            Export YAML
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </aside>
                </div>
            </main>

            <Footer variant="app" />
        </div>
    );
}
