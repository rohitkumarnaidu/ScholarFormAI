// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

import { useRef, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';

import usePageTitle from '@/src/hooks/usePageTitle';
import { useAuth } from '@/src/context/AuthContext';
import { useUpload } from '@/src/hooks/useUpload';
import { trackPageView } from '@/src/lib/rum';

// Core Components
import CategoryTabs from '@/src/components/upload/CategoryTabs';
import TemplateSelector from '@/src/components/upload/TemplateSelector';
import FormattingOptions from '@/src/components/upload/FormattingOptions';
import ProcessingStepper from '@/src/components/upload/ProcessingStepper';
import FastModeToggle from '@/src/components/FastModeToggle';
import { AlertTriangle, CloudUpload, FileUp, RefreshCw, X, XCircle } from 'lucide-react';

const ACCEPTED_FORMATS = '.docx,.pdf,.tex,.txt,.html,.htm,.md,.markdown,.doc';
const MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024;

const STEPS = [
    { id: 1, title: 'Uploading Manuscript', desc: 'Sending file to server...' },
    { id: 2, title: 'Converting Format', desc: 'Extracting text and layout...' },
    { id: 3, title: 'Parsing Structure', desc: 'Mapping sections and elements...' },
    { id: 4, title: 'Analyzing Content (AI)', desc: 'Detecting citation errors & gaps...' },
    { id: 5, title: 'Journal Validation', desc: 'Checking against template rules...' },
    { id: 6, title: 'Final Formatting', desc: 'Applying styles and layouts...' },
    { id: 7, title: 'Exporting Result', desc: 'Generating publication-ready file...' },
];

function UploadContent() {
    usePageTitle('Upload Document');
    useEffect(() => { trackPageView('/upload'); }, []);
    const { isLoggedIn } = useAuth();
    const searchParams = useSearchParams();
    const fileInputRef = useRef(null);

    const {
        file, setFile,
        isProcessing,
        progress,
        currentStep,
        statusMessage,
        template, setTemplate,
        category, setCategory,
        fileError, setFileError,
        formattingOptions, updateFormattingOption,
        remaining,
        startUpload,
        cancelUpload,
        resetProgress
    } = useUpload();

    // Pre-select template from query param
    useEffect(() => {
        const preSelectedTemplate = searchParams.get('template');
        if (preSelectedTemplate && typeof preSelectedTemplate === 'string') {
            setTemplate(preSelectedTemplate);
            setCategory(preSelectedTemplate === 'none' ? 'none' : preSelectedTemplate);
        }
    }, [searchParams, setTemplate, setCategory]);

    // Keyboard shortcuts
    useEffect(() => {
        const handler = (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                e.preventDefault();
                startUpload();
            }
            if (e.key === 'Escape') {
                e.preventDefault();
                cancelUpload();
            }
        };
        window.addEventListener('keydown', handler);
        return () => window.removeEventListener('keydown', handler);
    }, [cancelUpload, startUpload]);

    const handleFileChange = (e) => {
        setFileError(null);
        const selectedFile = e.target.files[0];
        if (selectedFile) {
            if (selectedFile.size > MAX_UPLOAD_SIZE_BYTES) {
                setFileError('File size exceeds 50MB limit.');
                return;
            }
            setFile(selectedFile);
            if (progress === 100) resetProgress();
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        if (isProcessing) return;
        setFileError(null);
        const droppedFile = e.dataTransfer.files[0];
        if (droppedFile) {
            if (droppedFile.size > MAX_UPLOAD_SIZE_BYTES) {
                setFileError('File size exceeds 50MB limit.');
                return;
            }
            setFile(droppedFile);
            if (progress === 100) resetProgress();
        }
    };

    const formatFileSize = (bytes) => {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    const quotaWarning = (remaining <= 2 && remaining > 0) 
        ? `${remaining} upload${remaining !== 1 ? 's' : ''} remaining on your current plan.`
        : null;

    return (
        <div className="bg-background-light dark:bg-background-dark font-display text-slate-900 dark:text-slate-100 min-h-screen">
            <main className="max-w-full max-w-[1280px] mx-auto px-4 sm:px-6 py-6 sm:py-8">
                <div className="mb-8">
                    <h1 className="text-slate-900 dark:text-white text-3xl sm:text-4xl font-black leading-tight tracking-[-0.033em]">
                        Upload Manuscript
                    </h1>
                    <p className="text-slate-500 dark:text-slate-400 text-base sm:text-lg mt-2">
                        {isLoggedIn
                            ? 'Transform your research into a publication-ready document in minutes.'
                            : 'Professional academic formatting in seconds. No account required to start.'}
                    </p>
                </div>

                <div className="mb-7 mt-4">
                    {quotaWarning && (
                        <div className="p-4 mb-4 bg-orange-50 border border-orange-200 text-orange-800 dark:bg-orange-900/30 dark:border-orange-800 dark:text-orange-300 rounded-xl flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <AlertTriangle />
                                <span className="font-medium">{quotaWarning}</span>
                            </div>
                        </div>
                    )}
                    {/* Fixed CategoryTabs props */}
                    <CategoryTabs 
                        activeCategory={category} 
                        onCategoryChange={(cat) => {
                            setCategory(cat);
                            setTemplate(cat);
                        }} 
                    />
                    <TemplateSelector
                        category={category}
                        template={template}
                        isProcessing={isProcessing}
                        file={file}
                        formatFileSize={formatFileSize}
                        onCategoryChange={(cat) => {
                            setCategory(cat);
                            setTemplate(cat);
                        }}
                    />
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                    <div className="lg:col-span-7 flex flex-col gap-6">
                        {/* 1. Document Source */}
                        <div className="bg-white rounded-xl border border-slate-200 dark:border-slate-700/70 p-6 shadow-sm hover:shadow-md dark:hover:shadow-none transition-shadow">
                            <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                                <FileUp className="text-primary" />
                                1. Document Source
                            </h2>
                            <div
                                id="upload-zone"
                                className={`flex flex-col items-center gap-6 rounded-xl border-2 border-dashed px-6 py-12 transition-all relative group/zone ${file ? 'border-primary bg-primary/5' : 'border-slate-300 dark:border-slate-700 bg-slate-50/50 '
                                    } hover:border-primary hover:bg-slate-50 dark:hover:bg-white/5`}
                                onDragOver={(e) => e.preventDefault()}
                                onDrop={handleDrop}
                            >
                                <div className="flex flex-col items-center gap-4 relative z-10">
                                    <div className={`w-16 h-16 rounded-full flex items-center justify-center transition-all duration-300 ${file ? 'bg-primary text-white scale-110' : 'bg-primary/10 text-primary group-hover/zone:scale-110'}`}>
                                        {isProcessing ? <RefreshCw className="w-10 h-10 animate-spin" /> : <CloudUpload className="w-10 h-10" />}
                                    </div>
                                    <div className="text-center">
                                        <p className="text-slate-900 dark:text-white text-lg font-bold">
                                            {file ? 'Manuscript Ready' : 'Drag and drop your manuscript here'}
                                        </p>
                                        <div className="text-slate-500 dark:text-slate-400 text-sm mt-1 flex items-center justify-center gap-2">
                                            {file ? (
                                                <div className="flex items-center gap-2 px-3 py-1 bg-white dark:bg-slate-800 rounded-full border border-slate-200 dark:border-slate-700 shadow-sm">
                                                    <span className="truncate max-w-[200px]">{file.name}</span>
                                                    <span className="text-slate-400 text-xs">({formatFileSize(file.size)})</span>
                                                    <button 
                                                        onClick={(e) => { e.stopPropagation(); setFile(null); setFileError(null); }} 
                                                        className="hover:text-red-500 dark:hover:text-red-400 transition-colors flex items-center p-0.5" 
                                                    >
                                                        <X className="text-sm" />
                                                    </button>
                                                </div>
                                            ) : 'Supported formats: DOCX, PDF, TEX, TXT, HTML, MD, DOC (Max 50MB)'}
                                        </div>
                                        {fileError && <p className="text-red-500 text-xs mt-2 font-bold animate-bounce">{fileError}</p>}
                                    </div>
                                </div>
                                <input
                                    id="file-upload"
                                    type="file"
                                    ref={fileInputRef}
                                    className="sr-only"
                                    onChange={handleFileChange}
                                    accept={ACCEPTED_FORMATS}
                                    disabled={isProcessing}
                                />
                                <label
                                    htmlFor="file-upload"
                                    className={`flex w-full sm:w-auto min-w-[140px] cursor-pointer items-center justify-center overflow-hidden rounded-lg h-11 px-6 bg-primary text-white text-sm font-bold tracking-wide shadow-md hover:bg-blue-700 transition-all ${isProcessing ? 'opacity-50 cursor-not-allowed' : 'active:scale-95'}`}
                                >
                                    {isProcessing ? 'Locked' : file ? 'Change File' : 'Browse Files'}
                                </label>
                            </div>
                        </div>

                        {/* 2. Processing Parameters */}
                        <FormattingOptions
                            addPageNumbers={formattingOptions.addPageNumbers}
                            setAddPageNumbers={(val) => updateFormattingOption('addPageNumbers', val)}
                            addBorders={formattingOptions.addBorders}
                            setAddBorders={(val) => updateFormattingOption('addBorders', val)}
                            addCoverPage={formattingOptions.addCoverPage}
                            setAddCoverPage={(val) => updateFormattingOption('addCoverPage', val)}
                            generateTOC={formattingOptions.generateTOC}
                            setGenerateTOC={(val) => updateFormattingOption('generateTOC', val)}
                            pageSize={formattingOptions.pageSize}
                            setPageSize={(val) => updateFormattingOption('pageSize', val)}
                            isProcessing={isProcessing}
                            progress={progress}
                            file={file}
                            onProcess={startUpload}
                        />

                        {/* Fast Mode Toggle */}
                        <div className="bg-white rounded-xl border border-slate-200 dark:border-slate-700/70 p-6 shadow-sm hover:shadow-md dark:hover:shadow-none transition-shadow">
                            <FastModeToggle
                                fastMode={formattingOptions.fastMode}
                                setFastMode={(val) => updateFormattingOption('fastMode', val)}
                                disabled={isProcessing || progress === 100}
                            />
                        </div>

                        {isProcessing && (
                            <button
                                onClick={cancelUpload}
                                className="w-full mt-3 bg-red-50 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/40 text-red-600 dark:text-red-400 font-bold py-3 rounded-xl border border-red-200 dark:border-red-800 flex items-center justify-center gap-2 transition-all"
                            >
                                <XCircle className="text-lg" />
                                Cancel Processing
                            </button>
                        )}
                    </div>

                    {/* Progress Sidebar */}
                    <div className="lg:col-span-5">
                        <ProcessingStepper
                            isProcessing={isProcessing}
                            progress={progress}
                            statusMessage={statusMessage}
                            currentStep={currentStep}
                            steps={STEPS}
                        />
                    </div>
                </div>
            </main>

        </div>
    );
}

export default function Upload() {
    return (
        <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div></div>}>
            <UploadContent />
        </Suspense>
    );
}
