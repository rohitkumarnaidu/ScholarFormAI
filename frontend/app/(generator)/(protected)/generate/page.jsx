// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

import usePageTitle from '@/src/hooks/usePageTitle';
import { useEffect } from 'react';
import DocTypeStep from './_components/DocTypeStep';
import GenerateStep from './_components/GenerateStep';
import MetadataStep from './_components/MetadataStep';
import StepIndicator from './_components/StepIndicator';
import TemplateStep from './_components/TemplateStep';
import { useGeneratorState } from './_components/useGeneratorState';

export default function DocumentGeneratorPage() {
    usePageTitle('Generate Document - ScholarForm AI');

    const {
        step,
        docType,
        template,
        metadata,
        templates,
        jobStatus,
        isSubmitting,
        canAdvance,
        steps,
        selectDocType,
        setTemplate,
        setMetadata,
        goBack,
        goNext,
        handleGenerate,
        handleDownload,
        handleReset,
    } = useGeneratorState();

    useEffect(() => {
        const handleKeyDown = (event) => {
            if (!(event.ctrlKey || event.metaKey) || event.key !== 'Enter') return;
            if (step >= 4) return;

            event.preventDefault();
            if (step === 3) {
                if (canAdvance && !isSubmitting) {
                    handleGenerate();
                }
                return;
            }

            if (canAdvance) {
                goNext();
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [step, canAdvance, isSubmitting, goNext, handleGenerate]);

    return (
        <div className="min-h-screen bg-background-light dark:bg-background-dark text-slate-900 dark:text-slate-100">
            <div className="max-w-4xl mx-auto px-4 py-10">
                <div className="text-center mb-10">
                    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-primary/10 border border-primary/20 text-primary-light text-xs font-medium mb-4">
                        <span className="material-symbols-outlined text-sm">auto_awesome</span>
                        AI Document Generator
                    </div>
                    <h1 className="text-3xl sm:text-4xl font-bold bg-gradient-to-r from-slate-900 to-slate-500 dark:from-white dark:to-gray-400 bg-clip-text text-transparent mb-2">
                        Generate from Scratch
                    </h1>
                    <p className="text-slate-500 text-sm">No file upload needed - describe your document, the AI writes it.</p>
                </div>

                <StepIndicator steps={steps} currentStep={step} />

                <div className="bg-glass-surface backdrop-blur-xl border border-glass-border rounded-2xl p-6 sm:p-8 shadow-2xl shadow-primary/10 animate-in fade-in zoom-in duration-500">
                    {step === 1 && <DocTypeStep selected={docType} onSelect={selectDocType} />}
                    {step === 2 && <TemplateStep selected={template} onSelect={setTemplate} templates={templates} />}
                    {step === 3 && <MetadataStep docType={docType} metadata={metadata} onChange={setMetadata} />}
                    {step === 4 && <GenerateStep {...jobStatus} onDownload={handleDownload} onReset={handleReset} />}

                    {step < 4 && (
                        <div className="flex justify-between mt-10 pt-6 border-t border-slate-200 dark:border-white/10">
                            <button
                                id="btn-back"
                                onClick={goBack}
                                disabled={step === 1}
                                className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-slate-100 dark:bg-white/5 text-slate-700 dark:text-slate-300 text-sm font-medium hover:bg-slate-200 dark:hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed transition min-h-[44px]"
                            >
                                <span className="material-symbols-outlined text-base">arrow_back</span>
                                Back
                            </button>
                            {step === 3 ? (
                                <button
                                    id="btn-generate"
                                    onClick={handleGenerate}
                                    disabled={!canAdvance || isSubmitting}
                                    title="Generate (Ctrl+Enter)"
                                    className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-primary to-primary-hover shadow-lg shadow-primary/30 hover:shadow-primary/50 text-white text-sm font-semibold hover:scale-[1.02] disabled:opacity-40 disabled:cursor-not-allowed transition min-h-[44px] active:scale-95"
                                >
                                    {isSubmitting ? (
                                        <>
                                            <span className="material-symbols-outlined text-base animate-spin">progress_activity</span>
                                            Starting...
                                        </>
                                    ) : (
                                        <>
                                            <span className="material-symbols-outlined text-base">auto_awesome</span>
                                            Generate Document
                                        </>
                                    )}
                                </button>
                            ) : (
                                <button
                                    id="btn-next"
                                    onClick={goNext}
                                    disabled={!canAdvance}
                                    title="Continue (Ctrl+Enter)"
                                    className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-primary to-primary-hover shadow-lg shadow-primary/30 hover:shadow-primary/50 text-white text-sm font-semibold hover:scale-[1.02] disabled:opacity-40 disabled:cursor-not-allowed transition min-h-[44px] active:scale-95"
                                >
                                    Continue
                                    <span className="material-symbols-outlined text-base">arrow_forward</span>
                                </button>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
