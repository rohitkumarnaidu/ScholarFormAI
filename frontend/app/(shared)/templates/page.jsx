// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import usePageTitle from '@/src/hooks/usePageTitle';
import { useState, useEffect, useMemo } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { useRouter } from 'next/navigation';
import { ChevronDown, ChevronLeft, ChevronRight, CloudDownload, Loader2, PlusCircle, Search, SearchX, X } from 'lucide-react';
import DynamicIcon from '@/src/components/ui/DynamicIcon';

import { getBuiltinTemplates, searchCSLStyles, fetchCSLStyle } from '@/src/services/api'; // B-FIX-22f

// Built-in templates with stable UI metadata.
const BUILT_IN_TEMPLATES = [
    { id: 'ieee', name: 'IEEE', description: 'IEEE manuscript style for engineering and technical papers.', category: 'Engineering', citation: 'Numbered [1]', icon: 'architecture', available: true },
    { id: 'apa', name: 'APA (7th)', description: 'APA 7th Edition formatting for social and behavioral sciences.', category: 'Social Science', citation: 'Author-Year', icon: 'history_edu', available: true },
    { id: 'acm', name: 'ACM', description: 'ACM format for computer science conference and journal submissions.', category: 'Computer Science', citation: 'ACM Numbered', icon: 'computer', available: true },
    { id: 'springer', name: 'Springer', description: 'Springer-ready structure and references for scientific manuscripts.', category: 'Science', citation: 'Author-Year', icon: 'science', available: true },
    { id: 'elsevier', name: 'Elsevier', description: 'Elsevier manuscript formatting with numbered reference conventions.', category: 'Science', citation: 'Numbered', icon: 'description', available: true },
    { id: 'nature', name: 'Nature', description: 'Nature-style manuscript setup with superscript citation expectations.', category: 'Biology/Science', citation: 'Superscript', icon: 'biotech', available: true },
    { id: 'harvard', name: 'Harvard', description: 'Harvard referencing and document conventions for general use.', category: 'General', citation: 'Author-Year', icon: 'menu_book', available: true },
    { id: 'chicago', name: 'Chicago (17th)', description: 'Chicago Notes-Bibliography formatting for humanities writing.', category: 'Humanities', citation: 'Notes-Bib', icon: 'library_books', available: true },
    { id: 'mla', name: 'MLA (9th)', description: 'MLA 9th Edition formatting for language and literature manuscripts.', category: 'Humanities', citation: 'Author-Page', icon: 'book_2', available: true },
    { id: 'vancouver', name: 'Vancouver', description: 'Vancouver numeric style commonly used in medical publishing.', category: 'Medicine', citation: 'Numbered', icon: 'medication', available: true },
    { id: 'numeric', name: 'Numeric', description: 'Generic numbered citation template for broad journal compatibility.', category: 'General', citation: 'Numbered', icon: 'format_list_numbered', available: true },
    { id: 'none', name: 'None', description: 'Preserves document structure with minimal formatting intervention.', category: 'Passthrough', citation: 'Preserved', icon: 'filter_none', available: true },
    { id: 'modern_blue', name: 'Modern Blue', description: 'Modern visual treatment with blue accents and IEEE-like citation behavior.', category: 'Custom', citation: 'IEEE-based', icon: 'water_drop', available: true },
    { id: 'modern_gold', name: 'Modern Gold', description: 'Modern premium style with gold accents and APA-like citation behavior.', category: 'Custom', citation: 'APA-based', icon: 'auto_awesome', available: true },
    { id: 'modern_red', name: 'Modern Red', description: 'Modern expressive style with red accents and APA-like citation behavior.', category: 'Custom', citation: 'APA-based', icon: 'palette', available: true },
];

const BUILT_IN_TEMPLATE_MAP = new Map(BUILT_IN_TEMPLATES.map((template) => [template.id, template]));
const ITEMS_PER_PAGE = 6;

export default function Templates() {
    usePageTitle('Journal Templates');
    const router = useRouter();
    const navigate = (href, options = {}) => {
        if (options?.replace) {
            router.replace(href);
            return;
        }
        router.push(href);
    };
    const [templates, setTemplates] = useState(BUILT_IN_TEMPLATES);
    const [searchQuery, setSearchQuery] = useState('');
    const [activeCategory, setActiveCategory] = useState('All Publishers');
    const [currentPage, setCurrentPage] = useState(1);
    const [isLoading, setIsLoading] = useState(true);
    const [previewTemplate, setPreviewTemplate] = useState(null);
    // B-FIX-22f: CSL importer state
    const [cslQuery, setCslQuery] = useState('');
    const [cslResults, setCslResults] = useState([]);
    const [cslSearching, setCslSearching] = useState(false);
    const [cslImporting, setCslImporting] = useState(null); // slug being imported
    const [cslBanner, setCslBanner] = useState(null); // { type: 'success'|'error', msg }

    // Fetch templates from API on mount
    useEffect(() => {
        let cancelled = false;
        setIsLoading(true);

        getBuiltinTemplates()
            .then((data) => {
                if (cancelled) return;
                const templatesData = data?.templates ?? data ?? [];
                if (Array.isArray(templatesData) && templatesData.length > 0) {
                    const mappedTemplates = templatesData.map((template) => {
                        const templateId = template.id || template.name?.toLowerCase().replace(/\s+/g, '_');
                        const metadata = BUILT_IN_TEMPLATE_MAP.get(templateId) || {};
                        return {
                            ...metadata,
                            id: templateId,
                            name: template.name || metadata.name || templateId,
                            description: template.description || metadata.description || '',
                            category: template.category || metadata.category || 'General',
                            citation: template.citation || metadata.citation || 'Unknown',
                            icon: template.icon || metadata.icon || 'description',
                            available: template.available !== false && metadata.available !== false,
                            guidelines: template.guidelines || template.rules || null,
                        };
                    });

                    const byId = new Map(mappedTemplates.map((template) => [template.id, template]));
                    const allKnownTemplates = BUILT_IN_TEMPLATES.map((template) => byId.get(template.id) || template);
                    const additionalTemplates = mappedTemplates.filter((template) => !BUILT_IN_TEMPLATE_MAP.has(template.id));
                    setTemplates([...allKnownTemplates, ...additionalTemplates]);
                }
            })
            .catch((err) => {
                if (process.env.NODE_ENV === 'development') {
                    console.info('Templates API unavailable, using local fallback list:', err.message);
                }
            })
            .finally(() => {
                if (!cancelled) setIsLoading(false);
            });

        return () => { cancelled = true; };
    }, []);

    const categories = useMemo(() => ([
        'All Publishers',
        ...new Set(templates.map((template) => template.category).filter(Boolean)),
    ]), [templates]);

    // Filter templates by search and category
    const filteredTemplates = useMemo(() => {
        let list = templates;
        if (activeCategory !== 'All Publishers') {
            list = list.filter(t => t.category === activeCategory);
        }
        if (searchQuery.trim()) {
            const q = searchQuery.toLowerCase();
            list = list.filter(t =>
                t.name.toLowerCase().includes(q) ||
                t.description.toLowerCase().includes(q) ||
                t.category.toLowerCase().includes(q)
            );
        }
        return list;
    }, [templates, searchQuery, activeCategory]);

    // Pagination
    const totalPages = Math.max(1, Math.ceil(filteredTemplates.length / ITEMS_PER_PAGE));
    const paginatedTemplates = filteredTemplates.slice(
        (currentPage - 1) * ITEMS_PER_PAGE,
        currentPage * ITEMS_PER_PAGE
    );

    // Reset page when filter changes
    useEffect(() => {
        setCurrentPage(1);
    }, [searchQuery, activeCategory]);

    const handleSelectTemplate = (tmpl) => {
        if (!tmpl.available) return;
        // B-FIX-9: persist selected template through URL query for Next.js routing parity
        navigate(`/upload?template=${encodeURIComponent(tmpl.id)}`);
    };

    const handlePreviewGuidelines = (template) => {
        setPreviewTemplate(template);
    };

    // B-FIX-22f: CSL importer handlers
    const handleCslSearch = async (e) => {
        e.preventDefault();
        if (!cslQuery.trim()) return;
        setCslSearching(true);
        setCslResults([]);
        setCslBanner(null);
        try {
            const cslData = await searchCSLStyles(cslQuery.trim());
            const results = cslData?.results ?? cslData ?? [];
            const normalizedResults = Array.isArray(results) ? results : [];
            setCslResults(normalizedResults);
            if (!normalizedResults.length) setCslBanner({ type: 'info', msg: 'No styles found. Try a different journal name.' });
        } catch {
            setCslBanner({ type: 'error', msg: 'CSL search failed. Backend endpoint may not be available yet.' });
        } finally {
            setCslSearching(false);
        }
    };

    const handleCslImport = async (slug, name) => {
        setCslImporting(slug);
        setCslBanner(null);
        try {
            await fetchCSLStyle(slug);
            setCslBanner({ type: 'success', msg: `Imported "${name}" successfully! Refresh templates to see it.` });
        } catch {
            setCslBanner({ type: 'error', msg: `Failed to import "${name}". The backend CSL endpoint may not be ready.` });
        } finally {
            setCslImporting(null);
        }
    };

    return (
        <div className="bg-background-light dark:bg-background-dark font-display text-[#0d131b] dark:text-slate-200 min-h-screen flex flex-col">
            
            <main className="px-4 sm:px-6 lg:px-10 flex flex-1 justify-center py-8 sm:py-10">
                <div className="layout-content-container flex flex-col max-w-full max-w-[1200px] flex-1">
                    {/* Header Section */}
                    <div className="flex flex-col gap-6 p-4">
                        <div className="flex flex-wrap justify-between items-end gap-3">
                            <div className="flex flex-col gap-3">
                                <h1 className="text-[#0d131b] dark:text-white text-3xl sm:text-4xl font-black leading-tight tracking-[-0.033em]">Journal Template Library</h1>
                                <p className="text-[#4c6c9a] dark:text-slate-400 text-base font-normal leading-normal">Browse and select official academic formatting templates for your manuscript.</p>
                            </div>
                        </div>
                        {/* Search Bar */}
                        <div className="py-3">
                            <label className="flex flex-col min-w-40 h-14 w-full">
                                <div className="flex w-full flex-1 items-stretch rounded-xl h-full shadow-sm">
                                    <div className="text-[#4c6c9a] flex border-none bg-white dark:bg-slate-800 items-center justify-center pl-5 rounded-l-xl border-r-0">
                                        <Search className="text-[24px]" />
                                    </div>
                                    <input
                                        className="form-input flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-xl text-[#0d131b] dark:text-white focus:outline-0 focus:ring-0 border-none bg-white dark:bg-slate-800 focus:border-none h-full placeholder:text-[#4c6c9a] dark:placeholder:text-slate-500 px-4 rounded-l-none border-l-0 pl-3 text-lg font-normal leading-normal"
                                        placeholder="Search for journal (e.g., IEEE, Nature, Elsevier)..."
                                        value={searchQuery}
                                        onChange={(e) => setSearchQuery(e.target.value)}
                                    />
                                </div>
                            </label>
                        </div>
                        {/* Filters/Chips */}
                        <div className="flex gap-3 py-2 flex-wrap">
                            {categories.map((cat) => (
                                <button
                                    key={cat}
                                    onClick={() => setActiveCategory(cat)}
                                    className={`flex h-10 shrink-0 items-center justify-center gap-x-2 rounded-lg pl-4 pr-3 transition-all ${activeCategory === cat
                                        ? 'bg-primary text-white shadow-md'
                                        : 'bg-white dark:bg-slate-800 border border-[#e7ecf3] dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700'
                                        }`}
                                >
                                    <p className={`text-sm font-${activeCategory === cat ? 'semibold' : 'medium'} leading-normal ${activeCategory !== cat ? 'text-[#0d131b] dark:text-slate-300' : ''}`}>{cat}</p>
                                    <ChevronDown className="text-[20px]" />
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Skeleton Loading State */}
                    {isLoading && (
                        <div className="grid grid-cols-1 md:grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 p-4">
                            {Array.from({ length: 6 }).map((_, i) => (
                                <div key={i} className="flex flex-col gap-4 p-5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 animate-pulse">
                                    <div className="flex justify-between items-start">
                                        <div className="size-12 rounded-lg bg-slate-200 dark:bg-slate-700"></div>
                                        <div className="w-16 h-5 rounded-full bg-slate-200 dark:bg-slate-700"></div>
                                    </div>
                                    <div className="flex flex-col gap-2">
                                        <div className="h-5 w-3/4 rounded bg-slate-200 dark:bg-slate-700"></div>
                                        <div className="h-4 w-full rounded bg-slate-100 dark:bg-slate-800"></div>
                                        <div className="h-4 w-2/3 rounded bg-slate-100 dark:bg-slate-800"></div>
                                    </div>
                                    <div className="flex flex-col gap-3 mt-2">
                                        <div className="h-10 rounded-lg bg-slate-200 dark:bg-slate-700"></div>
                                        <div className="h-10 rounded-lg bg-slate-100 dark:bg-slate-800"></div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Template Grid */}
                    {!isLoading && (
                        <div className="grid grid-cols-1 md:grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 p-4">
                            {paginatedTemplates.map((template) => (
                                <div
                                    key={template.id}
                                    className={`flex flex-col gap-4 p-5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:shadow-xl hover:-translate-y-1 transition-all duration-300 group ${template.available ? 'hover:border-primary/30' : 'opacity-80 grayscale'
                                        }`}
                                >
                                    <div className="flex justify-between items-start">
                                        <div className={`size-12 rounded-lg bg-slate-50 dark:bg-slate-800 flex items-center justify-center border border-slate-100 dark:border-slate-700 ${template.available ? 'text-primary' : 'text-slate-400'}`}>
                                            <DynamicIcon name={template.icon} className="w-8 h-8" />
                                        </div>
                                        <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${template.available
                                            ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                                            : 'bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-300'
                                            }`}>
                                            {template.available ? 'Available' : 'Coming Soon'}
                                        </span>
                                    </div>
                                    <div className="flex flex-col gap-1">
                                        <h3 className="text-[#0d131b] dark:text-white text-xl font-bold">{template.name}</h3>
                                        <p className="text-sm text-[#4c6c9a] dark:text-slate-400 leading-relaxed min-h-[40px] line-clamp-2">{template.description}</p>
                                    </div>
                                    <div className="flex flex-col gap-3 mt-2">
                                        <button
                                            onClick={() => handleSelectTemplate(template)}
                                            disabled={!template.available}
                                            className={`w-full py-2.5 rounded-lg font-semibold text-sm transition-colors ${template.available
                                                ? 'bg-primary text-white hover:bg-primary/90'
                                                : 'bg-slate-200 dark:bg-slate-800 text-slate-500 cursor-not-allowed'
                                                }`}
                                        >
                                            Select Template
                                        </button>
                                        <button
                                            onClick={() => handlePreviewGuidelines(template)}
                                            className="w-full bg-slate-100 dark:bg-slate-800 text-[#0d131b] dark:text-slate-300 py-2.5 rounded-lg font-semibold text-sm hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
                                        >
                                            Preview Guidelines
                                        </button>
                                    </div>
                                </div>
                            ))}

                            {/* Request Template Card */}
                            <div
                                className="flex flex-col items-center justify-center gap-4 p-5 rounded-xl bg-slate-50/50 dark:bg-slate-800/20 border-2 border-dashed border-slate-200 dark:border-slate-700 hover:border-primary/50 transition-all cursor-pointer group"
                                onClick={() => window.open('mailto:templates@scholarform.ai?subject=Template%20Request', '_self')}
                            >
                                <div className="size-14 rounded-full bg-white dark:bg-slate-800 flex items-center justify-center text-slate-400 group-hover:text-primary shadow-sm transition-colors">
                                    <PlusCircle className="text-[32px]" />
                                </div>
                                <div className="text-center">
                                    <h3 className="text-[#0d131b] dark:text-white text-lg font-bold">Missing a journal?</h3>
                                    <p className="text-sm text-[#4c6c9a] dark:text-slate-400 px-4">Request a new formatting template and our team will add it within 48 hours.</p>
                                </div>
                                <span className="text-primary text-sm font-bold hover:underline">Request Template</span>
                            </div>

                            {/* No results */}
                            {paginatedTemplates.length === 0 && (
                                <div className="col-span-full flex flex-col items-center justify-center py-12 text-center">
                                    <SearchX className="text-4xl text-slate-300 mb-3" />
                                    <p className="text-slate-500 font-medium">No templates found matching your criteria.</p>
                                    <button
                                        onClick={() => { setSearchQuery(''); setActiveCategory('All Publishers'); }}
                                        className="mt-3 text-primary text-sm font-bold hover:underline"
                                    >
                                        Clear filters
                                    </button>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Pagination */}
                    {!isLoading && totalPages > 1 && (
                        <div className="flex items-center justify-center gap-2 sm:gap-4 mt-12 py-6 border-t border-slate-200 dark:border-slate-800 flex-wrap">
                            <button
                                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                                disabled={currentPage === 1}
                                className="p-2 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-white dark:hover:bg-slate-800 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                            >
                                <ChevronLeft />
                            </button>
                            <div className="flex gap-2">
                                {Array.from({ length: totalPages }, (_, i) => i + 1).map(page => (
                                    <button
                                        key={page}
                                        onClick={() => setCurrentPage(page)}
                                        className={`w-10 h-10 rounded-lg font-bold transition-colors ${currentPage === page
                                            ? 'bg-primary text-white'
                                            : 'bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700'
                                            }`}
                                    >
                                        {page}
                                    </button>
                                ))}
                            </div>
                            <button
                                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                                disabled={currentPage === totalPages}
                                className="p-2 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-white dark:hover:bg-slate-800 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                            >
                                <ChevronRight />
                            </button>
                        </div>
                    )}

                    {/* CSL Import Section */}
                    <div className="mt-12 p-6 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-800 transition-colors">
                        <div className="flex flex-col gap-2 mb-6">
                            <h3 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                                <CloudDownload className="text-primary" />
                                Import Custom Style
                            </h3>
                            <p className="text-sm text-slate-500 dark:text-slate-400">Search the global Citation Style Language (CSL) repository (10,000+ journals).</p>
                        </div>

                        {cslBanner && (
                            <div className={`mb-4 p-3 rounded-lg text-sm font-medium ${cslBanner.type === 'error' ? 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400 border border-red-200 dark:border-red-800/50' : cslBanner.type === 'success' ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400 border border-green-200 dark:border-green-800/50' : 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400 border border-blue-200 dark:border-blue-800/50'}`}>
                                {cslBanner.msg}
                            </div>
                        )}

                        <form onSubmit={handleCslSearch} className="flex gap-3 max-w-2xl mb-2">
                            <div className="relative flex-1">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                                <input
                                    type="text"
                                    value={cslQuery}
                                    onChange={(e) => setCslQuery(e.target.value)}
                                    placeholder="e.g. American Medical Association"
                                    className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 focus:ring-2 focus:ring-primary focus:border-transparent transition-all disabled:opacity-50 text-slate-900 dark:text-white"
                                    disabled={cslSearching || Boolean(cslImporting)}
                                />
                            </div>
                            <button
                                type="submit"
                                disabled={!cslQuery.trim() || cslSearching || Boolean(cslImporting)}
                                className="px-6 py-2.5 bg-slate-900 dark:bg-white text-white dark:text-slate-900 font-bold rounded-lg hover:bg-slate-800 dark:hover:bg-slate-100 disabled:opacity-50 transition-colors flex items-center gap-2 justify-center min-w-[120px]"
                            >
                                {cslSearching ? (
                                    <><Loader2 className="animate-spin text-[18px]" /> Searching</>
                                ) : 'Search'}
                            </button>
                        </form>

                        {cslResults.length > 0 && (
                            <div className="mt-4 border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden bg-white dark:bg-slate-900 shadow-sm">
                                <ul className="divide-y divide-slate-100 dark:divide-slate-800 max-h-64 overflow-y-auto">
                                    {cslResults.map((res) => (
                                        <li key={res.slug} className="flex justify-between items-center p-3 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                                            <span className="text-sm font-medium text-slate-900 dark:text-white truncate pr-4">{res.title}</span>
                                            <button
                                                onClick={() => handleCslImport(res.slug, res.title)}
                                                disabled={Boolean(cslImporting)}
                                                className="shrink-0 px-4 py-1.5 bg-primary/10 text-primary hover:bg-primary hover:text-white rounded-md text-xs font-bold transition-colors disabled:opacity-50 flex items-center justify-center min-w-[80px]"
                                            >
                                                {cslImporting === res.slug ? (
                                                    <Loader2 className="animate-spin text-[16px]" />
                                                ) : 'Import'}
                                            </button>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>
                </div>
            </main>

            <Dialog.Root
                open={Boolean(previewTemplate)}
                onOpenChange={(open) => {
                    if (!open) setPreviewTemplate(null);
                }}
            >
                <Dialog.Portal>
                    <Dialog.Overlay className="fixed inset-0 z-[100] bg-black/50 backdrop-blur-sm" />
                    {previewTemplate && (
                        <Dialog.Content className="fixed left-1/2 top-1/2 z-[110] w-[calc(100vw-2rem)] max-w-lg max-h-[80vh] -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-2xl border border-slate-200 bg-white shadow-2xl focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 dark:border-slate-800 dark:bg-slate-900">
                            <div className="p-6 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <div className="size-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
                                        <DynamicIcon name={previewTemplate.icon} />
                                    </div>
                                    <div>
                                        <Dialog.Title className="text-lg font-bold text-slate-900 dark:text-white">
                                            {previewTemplate.name}
                                        </Dialog.Title>
                                        <Dialog.Description className="text-xs text-slate-500">
                                            {previewTemplate.category}
                                        </Dialog.Description>
                                    </div>
                                </div>
                                <Dialog.Close asChild>
                                    <button
                                        type="button"
                                        className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                                        aria-label="Close template preview"
                                    >
                                        <X className="text-slate-400" />
                                    </button>
                                </Dialog.Close>
                            </div>
                            <div className="p-6">
                                <h4 className="font-bold text-slate-900 dark:text-white mb-3">Formatting Guidelines</h4>
                                {previewTemplate.guidelines ? (
                                    <pre className="text-sm text-slate-600 dark:text-slate-400 whitespace-pre-wrap font-sans leading-relaxed">{typeof previewTemplate.guidelines === 'string' ? previewTemplate.guidelines : JSON.stringify(previewTemplate.guidelines, null, 2)}</pre>
                                ) : (
                                    <div className="space-y-3 text-sm text-slate-600 dark:text-slate-400">
                                        <p>{previewTemplate.description}</p>
                                        <div className="bg-slate-50 dark:bg-slate-800 rounded-lg p-4 space-y-2">
                                            <p className="font-bold text-slate-700 dark:text-slate-200">Standard Rules:</p>
                                            <ul className="list-disc list-inside space-y-1">
                                                <li>Two-column layout (where applicable)</li>
                                                <li>Times New Roman / Computer Modern fonts</li>
                                                <li>Numbered references in order of citation</li>
                                                <li>Author-date citation style (APA) or numbered</li>
                                                <li>Section numbering with hierarchical headings</li>
                                                <li>Abstract limited to 200-250 words</li>
                                            </ul>
                                        </div>
                                    </div>
                                )}
                            </div>
                            <div className="p-6 border-t border-slate-200 dark:border-slate-800 flex gap-3">
                                <button
                                    onClick={() => { handleSelectTemplate(previewTemplate); setPreviewTemplate(null); }}
                                    disabled={!previewTemplate.available}
                                    className={`flex-1 py-2.5 rounded-lg font-bold text-sm transition-colors ${previewTemplate.available ? 'bg-primary text-white hover:bg-blue-600' : 'bg-slate-200 text-slate-500 cursor-not-allowed'}`}
                                >
                                    {previewTemplate.available ? 'Use This Template' : 'Coming Soon'}
                                </button>
                                <Dialog.Close asChild>
                                    <button
                                        type="button"
                                        className="px-6 py-2.5 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-lg font-bold text-sm hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
                                    >
                                        Close
                                    </button>
                                </Dialog.Close>
                            </div>
                        </Dialog.Content>
                    )}
                </Dialog.Portal>
            </Dialog.Root>

        </div>
    );
}

