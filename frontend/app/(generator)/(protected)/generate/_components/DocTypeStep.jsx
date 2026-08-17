'use client';

import { CheckCircle } from 'lucide-react';
import DynamicIcon from '@/src/components/ui/DynamicIcon';

const DOC_TYPES = [
    { id: 'academic_paper', label: 'Academic Paper', icon: 'article', description: 'Research paper with abstract, methodology, results, and references.', color: 'from-blue-500 to-blue-700' },
    { id: 'resume', label: 'Resume / CV', icon: 'badge', description: 'Professional CV with education, experience, and skills sections.', color: 'from-emerald-500 to-emerald-700' },
    { id: 'portfolio', label: 'Portfolio', icon: 'folder_special', description: 'Researcher or creative portfolio with projects and publications.', color: 'from-purple-500 to-purple-700' },
    { id: 'report', label: 'Technical Report', icon: 'description', description: 'Structured technical or business report with findings and recommendations.', color: 'from-orange-500 to-orange-700' },
    { id: 'thesis', label: 'Thesis Chapter', icon: 'school', description: 'Thesis or dissertation chapter with structured academic sections.', color: 'from-rose-500 to-rose-700' },
];

export default function DocTypeStep({ selected, onSelect }) {
    return (
        <div>
            <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-2">Choose Document Type</h2>
            <p className="text-slate-500 dark:text-slate-400 mb-8">Select the type of document you want to generate.</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {DOC_TYPES.map((docType) => (
                    <button
                        key={docType.id}
                        id={`doc-type-${docType.id}`}
                        onClick={() => onSelect(docType.id)}
                        className={`relative group flex flex-col items-start gap-3 p-5 rounded-2xl border-2 transition-all duration-200 text-left min-h-[120px] ${selected === docType.id
                            ? 'border-primary bg-primary/10 shadow-lg shadow-primary/20'
                            : 'border-glass-border bg-white/5 hover:border-glass-border/50 hover:bg-white/10'
                            }`}
                    >
                        <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${docType.color} flex items-center justify-center`}>
                            <DynamicIcon name={docType.icon} className="text-white w-5 h-5" />
                        </div>
                        <div>
                            <p className="font-semibold text-slate-900 dark:text-slate-100 text-sm">{docType.label}</p>
                            <p className="text-slate-500 dark:text-slate-400 text-xs mt-1 leading-relaxed">{docType.description}</p>
                        </div>
                        {selected === docType.id && (
                            <CheckCircle className="absolute top-3 right-3  text-primary-light text-base" />
                        )}
                    </button>
                ))}
            </div>
        </div>
    );
}
