// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import React from 'react';
import { motion } from 'framer-motion';
import { CheckCircle, Circle, AlertCircle, Loader2 } from 'lucide-react';

const EXPECTED_STAGES = [
    'Upload Validation',
    'Document Extraction',
    'Embedding',
    'Cross-Document Analysis',
    'Synthesis Planning',
    'Content Generation',
    'Citation Insertion',
    'Template Rendering'
];

export default function SynthesisStageTimeline({ stages = [], currentStage = '' }) {
    
    // Map current stages from backend to the expected order to maintain a consistent UI
    const stageMap = {};
    stages.forEach(s => {
        stageMap[s.name] = s;
    });

    return (
        <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6 h-full overflow-y-auto">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-6">
                Synthesis Progress
            </h3>
            
            <div className="relative space-y-8 before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-slate-200 dark:before:via-slate-700 before:to-transparent">
                {EXPECTED_STAGES.map((stageName, index) => {
                    const stageData = stageMap[stageName];
                    const isDone = stageData?.status === 'done';
                    const isError = stageData?.status === 'error';
                    const isRunning = stageData?.status === 'running' || currentStage === stageName;
                    const isPending = !stageData && !isRunning && !isDone && !isError;
                    
                    // Let's also infer "done" if a subsequent stage is running
                    const hasPassed = stages.findIndex(s => s.name === stageName) !== -1;
                    const isActuallyDone = isDone || (hasPassed && !isRunning && !isError);

                    return (
                        <motion.div 
                            key={stageName}
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: index * 0.1 }}
                            className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group select-none"
                        >
                            {/* Icon marker */}
                            <div className={`flex items-center justify-center w-10 h-10 rounded-full border-4 border-white dark:border-slate-800 z-10 shrink-0 md:mx-auto shadow shrink-0
                                ${isActuallyDone ? 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400' : ''}
                                ${isRunning ? 'bg-indigo-100 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-400' : ''}
                                ${isError ? 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400' : ''}
                                ${isPending && !isActuallyDone && !isRunning && !isError ? 'bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500' : ''}
                            `}>
                                {isActuallyDone && !isError && <CheckCircle className="w-5 h-5" />}
                                {isRunning && <Loader2 className="w-5 h-5 animate-spin" />}
                                {isError && <AlertCircle className="w-5 h-5" />}
                                {(isPending && !isActuallyDone && !isRunning && !isError) && <Circle className="w-5 h-5" />}
                            </div>

                            {/* Content Card */}
                            <div className={`w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] p-4 rounded-xl border shadow-sm transition-all duration-200
                                ${isRunning ? 'border-indigo-200 dark:border-indigo-800 bg-indigo-50/50 dark:bg-indigo-900/10 scale-[1.02]' : 'border-slate-100 dark:border-slate-700 bg-white dark:bg-slate-800/50'}
                            `}>
                                <div className="flex justify-between items-center mb-1">
                                    <h4 className={`font-medium text-sm ${isRunning ? 'text-indigo-700 dark:text-indigo-300' : 'text-slate-800 dark:text-slate-200'}`}>
                                        {stageName}
                                    </h4>
                                    {stageData?.progress > 0 && stageData?.progress < 100 && (
                                        <span className="text-xs font-semibold text-indigo-600 dark:text-indigo-400">
                                            {stageData.progress}%
                                        </span>
                                    )}
                                </div>
                                <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-2">
                                    {isError ? stageData.message : (stageData?.message || (isActuallyDone ? 'Completed successfully' : isRunning ? 'Processing...' : 'Pending'))}
                                </p>
                                
                                {isRunning && stageData?.progress !== undefined && (
                                    <div className="mt-3 h-1.5 w-full bg-indigo-100 dark:bg-indigo-900/30 rounded-full overflow-hidden">
                                        <div 
                                            className="h-full bg-indigo-500 rounded-full transition-all duration-300 ease-out"
                                            style={{ width: `${Math.max(5, stageData.progress)}%` }}
                                        />
                                    </div>
                                )}
                            </div>
                        </motion.div>
                    );
                })}
            </div>
        </div>
    );
}
