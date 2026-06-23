// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import React, { useState, useCallback, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { UploadCloud, File as FileIcon, AlertCircle, CheckCircle, Trash2 } from 'lucide-react';
import { getBuiltinTemplates } from '../../services/api.templates';

const ACCEPTED_FORMATS = {
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'application/pdf': ['.pdf'],
  'text/plain': ['.txt'],
  'text/markdown': ['.md'],
  'application/x-tex': ['.tex'],
  'application/vnd.oasis.opendocument.text': ['.odt'],
  'text/html': ['.html'],
  'application/rtf': ['.rtf']
};

const MAX_FILES = 6;
const MIN_FILES = 2;

async function computeSHA256(file) {
    const buffer = await file.arrayBuffer();
    const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

export default function MultiUploadPanel({ onStart }) {
    const [files, setFiles] = useState([]);
    const [templates, setTemplates] = useState([]);
    const [selectedTemplate, setSelectedTemplate] = useState('');
    const [globalError, setGlobalError] = useState('');

    useEffect(() => {
        getBuiltinTemplates()
            .then(res => {
                if(res && res.length) {
                    setTemplates(res);
                    setSelectedTemplate(res[0].id || res[0].slug || '');
                }
            })
            .catch(err => console.error("Could not fetch templates:", err));
    }, []);

    const onDrop = useCallback(async (acceptedFiles) => {
        setGlobalError('');
        
        if (files.length + acceptedFiles.length > MAX_FILES) {
            setGlobalError(`You can only upload up to ${MAX_FILES} files.`);
            return;
        }

        const newFiles = [...files];
        
        for (const file of acceptedFiles) {
            const hash = await computeSHA256(file);
            const isDuplicate = newFiles.some(f => f.hash === hash);
            
            newFiles.push({
                file,
                id: Math.random().toString(36).substring(7),
                name: file.name,
                size: file.size,
                status: isDuplicate ? 'error' : 'ready',
                error: isDuplicate ? 'Duplicate detected' : null,
                hash,
                progress: isDuplicate ? 0 : 100 // Pre-filled progress for UI consistency
            });
        }
        
        setFiles(newFiles);
    }, [files]);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: ACCEPTED_FORMATS,
        maxFiles: MAX_FILES
    });

    const removeFile = (id) => {
        setFiles(files.filter(f => f.id !== id));
        setGlobalError('');
    };

    const handleStart = () => {
        const readyFiles = files.filter(f => f.status === 'ready');
        if (readyFiles.length < MIN_FILES) {
            setGlobalError(`Please upload at least ${MIN_FILES} valid files.`);
            return;
        }
        if (readyFiles.length > MAX_FILES) {
            setGlobalError(`Please upload no more than ${MAX_FILES} files.`);
            return;
        }
        
        onStart(readyFiles.map(f => f.file), selectedTemplate);
    };

    const validFileCount = files.filter(f => f.status === 'ready').length;
    const canStart = validFileCount >= MIN_FILES && validFileCount <= MAX_FILES;

    return (
        <div className="w-full max-w-4xl mx-auto space-y-6">
            <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
                <div 
                    {...getRootProps()} 
                    className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors ${
                        isDragActive ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20' : 'border-slate-300 dark:border-slate-600 hover:border-indigo-400 dark:hover:border-indigo-500'
                    }`}
                >
                    <input {...getInputProps()} />
                    <UploadCloud className="mx-auto h-12 w-12 text-slate-400 mb-4" />
                    <h3 className="text-lg font-medium text-slate-900 dark:text-white mb-1">
                        Drag & Drop documents here
                    </h3>
                    <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
                        Upload {MIN_FILES} to {MAX_FILES} files (.pdf, .docx, .md, .txt)
                    </p>
                    <button className="bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 border border-slate-300 dark:border-slate-600 px-4 py-2 rounded-lg text-sm font-medium hover:bg-slate-50 dark:hover:bg-slate-700 transition">
                        Browse Files
                    </button>
                </div>

                {globalError && (
                    <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm rounded-lg flex items-center">
                        <AlertCircle className="w-4 h-4 mr-2" />
                        {globalError}
                    </div>
                )}
            </div>

            {files.length > 0 && (
                <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
                    <h4 className="text-sm font-semibold text-slate-900 dark:text-white mb-4 uppercase tracking-wider">
                        Uploaded Files ({files.length}/{MAX_FILES})
                    </h4>
                    <div className="space-y-3">
                        {files.map((file) => (
                            <div key={file.id} className="flex items-center p-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                                <FileIcon className="w-8 h-8 text-indigo-500 mr-3 shrink-0" />
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm font-medium text-slate-900 dark:text-white truncate">
                                        {file.name}
                                    </p>
                                    <div className="flex items-center text-xs text-slate-500 dark:text-slate-400 mt-1">
                                        <span>{(file.size / 1024 / 1024).toFixed(2)} MB</span>
                                        <span className="mx-2">•</span>
                                        {file.status === 'error' ? (
                                            <span className="text-red-500 flex items-center">
                                                <AlertCircle className="w-3 h-3 mr-1" /> {file.error}
                                            </span>
                                        ) : (
                                            <span className="text-green-600 dark:text-green-400 flex items-center">
                                                <CheckCircle className="w-3 h-3 mr-1" /> Ready
                                            </span>
                                        )}
                                    </div>
                                    {file.status !== 'error' && (
                                        <div className="h-1.5 w-full bg-slate-200 dark:bg-slate-700 rounded-full mt-2 overflow-hidden">
                                            <div 
                                                className="h-full bg-green-500 transition-all duration-300"
                                                style={{ width: `${file.progress}%` }}
                                            />
                                        </div>
                                    )}
                                </div>
                                <button
                                    onClick={() => removeFile(file.id)}
                                    className="ml-4 p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition"
                                >
                                    <Trash2 className="w-4 h-4" />
                                </button>
                            </div>
                        ))}
                    </div>

                    <div className="mt-8 border-t border-slate-200 dark:border-slate-700 pt-6">
                        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
                            <div className="w-full sm:w-1/2">
                                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                                    Target Template
                                </label>
                                <select 
                                    className="w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-lg py-2 px-3 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                                    value={selectedTemplate}
                                    onChange={(e) => setSelectedTemplate(e.target.value)}
                                >
                                    {templates.length > 0 ? (
                                        templates.map(t => (
                                            <option key={t.id || t.slug} value={t.id || t.slug}>
                                                {t.name}
                                            </option>
                                        ))
                                    ) : (
                                        <option value="default_academic">Academic Standard</option>
                                    )}
                                    {/* Fallback mock templates if API fails */}
                                    {templates.length === 0 && (
                                        <>
                                            <option value="ieee_journal">IEEE Journal</option>
                                            <option value="nature">Nature</option>
                                            <option value="apa7">APA 7th Edition</option>
                                        </>
                                    )}
                                </select>
                            </div>
                            
                            <button
                                onClick={handleStart}
                                disabled={!canStart}
                                className={`w-full sm:w-auto px-6 py-2.5 rounded-lg text-sm font-medium transition flex items-center justify-center ${
                                    canStart 
                                    ? 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm' 
                                    : 'bg-slate-100 dark:bg-slate-800 text-slate-400 dark:text-slate-500 cursor-not-allowed'
                                }`}
                            >
                                Start Synthesis
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
