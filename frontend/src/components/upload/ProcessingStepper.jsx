// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import React, { memo } from 'react';
import { Check, Info, RefreshCw } from 'lucide-react';

const ProcessingStepper = memo(function ProcessingStepper({
    isProcessing,
    progress,
    statusMessage,
    currentStep,
    steps,
}) {
    return (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700/70 shadow-sm lg:sticky lg:top-24 hover:shadow-md dark:hover:shadow-none transition-shadow">
            <div className="p-6 border-b border-slate-100 dark:border-slate-700/60">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-bold text-slate-900 dark:text-white">Processing Status</h2>
                    <span className={`text-xs font-bold uppercase tracking-widest px-2 py-1 rounded transition-colors ${isProcessing ? 'bg-primary/10 text-primary animate-pulse' : 'bg-slate-100 text-slate-500'
                        }`}>
                        {isProcessing ? 'Processing' : 'Standby'}
                    </span>
                </div>
                <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-2 overflow-hidden">
                    <div
                        className="bg-primary h-full transition-all duration-500 ease-out"
                        style={{ width: `${progress}%` }}
                    ></div>
                </div>
                <div className="flex justify-between mt-2">
                    <span className="text-xs text-slate-500 truncate max-w-[200px]" title={statusMessage}>
                        {statusMessage}
                    </span>
                    <span className="text-xs font-bold text-primary">{Math.round(progress)}%</span>
                </div>
            </div>

            <div className="p-5 sm:p-6 space-y-5 sm:space-y-6">
                {steps.map((step) => {
                    const isStepCompleted = currentStep > step.id || progress === 100;
                    const isStepActive = currentStep === step.id && isProcessing;
                    const isPending = currentStep < step.id;

                    return (
                        <div key={step.id} className={`flex items-start gap-3 sm:gap-4 transition-opacity duration-500 ${isPending ? 'opacity-50' : 'opacity-100'}`}>
                            <div className="flex flex-col items-center">
                                <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 border-2 transition-all ${isStepCompleted ? 'bg-green-100 border-green-100 text-green-600' :
                                    isStepActive ? 'bg-primary/20 border-primary text-primary' :
                                        'bg-slate-100 dark:bg-slate-800 border-transparent text-slate-400'
                                    }`}>
                                    {isStepCompleted ? (
                                        <Check className="text-sm font-bold" />
                                    ) : isStepActive ? (
                                        <div className="w-2 h-2 bg-primary rounded-full animate-pulse"></div>
                                    ) : (
                                        <span className="text-xs font-bold">{step.id}</span>
                                    )}
                                </div>
                                {step.id < steps.length && (
                                    <div className={`w-0.5 h-8 mt-2 transition-colors duration-500 ${isStepCompleted ? 'bg-green-200 dark:bg-green-900' : 'bg-slate-200 dark:bg-white/10'}`}></div>
                                )}
                            </div>
                            <div className="pt-1">
                                <p className={`text-sm font-bold leading-snug transition-colors ${isStepActive ? 'text-primary' : 'text-slate-900 dark:text-white'}`}>
                                    {step.title}
                                </p>
                                <p className="text-xs text-slate-500 mt-1">
                                    {isStepCompleted ? 'Completed' : isStepActive ? step.desc : 'Pending...'}
                                </p>
                            </div>
                        </div>
                    );
                })}
            </div>

            <div className="p-6 bg-slate-50 dark:bg-slate-900/50 rounded-b-xl flex justify-center">
                <p className="text-xs text-slate-400 flex items-center gap-1 italic">
                    {isProcessing ? <RefreshCw className="text-[14px]" /> : <Info className="text-[14px]" />}
                    {isProcessing ? 'Live updates from server...' : 'Ready to process'}
                </p>
            </div>
        </div>
    );
});

ProcessingStepper.displayName = 'ProcessingStepper';

export default ProcessingStepper;
