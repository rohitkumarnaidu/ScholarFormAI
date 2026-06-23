// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import React, { createContext, useState, useContext, useEffect } from 'react';


const DocumentContext = createContext();

export const useDocument = () => useContext(DocumentContext);

const toFileMetadata = (file) => ({
    originalFileName: file?.name || '',
    originalFileSize: file?.size || 0,
    originalFileType: file?.type || '',
});

export const DocumentProvider = ({ children }) => {
    const [job, setJob] = useState(null);
    const [processing, setProcessing] = useState(false);

    useEffect(() => {
        const savedJob = sessionStorage.getItem('scholarform_currentJob');
        if (savedJob) {
            try {
                const parsedJob = JSON.parse(savedJob);
                setJob(parsedJob);
            } catch (e) {
                console.error("Failed to hydrate job:", e);
                sessionStorage.removeItem('scholarform_currentJob');
            }
        }
    }, []);

    useEffect(() => {
        if (job) {
            sessionStorage.setItem('scholarform_currentJob', JSON.stringify(job));
        } else {
            sessionStorage.removeItem('scholarform_currentJob');
        }
    }, [job]);

    const addToHistory = (newJob) => {
        setJob(newJob);
    };

    const startProcessing = () => {
        setProcessing(true);
        setJob(null);
    };

    const finishProcessing = (result, file, template, options) => {
        setProcessing(false);
        const fileMetadata = toFileMetadata(file);
        const newJob = {
            id: result.job_id || Date.now().toString(),
            timestamp: new Date().toISOString(),
            status: 'completed',
            ...fileMetadata,
            template: template,
            options: options,
            result: result.validation_result,
            outputPath: result.output_path,
            flags: result.flags
        };
        setJob(newJob);
        addToHistory(newJob);
    };

    const failProcessing = (error) => {
        setProcessing(false);
        setJob({ status: 'failed', error: error.message });
    };

    return (
        <DocumentContext.Provider value={{
            job,
            setJob,
            processing,
            startProcessing,
            finishProcessing,
            failProcessing
        }}>
            {children}
        </DocumentContext.Provider>
    );
};
