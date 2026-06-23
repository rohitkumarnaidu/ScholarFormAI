// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Download, FileText, CheckCircle2, ShieldAlert, Award } from 'lucide-react';
import TokenStream from './TokenStream';

const QualityScoreBadge = React.memo(({ score }) => {
  if (!score) return null;
  const overallScore = score.overallScore ?? score.overall_score ?? score.overall ?? score.score;
  if (typeof overallScore !== 'number') return null;
  
  const isHigh = overallScore >= 85;
  const isMedium = overallScore >= 70 && overallScore < 85;
  
  const getColorClasses = () => {
    if (isHigh) return 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-400 dark:border-emerald-500/20';
    if (isMedium) return 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-500/10 dark:text-amber-400 dark:border-amber-500/20';
    return 'bg-red-50 text-red-700 border-red-200 dark:bg-red-500/10 dark:text-red-400 dark:border-red-500/20';
  };

  const getIcon = () => {
    if (isHigh) return <Award className="w-5 h-5 text-emerald-500" />;
    if (isMedium) return <CheckCircle2 className="w-5 h-5 text-amber-500" />;
    return <ShieldAlert className="w-5 h-5 text-red-500" />;
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`p-4 rounded-xl border flex items-center justify-between shadow-sm ${getColorClasses()}`}
    >
      <div className="flex items-center gap-3">
        {getIcon()}
        <div>
          <h4 className="font-semibold text-sm">Quality Analysis</h4>
          <p className="text-xs opacity-80 mt-0.5">
            {isHigh ? 'Excellent quality document' : isMedium ? 'Good with some potential improvements' : 'Review suggested before publishing'}
          </p>
        </div>
      </div>
      
      <div className="flex items-baseline gap-1">
        <span className="text-2xl font-bold">{overallScore}</span>
        <span className="text-sm font-medium opacity-60">/100</span>
      </div>
    </motion.div>
  );
});

QualityScoreBadge.displayName = 'QualityScoreBadge';

const DocumentBuildPane = React.memo(({ 
  sessionId, 
  stage, // 'idle', 'generating', 'complete'
  qualityScore,
  initialSections,
  onDownload 
}) => {
  return (
    <div className="flex flex-col h-full bg-zinc-50 dark:bg-zinc-900 border-l border-zinc-200 dark:border-zinc-800">
      
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950">
        <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
          <FileText className="w-4 h-4 text-zinc-500" />
          Live Document
        </h2>
        
        <div className="flex items-center gap-2">
          {stage === 'generating' && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-indigo-50 dark:bg-indigo-500/10 text-xs font-medium text-indigo-700 dark:text-indigo-400 border border-indigo-100 dark:border-indigo-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse"></span>
              Generating
            </span>
          )}
          
          {stage === 'complete' && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 dark:bg-emerald-500/10 text-xs font-medium text-emerald-700 dark:text-emerald-400 border border-emerald-100 dark:border-emerald-500/20">
              <CheckCircle2 className="w-3.5 h-3.5" />
              Complete
            </span>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-hidden relative">
        <TokenStream sessionId={sessionId} isGenerating={stage === 'generating'} initialSections={initialSections} />
        
        {/* Overlay for Idle State */}
        <AnimatePresence>
          {stage === 'idle' && (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-zinc-50/80 dark:bg-zinc-900/80 backdrop-blur-sm"
            >
              <div className="w-16 h-16 rounded-2xl bg-white dark:bg-zinc-800 flex items-center justify-center shadow-lg shadow-zinc-200/50 dark:shadow-none mb-4 border border-zinc-100 dark:border-zinc-700">
                <FileText className="w-8 h-8 text-zinc-400 dark:text-zinc-500" />
              </div>
              <p className="text-zinc-500 dark:text-zinc-400 font-medium">No active document</p>
              <p className="text-sm text-zinc-400 dark:text-zinc-500 mt-1">Start a new request in the chat</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Footer / Results Area */}
      <AnimatePresence>
        {stage === 'complete' && (
          <motion.div 
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            className="border-t border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 p-6 space-y-4"
          >
            {qualityScore && <QualityScoreBadge score={qualityScore} />}
            
            <div className="flex items-center gap-3 w-full">
              <button
                onClick={() => onDownload('docx')}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-sm font-medium transition-colors shadow-sm shadow-indigo-600/20"
              >
                <Download className="w-4 h-4" />
                Download DOCX
              </button>
              
              <button
                onClick={() => onDownload('pdf')}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-white dark:bg-zinc-900 border border-zinc-300 dark:border-zinc-700 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-zinc-800 rounded-xl text-sm font-medium transition-colors shadow-sm"
              >
                <Download className="w-4 h-4" />
                Download PDF
              </button>
            </div>
            
            <div className="text-center">
              <p className="text-xs text-zinc-500 dark:text-zinc-400">
                Need changes? Ask the agent in the chat to rewrite specific sections.
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
});

DocumentBuildPane.displayName = 'DocumentBuildPane';

export default DocumentBuildPane;
