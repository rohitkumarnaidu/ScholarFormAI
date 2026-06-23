// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

import {
    DEFAULT_PAPER_SECTIONS,
    DEFAULT_RESUME_EDUCATION,
    DEFAULT_RESUME_EXPERIENCE,
} from './useGeneratorState';

export default function MetadataStep({ docType, metadata, onChange }) {
    const setValue = (key, value) => onChange({ ...metadata, [key]: value });

    const toggleSection = (index) => {
        const sections = [...(metadata.sections || DEFAULT_PAPER_SECTIONS)];
        sections[index] = { ...sections[index], include: !sections[index].include };
        onChange({ ...metadata, sections });
    };

    const updateArrayItem = (key, index, field, value) => {
        const list = [...(metadata[key] || [])];
        list[index] = { ...(list[index] || {}), [field]: value };
        onChange({ ...metadata, [key]: list });
    };

    const addArrayItem = (key, template) => onChange({ ...metadata, [key]: [...(metadata[key] || []), template] });

    const removeArrayItem = (key, index) => {
        const list = [...(metadata[key] || [])];
        list.splice(index, 1);
        onChange({
            ...metadata,
            [key]: list.length
                ? list
                : [key === 'education' ? { institution: '', degree: '', year: '' } : { company: '', role: '', duration: '', bullets_raw: '' }],
        });
    };

    const inputCls = 'w-full bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl px-4 py-3 text-slate-900 dark:text-slate-100 placeholder-slate-500 dark:placeholder-gray-600 text-sm focus:outline-none focus:border-primary transition';

    if (docType === 'academic_paper' || docType === 'thesis') {
        const sections = metadata.sections || DEFAULT_PAPER_SECTIONS;

        return (
            <div className="space-y-6">
                <div>
                    <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-1">Document Details</h2>
                    <p className="text-slate-500 dark:text-gray-400 text-sm">Fill in the details for your {docType === 'thesis' ? 'thesis chapter' : 'academic paper'}.</p>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="md:col-span-2">
                        <label className="text-slate-900 dark:text-slate-100 text-sm font-medium mb-1.5 block">Paper Title *</label>
                        <input id="meta-title" type="text" placeholder="e.g. Deep Learning for Academic Document Formatting" value={metadata.title || ''} onChange={(event) => setValue('title', event.target.value)} className={inputCls} />
                    </div>
                    <div>
                        <label className="text-slate-900 dark:text-slate-100 text-sm font-medium mb-1.5 block">Authors</label>
                        <input id="meta-authors" type="text" placeholder="e.g. John Doe, Jane Smith" value={metadata.authors_raw || ''} onChange={(event) => setValue('authors_raw', event.target.value)} className={inputCls} />
                    </div>
                    <div>
                        <label className="text-slate-900 dark:text-slate-100 text-sm font-medium mb-1.5 block">Affiliation</label>
                        <input id="meta-affiliation" type="text" placeholder="e.g. MIT, Cambridge University" value={metadata.affiliation || ''} onChange={(event) => setValue('affiliation', event.target.value)} className={inputCls} />
                    </div>
                    <div className="md:col-span-2">
                        <label className="text-slate-900 dark:text-slate-100 text-sm font-medium mb-1.5 block">Abstract</label>
                        <textarea id="meta-abstract" rows={4} placeholder="Brief description of your paper's aim, methods, and findings..." value={metadata.abstract || ''} onChange={(event) => setValue('abstract', event.target.value)} className={`${inputCls} resize-none`} />
                    </div>
                    <div>
                        <label className="text-slate-900 dark:text-slate-100 text-sm font-medium mb-1.5 block">Keywords</label>
                        <input id="meta-keywords" type="text" placeholder="e.g. machine learning, NLP, formatting" value={metadata.keywords_raw || ''} onChange={(event) => setValue('keywords_raw', event.target.value)} className={inputCls} />
                    </div>
                    <div>
                        <label className="text-slate-900 dark:text-slate-100 text-sm font-medium mb-1.5 block">Language</label>
                        <select id="meta-language" value={metadata.language || 'english'} onChange={(event) => setValue('language', event.target.value)} className={inputCls}>
                            {['english', 'spanish', 'french', 'german', 'portuguese', 'arabic'].map((language) => (
                                <option key={language} value={language} className="bg-background-light dark:bg-gray-900 text-slate-900 dark:text-slate-100">
                                    {language.charAt(0).toUpperCase() + language.slice(1)}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>
                <div>
                    <label className="text-slate-700 dark:text-slate-300 text-sm font-medium mb-3 block">Sections to Include</label>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                        {sections.map((section, index) => (
                            <button
                                key={section.name}
                                id={`section-${section.name.toLowerCase().replace(/\s+/g, '-')}`}
                                onClick={() => toggleSection(index)}
                                className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm transition min-h-[44px] ${section.include ? 'border-primary/50 bg-primary/10 text-blue-300' : 'border-white/10 bg-white/5 text-gray-500 hover:text-gray-300'}`}
                            >
                                <span className="material-symbols-outlined text-base">{section.include ? 'check_box' : 'check_box_outline_blank'}</span>
                                {section.name}
                            </button>
                        ))}
                    </div>
                </div>
                <div className="flex items-center gap-3 p-4 rounded-xl bg-white/5 border border-white/10">
                    <input id="option-placeholder" type="checkbox" checked={metadata.include_placeholder !== false} onChange={(event) => setValue('include_placeholder', event.target.checked)} className="w-4 h-4 accent-primary" />
                    <div>
                        <p className="text-slate-900 dark:text-slate-100 text-sm font-medium">Include placeholder content</p>
                        <p className="text-gray-500 text-xs">AI will write full paragraphs for each section (recommended)</p>
                    </div>
                </div>
            </div>
        );
    }

    if (docType === 'resume') {
        const education = metadata.education || [...DEFAULT_RESUME_EDUCATION];
        const experience = metadata.experience || [...DEFAULT_RESUME_EXPERIENCE];
        const resumeInputCls = 'bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg px-3 py-2 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:border-emerald-500 transition w-full';

        return (
            <div className="space-y-6">
                <div>
                    <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-1">Your Details</h2>
                    <p className="text-slate-500 dark:text-gray-400 text-sm">Fill in your information for the AI to generate your professional CV.</p>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {[
                        { key: 'name', label: 'Full Name *', placeholder: 'e.g. John Doe', id: 'meta-name' },
                        { key: 'email', label: 'Email', placeholder: 'john@example.com', id: 'meta-email' },
                        { key: 'phone', label: 'Phone', placeholder: '+1 (555) 000-0000', id: 'meta-phone' },
                        { key: 'linkedin', label: 'LinkedIn URL', placeholder: 'linkedin.com/in/johndoe', id: 'meta-linkedin' },
                    ].map((field) => (
                        <div key={field.key}>
                            <label className="text-slate-900 dark:text-slate-100 text-sm font-medium mb-1.5 block">{field.label}</label>
                            <input
                                id={field.id}
                                type="text"
                                placeholder={field.placeholder}
                                value={metadata[field.key] || ''}
                                onChange={(event) => setValue(field.key, event.target.value)}
                                className="w-full bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl px-4 py-3 text-slate-900 dark:text-slate-100 placeholder-slate-500 dark:placeholder-gray-600 text-sm focus:outline-none focus:border-emerald-500 transition"
                            />
                        </div>
                    ))}
                    <div className="md:col-span-2">
                        <label className="text-slate-900 dark:text-slate-100 text-sm font-medium mb-1.5 block">Professional Summary</label>
                        <textarea
                            id="meta-summary"
                            rows={3}
                            placeholder="Brief professional summary or career objective..."
                            value={metadata.summary || ''}
                            onChange={(event) => setValue('summary', event.target.value)}
                            className="w-full bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl px-4 py-3 text-slate-900 dark:text-slate-100 placeholder-slate-500 dark:placeholder-gray-600 text-sm focus:outline-none focus:border-emerald-500 transition resize-none"
                        />
                    </div>
                    <div className="md:col-span-2">
                        <label className="text-slate-900 dark:text-slate-100 text-sm font-medium mb-1.5 block">Skills</label>
                        <input
                            id="meta-skills"
                            type="text"
                            placeholder="e.g. Python, Machine Learning, React"
                            value={metadata.skills_raw || ''}
                            onChange={(event) => setValue('skills_raw', event.target.value)}
                            className="w-full bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl px-4 py-3 text-slate-900 dark:text-slate-100 placeholder-slate-500 dark:placeholder-gray-600 text-sm focus:outline-none focus:border-emerald-500 transition"
                        />
                    </div>
                    <div className="md:col-span-2">
                        <label className="text-slate-900 dark:text-slate-100 text-sm font-medium mb-1.5 block">Certifications</label>
                        <input
                            id="meta-certifications"
                            type="text"
                            placeholder="e.g. AWS Certified Developer, PMP"
                            value={metadata.certifications_raw || ''}
                            onChange={(event) => setValue('certifications_raw', event.target.value)}
                            className="w-full bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl px-4 py-3 text-slate-900 dark:text-slate-100 placeholder-slate-500 dark:placeholder-gray-600 text-sm focus:outline-none focus:border-emerald-500 transition"
                        />
                    </div>
                </div>
                <div className="space-y-3">
                    <div className="flex items-center justify-between">
                        <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">Education</h3>
                        <button type="button" id="btn-add-education" onClick={() => addArrayItem('education', { institution: '', degree: '', year: '' })} className="text-xs px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-white/10 hover:bg-slate-200 dark:hover:bg-white/20 text-slate-700 dark:text-white transition min-h-[36px]">Add Education</button>
                    </div>
                    {education.map((item, index) => (
                        <div key={`education-${index}`} className="grid grid-cols-1 md:grid-cols-3 gap-2 bg-white/5 border border-white/10 rounded-xl p-3">
                            <input type="text" placeholder="Institution" value={item.institution || ''} onChange={(event) => updateArrayItem('education', index, 'institution', event.target.value)} className={resumeInputCls} />
                            <input type="text" placeholder="Degree" value={item.degree || ''} onChange={(event) => updateArrayItem('education', index, 'degree', event.target.value)} className={resumeInputCls} />
                            <div className="flex gap-2">
                                <input type="text" placeholder="Year" value={item.year || ''} onChange={(event) => updateArrayItem('education', index, 'year', event.target.value)} className={`${resumeInputCls} flex-1`} />
                                {education.length > 1 && (
                                    <button type="button" onClick={() => removeArrayItem('education', index)} className="px-2 rounded-lg bg-red-500/20 text-red-300 hover:bg-red-500/30 transition" aria-label="Remove education entry">
                                        <span className="material-symbols-outlined text-base">delete</span>
                                    </button>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
                <div className="space-y-3">
                    <div className="flex items-center justify-between">
                        <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">Experience</h3>
                        <button type="button" id="btn-add-experience" onClick={() => addArrayItem('experience', { company: '', role: '', duration: '', bullets_raw: '' })} className="text-xs px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-white/10 hover:bg-slate-200 dark:hover:bg-white/20 text-slate-700 dark:text-white transition min-h-[36px]">Add Experience</button>
                    </div>
                    {experience.map((item, index) => (
                        <div key={`experience-${index}`} className="grid grid-cols-1 md:grid-cols-2 gap-2 bg-white/5 border border-white/10 rounded-xl p-3">
                            <input type="text" placeholder="Company" value={item.company || ''} onChange={(event) => updateArrayItem('experience', index, 'company', event.target.value)} className={resumeInputCls} />
                            <input type="text" placeholder="Role" value={item.role || ''} onChange={(event) => updateArrayItem('experience', index, 'role', event.target.value)} className={resumeInputCls} />
                            <input type="text" placeholder="Duration (e.g. 2021-2024)" value={item.duration || ''} onChange={(event) => updateArrayItem('experience', index, 'duration', event.target.value)} className={resumeInputCls} />
                            <div className="flex gap-2">
                                <input type="text" placeholder="Bullets (comma separated)" value={item.bullets_raw || ''} onChange={(event) => updateArrayItem('experience', index, 'bullets_raw', event.target.value)} className={`${resumeInputCls} flex-1`} />
                                {experience.length > 1 && (
                                    <button type="button" onClick={() => removeArrayItem('experience', index)} className="px-2 rounded-lg bg-red-500/20 text-red-300 hover:bg-red-500/30 transition" aria-label="Remove experience entry">
                                        <span className="material-symbols-outlined text-base">delete</span>
                                    </button>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-1">Document Details</h2>
                <p className="text-slate-500 dark:text-gray-400 text-sm">Provide details for your {docType.replace('_', ' ')}.</p>
            </div>
            <div className="grid grid-cols-1 gap-4">
                <div>
                    <label className="text-slate-900 dark:text-slate-100 text-sm font-medium mb-1.5 block">Title *</label>
                    <input id="meta-title-generic" type="text" placeholder="Document title" value={metadata.title || ''} onChange={(event) => setValue('title', event.target.value)} className={inputCls} />
                </div>
                <div>
                    <label className="text-slate-900 dark:text-slate-100 text-sm font-medium mb-1.5 block">Author / Name</label>
                    <input id="meta-name-generic" type="text" placeholder="Your name or organization" value={metadata.name || ''} onChange={(event) => setValue('name', event.target.value)} className={inputCls} />
                </div>
                <div>
                    <label className="text-slate-900 dark:text-slate-100 text-sm font-medium mb-1.5 block">Description / Abstract</label>
                    <textarea id="meta-abstract-generic" rows={4} placeholder="Brief description of the document's purpose and content..." value={metadata.abstract || ''} onChange={(event) => setValue('abstract', event.target.value)} className={`${inputCls} resize-none`} />
                </div>
            </div>
        </div>
    );
}
