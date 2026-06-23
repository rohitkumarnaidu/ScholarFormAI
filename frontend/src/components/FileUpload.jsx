// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { useRef, useState } from 'react';

const ACCEPTED_FORMATS = '.docx,.pdf,.tex,.txt,.html,.htm,.md,.markdown,.doc';
const ACCEPTED_EXTENSIONS = ['.docx', '.pdf', '.tex', '.txt', '.html', '.htm', '.md', '.markdown', '.doc'];
const MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024;

const isAllowedUploadFile = (selectedFile) => {
    if (!selectedFile?.name) {
        return false;
    }

    const fileExtension = selectedFile.name
        .substring(selectedFile.name.lastIndexOf('.'))
        .toLowerCase();

    return (
        ACCEPTED_EXTENSIONS.includes(fileExtension) &&
        selectedFile.size > 0 &&
        selectedFile.size <= MAX_UPLOAD_SIZE_BYTES
    );
};

export default function FileUpload({ onFileSelect }) {
    const fileInputRef = useRef(null);
    const [dragActive, setDragActive] = useState(false);
    const [fileName, setFileName] = useState(null);
    const [validationError, setValidationError] = useState('');

    const validateAndSelect = (file) => {
        if (!isAllowedUploadFile(file)) {
            setValidationError('Unsupported file format. Please upload: DOCX, PDF, TEX, TXT, HTML, MD, or DOC.');
            return;
        }

        setValidationError('');
        setFileName(file.name);
        onFileSelect(file);
    };

    const handleDrag = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true);
        } else if (e.type === "dragleave") {
            setDragActive(false);
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            validateAndSelect(e.dataTransfer.files[0]);
        }
    };

    const handleChange = (e) => {
        e.preventDefault();
        if (e.target.files && e.target.files[0]) {
            validateAndSelect(e.target.files[0]);
        }
    };

    const onButtonClick = () => {
        fileInputRef.current.click();
    };

    return (
        <div
            role="button"
            tabIndex="0"
            aria-label="Upload manuscript"
            className={`flex flex-col items-center gap-6 rounded-xl border-2 border-dashed px-6 py-12 transition-colors bg-slate-50/50 dark:bg-slate-800/50 focus:ring-2 focus:ring-primary focus:outline-none ${dragActive ? 'border-primary bg-blue-50 dark:bg-blue-900/10' : 'border-slate-300 dark:border-slate-700 hover:border-primary'}`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={onButtonClick}
            onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onButtonClick();
                }
            }}
        >
            <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                onChange={handleChange}
                accept={ACCEPTED_FORMATS}
            />
            <div className="flex flex-col items-center gap-4">
                <div className={`w-16 h-16 rounded-full flex items-center justify-center text-primary ${fileName ? 'bg-green-100 text-green-600' : 'bg-primary/10'}`}>
                    <span className="material-symbols-outlined text-4xl" aria-hidden="true">
                        {fileName ? 'check_circle' : 'cloud_upload'}
                    </span>
                </div>
                <div className="text-center">
                    <p className="text-slate-900 dark:text-white text-lg font-bold">
                        {fileName ? fileName : 'Drag and drop your manuscript here'}
                    </p>
                    <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">Supported formats: DOCX, PDF, TEX, TXT, HTML/HTM, MD/MARKDOWN, DOC (Max 50MB)</p>
                    {validationError ? (
                        <p className="text-red-600 text-xs mt-2">{validationError}</p>
                    ) : null}
                </div>
            </div>
            <button
                onClick={onButtonClick}
                className="flex min-w-[140px] cursor-pointer items-center justify-center overflow-hidden rounded-lg h-11 px-6 bg-primary text-white text-sm font-bold tracking-wide shadow-md hover:bg-blue-700 transition-all"
            >
                {fileName ? 'Change File' : 'Browse Files'}
            </button>
        </div>
    );
}
