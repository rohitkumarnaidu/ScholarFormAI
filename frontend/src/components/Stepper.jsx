// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, Loader2, XCircle } from 'lucide-react';

/**
 * Static fallback stages — used when the parent doesn't provide a stages prop.
 */
const STATIC_STEPS = [
    { id: 'uploading',  title: 'Uploading Manuscript',   desc: 'Source file received and secured.' },
    { id: 'converting', title: 'Converting Format',       desc: 'Extracting semantic layers...' },
    { id: 'parsing',    title: 'Parsing Structure',       desc: 'Identifying headers and sections...' },
    { id: 'analyzing',  title: 'Analyzing Content (AI)', desc: 'Classifying academic intent...' },
    { id: 'validating', title: 'Journal Validation',      desc: 'Checking against style guide...' },
    { id: 'formatting', title: 'Final Formatting',        desc: 'Applying template rules...' },
    { id: 'exporting',  title: 'Exporting Result',        desc: 'Generating output files...' },
];

/**
 * Stepper — accepts either:
 *   - stages: array from backend  { id, title, desc, status:'pending'|'running'|'success'|'failed', progress? }
 *   - activeStep: numeric index (legacy fallback)
 * Falls back to STATIC_STEPS when no stages are provided.
 */
export default function Stepper({ activeStep = 0, stages }) {
    // Normalise: if backend stages provided, map them; otherwise build from static list + activeStep
    const steps = stages
        ? stages.map((s) => {
              // Normalise status to lowercase so backend values like PROCESSING, COMPLETED,
              // FAILED, RUNNING, PENDING all map correctly to the display logic below.
              const rawStatus = String(s.status || 'pending').toLowerCase();
              // Accept common backend aliases → canonical lowercase names
              const status =
                  rawStatus === 'processing' || rawStatus === 'in_progress' ? 'running'
                  : rawStatus === 'completed' || rawStatus === 'completed_with_warnings' || rawStatus === 'done'
                                                                         ? 'success'
                  : rawStatus === 'error' || rawStatus === 'cancelled' || rawStatus === 'canceled'
                                                                         ? 'failed'
                  : ['running', 'success', 'failed', 'pending'].includes(rawStatus)
                                                                         ? rawStatus
                                                                         : 'pending';
              return {
                  id: s.id || s.name,
                  title: s.title || s.name,
                  desc: s.desc || s.description || '',
                  status,
                  progress: s.progress ?? null,
              };
          })
        : STATIC_STEPS.map((s, i) => ({
              ...s,
              status: i < activeStep ? 'success' : i === activeStep ? 'running' : 'pending',
              progress: null,
          }));

    return (
        <div className="p-4 sm:p-6 space-y-2" role="list" aria-label="Processing steps">
            <AnimatePresence>
                {steps.map((step, index) => {
                    const isActive    = step.status === 'running';
                    const isCompleted = step.status === 'success';
                    const isFailed    = step.status === 'failed';
                    const isPending   = step.status === 'pending';

                    // When using static fallback, hide anything more than one step ahead
                    if (!stages && isPending && index > activeStep + 1) return null;

                    return (
                        <motion.div
                            key={step.id}
                            role="listitem"
                            aria-current={isActive ? 'step' : undefined}
                            aria-label={`Step ${index + 1}: ${step.title} – ${isCompleted ? 'completed' : isActive ? 'in progress' : isFailed ? 'failed' : 'pending'}`}
                            initial={{ opacity: 0, y: 10, height: 0 }}
                            animate={{ opacity: isPending ? 0.5 : 1, y: 0, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            transition={{ duration: 0.3 }}
                            className={`flex items-start gap-4 overflow-hidden relative ${isActive ? 'pb-2' : ''}`}
                        >
                            <div className="flex flex-col items-center z-10">
                                <motion.div
                                    className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 border-2 transition-colors bg-white dark:bg-slate-900
                                        ${isCompleted ? 'text-green-500 border-green-500 bg-green-50 dark:bg-green-900/20' : ''}
                                        ${isActive    ? 'text-primary border-primary shadow-sm shadow-primary/20 bg-blue-50 dark:bg-blue-900/20' : ''}
                                        ${isFailed    ? 'text-red-500 border-red-400 bg-red-50 dark:bg-red-900/20' : ''}
                                        ${isPending   ? 'text-slate-300 dark:text-slate-600 border-slate-200 dark:border-slate-700' : ''}
                                    `}
                                    animate={isActive ? { scale: [1, 1.05, 1] } : {}}
                                    transition={isActive ? { repeat: Infinity, duration: 2 } : {}}
                                >
                                    {isCompleted ? (
                                        <CheckCircle2 className="w-4 h-4" />
                                    ) : isActive ? (
                                        <Loader2 className="w-4 h-4 animate-spin text-primary" />
                                    ) : isFailed ? (
                                        <XCircle className="w-4 h-4" />
                                    ) : (
                                        <span className="text-xs font-bold">{index + 1}</span>
                                    )}
                                </motion.div>
                                {index < steps.length - 1 && (!isPending || index === activeStep + 1 || stages) && (
                                    <div className="w-0.5 h-full min-h-[32px] mt-2 mb-2 bg-slate-100 dark:bg-slate-800 relative rounded-full overflow-hidden">
                                        <motion.div
                                            className={`absolute top-0 w-full ${isFailed ? 'bg-red-400' : 'bg-green-500'}`}
                                            initial={{ height: 0 }}
                                            animate={{ height: isCompleted || isFailed ? '100%' : '0%' }}
                                            transition={{ duration: 0.5 }}
                                        />
                                    </div>
                                )}
                            </div>

                            <div className="pt-1 w-full pb-4 relative">
                                <p className={`text-sm font-bold transition-colors ${
                                    isActive    ? 'text-primary'
                                    : isCompleted ? 'text-slate-700 dark:text-slate-300'
                                    : isFailed  ? 'text-red-600 dark:text-red-400'
                                    : 'text-slate-500 dark:text-slate-400'
                                }`}>
                                    {step.title}
                                </p>
                                <AnimatePresence>
                                    {(isActive || isCompleted || isFailed) && (
                                        <motion.p
                                            initial={{ opacity: 0, height: 0 }}
                                            animate={{ opacity: 1, height: 'auto' }}
                                            exit={{ opacity: 0, height: 0 }}
                                            className={`text-xs mt-1 ${isFailed ? 'text-red-500 dark:text-red-400' : 'text-slate-500 dark:text-slate-400'}`}
                                        >
                                            {isFailed   ? 'Step failed'
                                             : isActive  ? step.desc || 'Processing active layer...'
                                             : 'Completed successfully'}
                                        </motion.p>
                                    )}
                                </AnimatePresence>

                                {/* Per-step progress bar (when backend provides %) */}
                                {isActive && step.progress !== null && (
                                    <div className="mt-2 h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                                        <motion.div
                                            className="h-full rounded-full bg-primary"
                                            initial={{ width: 0 }}
                                            animate={{ width: `${step.progress}%` }}
                                            transition={{ duration: 0.4 }}
                                        />
                                    </div>
                                )}

                                <AnimatePresence>
                                    {/* Only show fallback spinner when NO progress data at all (null, not 0) */}
                                    {isActive && step.progress == null && (
                                        <motion.div
                                            initial={{ opacity: 0, scale: 0.95, height: 0 }}
                                            animate={{ opacity: 1, scale: 1, height: 'auto' }}
                                            exit={{ opacity: 0, height: 0 }}
                                            className="mt-3 p-3 bg-slate-50 dark:bg-slate-800/50 rounded-lg border border-slate-100 dark:border-slate-800 text-xs text-slate-600 dark:text-slate-400 flex items-center gap-2"
                                        >
                                            <Loader2 className="w-3 h-3 animate-spin text-primary" />
                                            <span className="animate-pulse">Live activity stream starting...</span>
                                        </motion.div>
                                    )}
                                </AnimatePresence>
                            </div>
                        </motion.div>
                    );
                })}
            </AnimatePresence>
        </div>
    );
}
