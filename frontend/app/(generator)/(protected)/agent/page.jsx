// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

"use client";

import React, { useState, useEffect, useCallback, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import {
  Group as ResizablePanelGroup,
  Panel as ResizablePanel,
  Separator as ResizableHandle,
} from 'react-resizable-panels';
import { 
  BrainCircuit, 
  PanelLeftClose, 
  PanelLeftOpen, 
  Plus, 
  Settings2
} from 'lucide-react';

import AgentChatPane from '@/src/components/generator/AgentChatPane';
import DocumentBuildPane from '@/src/components/generator/DocumentBuildPane';
import SessionHistory from '@/src/components/generator/SessionHistory';
import OutlineApproval from '@/src/components/generator/OutlineApproval';
import UpgradeModal from '@/src/components/UpgradeModal';

import { useAgent } from '@/src/hooks/useAgent';
import { useAgentEvents } from '@/src/hooks/useAgentEvents';
import { useAuth } from '@/src/context/AuthContext';
import { canAccess } from '@/src/lib/planTier';
import { trackPageView } from '@/src/lib/rum';

/**
 * AgentWorkspaceContent
 * 
 * Performance-optimized main container for the AI Agent authoring experience.
 * Uses custom hooks for state management and SSE event handling.
 */
function AgentWorkspaceContent() {
  const searchParams = useSearchParams();
  const { user } = useAuth();
  useEffect(() => { trackPageView('/agent'); }, []);
  
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [activeMobileTab, setActiveMobileTab] = useState('chat');

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 640);
    check();
    window.addEventListener('resize', check);
    return () => window.removeEventListener('resize', check);
  }, []);
  
  // Use our optimized hooks
  const {
    activeSessionId,
    messages,
    isTyping,
    sessionState,
    outlineData,
    qualityScore,
    documentSections,
    error,
    setActiveSessionId,
    setSessionState,
    setMessages,
    setOutlineData,
    setQualityScore,
    setIsTyping,
    setLastPrompt,
    setDocumentSections,
    selectedTemplate,
    selectedModel,
    setSelectedModel,
    lastPrompt,
    handleStartSession,
    handleSendMessage,
    handleStop,
    handleApprove,
    loadSession,
    fetchSessionData,
    fetchLatestDocument
  } = useAgent();

  // Handle SSE events
  useAgentEvents({
    activeSessionId,
    setOutlineData,
    setSessionState,
    setIsTyping,
    setMessages,
    fetchSessionData,
    fetchLatestDocument,
    selectedTemplate,
    lastPrompt,
  });

  // Initial load from search params
  useEffect(() => {
    const sessionFromQuery = searchParams.get('session');
    if (sessionFromQuery && sessionFromQuery !== activeSessionId) {
      loadSession(sessionFromQuery);
    }
  }, [searchParams, loadSession, activeSessionId]);

  // Auth check
  useEffect(() => {
    if (user && !canAccess(user, 'generator_agent')) {
      setShowUpgradeModal(true);
    }
  }, [user]);

  // Layout Handlers
  const toggleSidebar = () => setIsSidebarOpen(!isSidebarOpen);

  const handleSelectSession = (id) => {
    loadSession(id);
  };

  const handleNewSession = () => {
    setActiveSessionId(null);
    setMessages([]);
    setOutlineData(null);
    setQualityScore(null);
    setSessionState('idle');
    setIsTyping(false);
    setLastPrompt('');
    setDocumentSections([]);
  };

  const handleChatSubmit = useCallback((text) => {
    const submit = async () => {
      if (activeSessionId) {
        await handleSendMessage(text);
        return;
      }
      await handleStartSession(text, selectedTemplate, {});
    };

    submit().catch((submitError) => {
      console.error('Agent submission failed:', submitError);
    });
  }, [activeSessionId, handleSendMessage, handleStartSession, selectedTemplate]);

  if (user && !canAccess(user, 'generator_agent')) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-background-light dark:bg-background-dark">
        <UpgradeModal 
          isOpen={showUpgradeModal} 
          onClose={() => setShowUpgradeModal(false)} 
          title="Upgrade to Pro for AI Agent" 
        />
        <div className="w-16 h-16 rounded-2xl bg-indigo-100 dark:bg-indigo-500/10 flex items-center justify-center mb-6">
          <BrainCircuit className="w-8 h-8 text-indigo-600 dark:text-indigo-400" />
        </div>
        <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-4">AI Agent is a Pro Feature</h2>
        <p className="text-slate-600 dark:text-slate-400 mb-8 max-w-md">
          Upgrade to our Pro plan to interact with the AI Agent for intelligent document synthesis and drafting.
        </p>
        <button 
          onClick={() => setShowUpgradeModal(true)} 
          className="px-8 py-3 bg-indigo-600 text-white font-semibold rounded-xl hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-600/20"
        >
          View Plans
        </button>
      </div>
    );
  }

  // Chat panel content (shared between mobile + desktop)
  const chatPanel = (
    <div className="h-full flex flex-col relative">
      {sessionState === 'outline_review' && outlineData && (
        <div className="absolute inset-x-4 top-4 bottom-24 z-30 transition-all">
          <OutlineApproval
            outline={outlineData}
            onApprove={handleApprove}
            onRegenerate={() => handleSendMessage('Regenerate the outline with more focus on methodology.')}
          />
        </div>
      )}
      <AgentChatPane
        messages={messages}
        onSendMessage={handleChatSubmit}
        onStop={handleStop}
        isTyping={isTyping}
        error={error}
        selectedModel={selectedModel}
        onModelChange={setSelectedModel}
      />
    </div>
  );

  const documentPanel = (
    <DocumentBuildPane
      sessionId={activeSessionId}
      stage={sessionState}
      qualityScore={qualityScore}
      initialSections={documentSections}
      onDownload={(format) => window.open(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/generator/sessions/${activeSessionId}/export?format=${format}`)}
    />
  );

  return (
    <div className="flex flex-col h-[calc(100vh-64px)] overflow-hidden bg-background-light dark:bg-background-dark">
      <UpgradeModal
        isOpen={showUpgradeModal}
        onClose={() => setShowUpgradeModal(false)}
        title="Upgrade to Pro for AI Agent"
      />

      {/* Top Toolbar */}
      <div className="h-12 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-4 bg-slate-50/50 dark:bg-slate-900/50 shrink-0">
        <div className="flex items-center gap-3">
          {!isMobile && (
            <button
              onClick={toggleSidebar}
              className="p-1.5 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-md transition-colors text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
              title={isSidebarOpen ? 'Hide History' : 'Show History'}
              aria-label={isSidebarOpen ? 'Hide history sidebar' : 'Show history sidebar'}
            >
              {isSidebarOpen ? <PanelLeftClose className="w-4 h-4" /> : <PanelLeftOpen className="w-4 h-4" />}
            </button>
          )}
          <div className="h-4 w-px bg-slate-300 dark:bg-slate-700 mx-1 hidden sm:block" />
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg bg-indigo-600 flex items-center justify-center">
              <BrainCircuit className="w-3.5 h-3.5 text-white" />
            </div>
            <h1 className="text-sm font-semibold text-slate-900 dark:text-slate-100 italic">
              ScholarForm AI <span className="text-slate-400 font-normal hidden sm:inline">Agent Workspace</span>
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleNewSession}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700/50 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 transition-colors shadow-sm"
          >
            <Plus className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">New Project</span>
            <span className="sm:hidden">New</span>
          </button>
          <button className="p-1.5 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-md transition-colors text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/40">
            <Settings2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* ── Mobile Tab Bar ──────────────────────────────────────────────── */}
      {isMobile ? (
        <div className="flex flex-col flex-1 min-h-0">
          {/* Tab switcher */}
          <div className="flex shrink-0 border-b border-slate-200 dark:border-slate-800 bg-background-light dark:bg-background-dark">
            <button
              onClick={() => setActiveMobileTab('chat')}
              className={`flex flex-1 items-center justify-center gap-2 py-3 text-xs font-bold uppercase tracking-wider transition-colors ${
                activeMobileTab === 'chat'
                  ? 'text-indigo-600 border-b-2 border-indigo-600 bg-indigo-50/50 dark:bg-indigo-500/5'
                  : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
              }`}
            >
              <BrainCircuit className="w-4 h-4" />
              Chat
            </button>
            <button
              onClick={() => setActiveMobileTab('document')}
              className={`flex flex-1 items-center justify-center gap-2 py-3 text-xs font-bold uppercase tracking-wider transition-colors ${
                activeMobileTab === 'document'
                  ? 'text-indigo-600 border-b-2 border-indigo-600 bg-indigo-50/50 dark:bg-indigo-500/5'
                  : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
              }`}
            >
              <Settings2 className="w-4 h-4" />
              Document
            </button>
          </div>

          {/* Tab content */}
          <div className={`flex-1 min-h-0 overflow-hidden ${activeMobileTab !== 'chat' ? 'hidden' : 'flex flex-col'}`}>
            {chatPanel}
          </div>
          <div className={`flex-1 min-h-0 overflow-hidden ${activeMobileTab !== 'document' ? 'hidden' : 'flex flex-col'}`}>
            {documentPanel}
          </div>
        </div>
      ) : (
        /* ── Desktop Resizable Layout ────────────────────────────────────── */
        <ResizablePanelGroup direction="horizontal" className="flex-1">
          {/* Sidebar: History */}
          {isSidebarOpen && (
            <>
              <ResizablePanel defaultSize={20} minSize={15} maxSize={30}>
                <SessionHistory
                  activeSessionId={activeSessionId}
                  onSelectSession={handleSelectSession}
                />
              </ResizablePanel>
              <ResizableHandle className="bg-slate-200 dark:bg-slate-800" />
            </>
          )}

          {/* Center: Chat */}
          <ResizablePanel defaultSize={40} minSize={30}>
            {chatPanel}
          </ResizablePanel>

          <ResizableHandle className="bg-slate-200 dark:bg-slate-800" />

          {/* Right: Document */}
          <ResizablePanel defaultSize={40} minSize={30}>
            {documentPanel}
          </ResizablePanel>
        </ResizablePanelGroup>
      )}
    </div>
  );
}

export default function AgentPage() {
  return (
    <Suspense fallback={<div className="h-screen flex items-center justify-center bg-background-light dark:bg-background-dark"><div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div></div>}>
      <AgentWorkspaceContent />
    </Suspense>
  );
}
