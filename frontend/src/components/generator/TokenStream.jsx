// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, ChevronDown, ChevronRight } from 'lucide-react';
import { supabase } from '../../lib/supabaseClient';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const WORD_FLUSH_INTERVAL = 40;

const SectionHeader = ({ section, index, isCompleted, isExpanded, onToggle, isActive }) => (
  <motion.div 
    initial={{ opacity: 0, x: -20 }}
    animate={{ opacity: 1, x: 0 }}
    className="flex items-center gap-2 group cursor-pointer sticky top-0 bg-white dark:bg-zinc-950 py-2 z-10"
    onClick={onToggle}
  >
    <button className="p-1 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300">
      {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
    </button>
    
    <div className="flex items-center justify-center w-6 h-6 rounded-full bg-zinc-100 dark:bg-zinc-800 text-xs font-medium text-zinc-600 dark:text-zinc-400">
      {index + 1}
    </div>
    
    <h3 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100 flex-1">
      {section.title}
    </h3>

    {isCompleted ? (
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: "spring", stiffness: 300, damping: 20 }}
      >
        <CheckCircle2 className="w-5 h-5 text-emerald-500" />
      </motion.div>
    ) : (
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium text-indigo-500 animate-pulse">
          {isActive ? 'Writing...' : 'Queued'}
        </span>
      </div>
    )}
  </motion.div>
);

const TokenStream = ({ sessionId, isGenerating, initialSections = [] }) => {
  const [sections, setSections] = useState([]);
  const [activeSectionId, setActiveSectionId] = useState(null);
  const [expandedSections, setExpandedSections] = useState({});
  const containerRef = useRef(null);
  const bottomRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const wordQueueRef = useRef(new Map());
  const flushTimerRef = useRef(null);
  const eventSourceRef = useRef(null);

  const resetStreamState = useCallback(() => {
    setSections([]);
    setActiveSectionId(null);
    setExpandedSections({});
    wordQueueRef.current = new Map();
  }, []);

  // Reset state when session changes
  useEffect(() => {
    if (!sessionId) {
      resetStreamState();
    } else {
      resetStreamState();
    }
  }, [sessionId, resetStreamState]);

  useEffect(() => {
    if (!initialSections || initialSections.length === 0) return;
    if (isGenerating) return;
    setSections(initialSections);
    const expanded = {};
    initialSections.forEach(section => {
      expanded[section.id] = true;
    });
    setExpandedSections(expanded);
    setActiveSectionId(null);
  }, [initialSections, isGenerating]);

  // Auto-scroll to bottom when new content arrives
  useEffect(() => {
    if (bottomRef.current && isGenerating) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [sections, isGenerating]);

  const enqueueWords = useCallback((sectionId, text) => {
    if (!text) return;
    const tokens = String(text).split(/(\s+)/).filter(Boolean);
    if (!tokens.length) return;
    const existing = wordQueueRef.current.get(sectionId) || [];
    wordQueueRef.current.set(sectionId, [...existing, ...tokens]);
  }, []);

  useEffect(() => {
    const hasPendingTokens = () => {
      for (const queue of wordQueueRef.current.values()) {
        if (queue.length) return true;
      }
      return false;
    };

    if (!isGenerating && !hasPendingTokens()) {
      if (flushTimerRef.current) {
        clearInterval(flushTimerRef.current);
        flushTimerRef.current = null;
      }
      return;
    }

    if (!flushTimerRef.current) {
      flushTimerRef.current = setInterval(() => {
        let didUpdate = false;
        setSections(prev => {
          const next = prev.map(section => {
            const queue = wordQueueRef.current.get(section.id);
            if (queue && queue.length) {
              const token = queue.shift();
              didUpdate = true;
              const content = `${section.content || ''}${token}`;
              return {
                ...section,
                content,
                wordCount: content.trim() ? content.trim().split(/\s+/).length : 0
              };
            }
            return section;
          });
          return didUpdate ? next : prev;
        });
        if (!isGenerating && !hasPendingTokens() && flushTimerRef.current) {
          clearInterval(flushTimerRef.current);
          flushTimerRef.current = null;
        }
      }, WORD_FLUSH_INTERVAL);
    }

    return () => {
      if (flushTimerRef.current) {
        clearInterval(flushTimerRef.current);
        flushTimerRef.current = null;
      }
    };
  }, [isGenerating]);

  useEffect(() => {
    if (!sessionId) return;

    let retryCount = 0;
    const maxRetries = 5;
    let isMounted = true;

    const connectSSE = async () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      if (!isMounted) return;

      let authToken = null;
      if (supabase) {
        try {
          const { data: { session } } = await supabase.auth.getSession();
          authToken = session?.access_token;
        } catch (err) {
          console.error("[TokenStream] Failed to get auth session:", err);
        }
      }

      const url = new URL(`${API_BASE_URL}/api/v1/generator/sessions/${sessionId}/events`);
      if (authToken) {
        url.searchParams.set('token', authToken);
      }

      const eventSource = new EventSource(url.toString(), { withCredentials: true });
      eventSourceRef.current = eventSource;

      const handleWritingChunk = (event) => {
        try {
          const data = JSON.parse(event.data);
          const payload = data.payload || {};
          const stage = data.stage || payload.stage;
          const isRewrite = stage === 'rewriting' || payload.reset === true;
          const sectionTitle = payload.section || payload.section_name || payload.title;
          if (!sectionTitle) return;
          const sectionId = `section-${sectionTitle.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`;
          setSections(prev => {
            const exists = prev.some(s => s.id === sectionId);
            if (exists) {
              if (isRewrite) {
                wordQueueRef.current.set(sectionId, []);
                return prev.map(s => s.id === sectionId ? { ...s, content: '', isCompleted: false, wordCount: 0 } : s);
              }
              return prev;
            }
            return [
              ...prev,
              {
                id: sectionId,
                title: sectionTitle,
                content: '',
                isCompleted: false,
                wordCount: 0
              }
            ];
          });
          setActiveSectionId(sectionId);
          setExpandedSections(prev => ({ ...prev, [sectionId]: true }));
          enqueueWords(sectionId, payload.content);
        } catch (error) {
          console.error("Error parsing writing_chunk SSE data:", error);
        }
      };

      const handleStageUpdate = (event) => {
        try {
          const data = JSON.parse(event.data);
          const payload = data.payload || {};
          const stage = data.stage || payload.stage;
          const message = payload.message || data.message || '';
          const sectionTitle = payload.section;
          const messageLower = message.toLowerCase();
          if ((stage === 'writing' || stage === 'rewriting') && sectionTitle && (messageLower.includes('completed') || messageLower.includes('rewritten'))) {
            const sectionId = `section-${sectionTitle.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`;
            setSections(prev => prev.map(s => s.id === sectionId ? { ...s, isCompleted: true } : s));
            setActiveSectionId(null);
          }
          if (stage === 'done' || payload.status === 'completed') {
            setSections(prev => prev.map(s => ({ ...s, isCompleted: true })));
            setActiveSectionId(null);
          }
        } catch (error) {
          console.error("Error parsing stage_update SSE data:", error);
        }
      };

      eventSource.addEventListener('writing_chunk', handleWritingChunk);
      eventSource.addEventListener('stage_update', handleStageUpdate);

      eventSource.onerror = (error) => {
        console.error("SSE Error:", error);
        eventSource.close();
        if (retryCount < maxRetries && isMounted) {
          retryCount += 1;
          const delay = Math.min(3000 * retryCount, 15000);
          reconnectTimeoutRef.current = setTimeout(connectSSE, delay);
        }
      };
    };

    connectSSE();

    return () => {
      isMounted = false;
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    };
  }, [sessionId, enqueueWords]);

  const toggleSection = (id) => {
    setExpandedSections(prev => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  if (!sections.length && !isGenerating) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-zinc-500 dark:text-zinc-400 p-8 text-center bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl">
        <div className="w-16 h-16 rounded-full bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center mb-4">
          <ChevronRight className="w-8 h-8 text-zinc-400" />
        </div>
        <p className="font-medium text-zinc-900 dark:text-zinc-100">Document Area</p>
        <p className="text-sm mt-1 max-w-sm">
          Approve the outline in the chat panel to begin writing your document.
        </p>
      </div>
    );
  }

  return (
    <div 
      ref={containerRef}
      className="h-full overflow-y-auto px-8 py-10 bg-white dark:bg-zinc-950 custom-scrollbar border border-zinc-200 dark:border-zinc-800 rounded-xl shadow-sm"
    >
      <div className="max-w-3xl mx-auto space-y-12">
        {sections.map((section, index) => (
          <motion.div key={section.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="relative">
            <SectionHeader 
              section={section} 
              index={index}
              isCompleted={section.isCompleted} 
              isExpanded={expandedSections[section.id]}
              onToggle={() => toggleSection(section.id)}
              isActive={activeSectionId === section.id}
            />
            
            <AnimatePresence initial={false}>
              {expandedSections[section.id] && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.3 }}
                  className="overflow-hidden"
                >
                  <div className="pt-4 pl-9 text-zinc-700 dark:text-zinc-300 leading-relaxed font-serif whitespace-pre-wrap">
                    {section.content}
                    {activeSectionId === section.id && (
                      <span className="inline-block w-2 bg-indigo-500 ml-1 h-5 align-middle animate-pulse" />
                    )}
                  </div>
                  
                  {/* Subtle word count */}
                  <div className="mt-2 pl-9 text-xs text-zinc-400 dark:text-zinc-500">
                    {section.wordCount} words
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        ))}
        
        {/* Invisible element to scroll to */}
        <div ref={bottomRef} className="h-4" />
      </div>
    </div>
  );
};

export default TokenStream;
