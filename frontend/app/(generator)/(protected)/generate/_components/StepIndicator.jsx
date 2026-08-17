// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

export default function StepIndicator({ steps, currentStep }) {
    return (
        <div className="flex items-center justify-center mb-10">
            {steps.map((stepItem, index) => {
                const number = index + 1;
                const isDone = number < currentStep;
                const isCurrent = number === currentStep;

                return (
                    <div key={stepItem.label} className="flex items-center">
                        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition ${isDone ? 'text-green-400' : isCurrent ? 'text-primary-light bg-primary/10' : 'text-slate-600'}`}>
                            <span className="material-symbols-outlined text-sm">{isDone ? 'check_circle' : stepItem.icon}</span>
                            <span className="hidden sm:inline">{stepItem.label}</span>
                        </div>
                        {index < steps.length - 1 && (
                            <div className={`w-8 h-px mx-1 ${isDone ? 'bg-green-500/40' : 'bg-slate-300 dark:bg-white/10'}`} />
                        )}
                    </div>
                );
            })}
        </div>
    );
}
