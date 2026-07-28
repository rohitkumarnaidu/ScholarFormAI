// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import React, { useState, useEffect, useRef } from 'react';
import { Send, User, Bot, Loader2, Sparkles, AlertCircle, Square } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ModelSelector from './ModelSelector';
import { useAuth } from '@/context/AuthContext';

const formatSourceLabel = (source) => {
  if (!source) return 'Source';
  if (typeof source === 'string') return source;
  const name = source.source_doc || source.filename || source.name || 'Source';
  const section = source.section ? String(source.section) : '';
  if (!section) return name;
  const sectionLabel = section.toLowerCase().includes('section') ? section : `Section ${section}`;
  return `${name}, ${sectionLabel}`;
};

const SourceBadge = ({ source }) => (
  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-100 dark:border-indigo-500/20">
    <Sparkles className="w-3 h-3" />
    {formatSourceLabel(source)}
  </span>
);

const MessageBubble = React.memo(({ message }) => {
  const isUser = message.role === 'user';
  const isStatus = Boolean(message.isStatus);
  const renderStructuredContent = () => {
    if (typeof message.content === 'string') {
      return <div className="text-sm whitespace-pre-wrap leading-relaxed">{message.content}</div>;
    }
    const outline = message.outline || message.content?.outline || message.content;
    if (outline && Array.isArray(outline.sections)) {
      return (
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500">Outline</p>
          <div className="space-y-1">
            {outline.sections.map((section, idx) => (
              <div key={`${section.title}-${idx}`} className="flex items-center justify-between text-xs text-zinc-700 dark:text-zinc-300">
                <span className="truncate">{section.title || section.section || `Section ${idx + 1}`}</span>
                {section.expectedWordCount && (
                  <span className="text-[10px] text-zinc-400">{section.expectedWordCount} words</span>
                )}
              </div>
            ))}
          </div>
        </div>
      );
    }

    const quality = message.qualityScore || message.content?.quality || message.content;
    const overallScore = quality?.overallScore ?? quality?.overall_score;
    if (typeof overallScore === 'number') {
      return (
        <div className="flex items-center justify-between text-sm">
          <span className="font-medium text-zinc-700 dark:text-zinc-200">Quality Score</span>
          <span className="font-semibold text-emerald-600">{overallScore}/100</span>
        </div>
      );
    }

    return (
      <pre className="text-xs whitespace-pre-wrap text-zinc-600 dark:text-zinc-300">
        {JSON.stringify(message.content, null, 2)}
      </pre>
    );
  };
  
  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex gap-3 max-w-[85%] ${isUser ? 'ml-auto flex-row-reverse' : ''}`}
    >
      <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
        isUser 
          ? 'bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900' 
          : 'bg-indigo-100 dark:bg-indigo-500/20 text-indigo-600 dark:text-indigo-400'
      }`}>
        {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
      </div>
      
      <div className={`flex flex-col gap-1 ${isUser ? 'items-end' : 'items-start'}`}>
        <div className={`px-4 py-2.5 rounded-2xl ${
          isUser 
            ? 'bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 rounded-tr-sm' 
            : isStatus
              ? 'bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-300 rounded-tl-sm border border-amber-100 dark:border-amber-500/20'
              : 'bg-zinc-100 dark:bg-zinc-800/80 text-zinc-900 dark:text-zinc-100 rounded-tl-sm border border-zinc-200 dark:border-zinc-700/50'
        }`}>
          {renderStructuredContent()}
          
          {/* Source Attributions (if AI) */}
          {!isUser && message.sources && message.sources.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2 pt-2 border-t border-zinc-200 dark:border-zinc-700/50">
              {message.sources.map((src, idx) => (
                <SourceBadge key={idx} source={src} />
              ))}
            </div>
          )}
        </div>
        
        <span className="text-[10px] text-zinc-400 dark:text-zinc-500 px-1">
          {new Date(message.timestamp || message.created_at || Date.now()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>
    </motion.div>
  );
});

MessageBubble.displayName = 'MessageBubble';

const AgentChatPane = React.memo(({ 
  messages, 
  onSendMessage, 
  onStop,
  isTyping,
  error,
  selectedModel: externalModel,
  onModelChange 
}) => {
  const [input, setInput] = useState('');
  const [selectedModel, setSelectedModel] = useState(() => {
    if (externalModel) return externalModel;
    if (typeof window !== 'undefined') {
      try { return localStorage.getItem('scholarform_selected_model') || ''; } catch (e) { /* localStorage unavailable */ }
    }
    return '';
  });
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const { user } = useAuth();

  useEffect(() => {
    if (externalModel && externalModel !== selectedModel) {
      setSelectedModel(externalModel);
    }
  }, [externalModel, selectedModel]);

  const handleModelChange = (model) => {
    setSelectedModel(model);
    if (onModelChange) onModelChange(model);
    try { localStorage.setItem('scholarform_selected_model', model); } catch (e) { /* localStorage unavailable */ }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  useEffect(() => {
    // Auto-focus input when enabled
    if (!isTyping && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isTyping]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || isTyping) return;
    
    onSendMessage(input.trim());
    setInput('');
  };

  const handleKeyDown = (e) => {
    // Ctrl+Enter or Cmd+Enter to submit
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden shadow-sm shadow-zinc-200/50 dark:shadow-none">
      
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-zinc-200 dark:border-zinc-800 bg-white/50 dark:bg-zinc-950/50 backdrop-blur-sm z-10">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-indigo-100 dark:bg-indigo-500/20 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">ScholarForm Assistant</h2>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
              {selectedModel || 'Auto'}
            </p>
          </div>
        </div>
        <ModelSelector
          selectedModel={selectedModel}
          onModelChange={handleModelChange}
          userToken={user?.access_token}
        />
      </div>

      {/* Message History */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6 custom-scrollbar">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center space-y-3">
            <div className="w-12 h-12 rounded-full bg-indigo-50 dark:bg-indigo-500/10 flex items-center justify-center text-indigo-500 mb-2">
              <Sparkles className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-medium text-zinc-900 dark:text-zinc-100">Ready to write?</h3>
            <p className="text-sm text-zinc-500 dark:text-zinc-400 max-w-sm">
              Describe the document you want to create, and I&apos;ll generate a structured outline for your review.
            </p>
          </div>
        ) : (
          messages.map((msg, index) => (
            <MessageBubble key={msg.id || index} message={msg} />
          ))
        )}

        {/* Error Message */}
        {error && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 dark:bg-red-500/10 text-red-600 dark:text-red-400 text-sm border border-red-100 dark:border-red-500/20 mx-4">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <p>{error}</p>
          </div>
        )}

        {/* Typing Indicator */}
        <AnimatePresence>
          {isTyping && (
            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="flex gap-3 max-w-[85%]"
            >
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-indigo-100 dark:bg-indigo-500/20 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
                <Bot className="w-4 h-4" />
              </div>
              <div className="px-4 py-3 rounded-2xl rounded-tl-sm bg-zinc-100 dark:bg-zinc-800/80 border border-zinc-200 dark:border-zinc-700/50 flex items-center gap-1 w-16">
                <span className="w-1.5 h-1.5 bg-zinc-400 dark:bg-zinc-500 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                <span className="w-1.5 h-1.5 bg-zinc-400 dark:bg-zinc-500 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                <span className="w-1.5 h-1.5 bg-zinc-400 dark:bg-zinc-500 rounded-full animate-bounce"></span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="px-4 py-3 border-t border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950">
        <form 
          onSubmit={handleSubmit}
          className="relative flex items-end gap-2 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-2 focus-within:ring-2 focus-within:ring-indigo-500/20 focus-within:border-indigo-500 transition-all"
        >
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isTyping ? "Agent is thinking..." : "Type your prompt here..."}
            disabled={isTyping}
            rows={1}
            className="flex-1 max-h-32 min-h-[24px] bg-transparent border-0 resize-none py-1 px-2 text-sm text-zinc-900 dark:text-zinc-100 placeholder-zinc-500 focus:ring-0 focus:outline-none custom-scrollbar disabled:opacity-50"
            style={{ height: 'auto' }}
            onInput={(e) => {
              e.target.style.height = 'auto';
              e.target.style.height = `${e.target.scrollHeight}px`;
            }}
          />
          {isTyping && onStop && (
            <button
              type="button"
              onClick={onStop}
              className="flex-shrink-0 p-2 rounded-lg bg-red-100 dark:bg-red-500/10 hover:bg-red-200 dark:hover:bg-red-500/20 text-red-600 dark:text-red-400 transition-colors"
              title="Stop Agent"
            >
              <Square className="w-4 h-4 fill-current" />
            </button>
          )}
          <button
            type="submit"
            disabled={!input.trim() || isTyping}
            className="flex-shrink-0 p-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:bg-zinc-200 dark:disabled:bg-zinc-800 text-white disabled:text-zinc-400 transition-colors"
            title="Submit (Ctrl+Enter)"
          >
            {isTyping ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4 ml-0.5" />
            )}
          </button>
        </form>
        <div className="mt-2 text-center">
          <p className="text-[10px] text-zinc-500 dark:text-zinc-400">
            AI can make mistakes. Verify important information.
          </p>
        </div>
      </div>
    </div>
  );
});

AgentChatPane.displayName = 'AgentChatPane';

export default AgentChatPane;
