// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { useState, useCallback } from 'react';
import { 
  createAgentSession, 
  getSession, 
  getSessionMessages, 
  getSessionDocument, 
  sendMessage, 
  stopSession,
  approveOutline
} from '../services/api.generator.v1';
import { trackEvent } from '../lib/analytics';
import { AgentMessageSchema, AgentSessionStartSchema, getFirstZodError } from '../lib/schemas';

/**
 * Custom hook for managing Agent Session state and operations.
 * Provides abstraction for API calls and state management.
 */
export const useAgent = (initialSessionId = null) => {
  const [activeSessionId, setActiveSessionId] = useState(initialSessionId);
  const [sessionState, setSessionState] = useState('idle');
  const [messages, setMessages] = useState([]);
  const [outlineData, setOutlineData] = useState(null);
  const [qualityScore, setQualityScore] = useState(null);
  const [isTyping, setIsTyping] = useState(false);
  const [error, setError] = useState(null);
  const [lastPrompt, setLastPrompt] = useState('');
  const [documentSections, setDocumentSections] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState('ieee');
  const [selectedModel, setSelectedModel] = useState('');

  const deriveSessionState = useCallback((session) => {
    const status = session?.status || '';
    const stage = session?.config?.stage || '';
    if (status === 'completed' || stage === 'done') return 'complete';
    if (status === 'awaiting_approval' || stage === 'awaiting_approval' || stage === 'outline') return 'outline_review';
    if (['writing', 'citations', 'rendering', 'scoring', 'rewriting', 'quality_boost'].includes(stage)) return 'generating';
    if (status === 'processing' || stage) return 'parsing';
    if (status === 'canceled') return 'idle';
    return 'idle';
  }, []);

  const fetchSessionData = useCallback(async (sessionId) => {
    try {
      const data = await getSession(sessionId);
      const config = data?.config || {};
      setOutlineData(data?.outline || null);
      setQualityScore(config?.quality || null);
      if (config?.template) {
        setSelectedTemplate(String(config.template).toLowerCase());
      }
      if (config?.user_prompt) {
        setLastPrompt(String(config.user_prompt));
      }
      setSessionState(deriveSessionState(data));
      return data;
    } catch (err) {
      console.error("Failed to fetch session data:", err);
      throw err;
    }
  }, [deriveSessionState]);

  const fetchSessionMessages = useCallback(async (sessionId) => {
    try {
      const res = await getSessionMessages(sessionId);
      const rawMessages = res?.messages || res || [];
      const filtered = rawMessages.filter(msg => msg.role !== 'system');
      const mapped = filtered.map((msg, index) => ({
        id: `${msg.created_at || Date.now()}-${index}`,
        role: msg.role,
        content: msg.content,
        timestamp: msg.created_at || Date.now()
      }));
      if (mapped.length) {
        setMessages(mapped);
      }
      return mapped.length;
    } catch (err) {
      console.error("Failed to fetch session messages:", err);
      return 0;
    }
  }, []);

  const fetchLatestDocument = useCallback(async (sessionId) => {
    try {
      const res = await getSessionDocument(sessionId);
      const content = res?.content || res?.content_json || res;
      const sections = content?.sections || {};
      let entries = [];

      if (Array.isArray(sections)) {
        entries = sections.map((item, idx) => ({
          title: item.title || item.section || `Section ${idx + 1}`,
          content: item.content || ''
        }));
      } else if (sections && typeof sections === 'object') {
        entries = Object.entries(sections).map(([title, content]) => ({ title, content: String(content || '') }));
      }

      if (content?.references && Array.isArray(content.references) && content.references.length) {
        entries.push({ title: 'References', content: content.references.join('\n') });
      }

      const mapped = entries.map((section) => ({
        id: `section-${String(section.title).toLowerCase().replace(/[^a-z0-9]+/g, '-')}`,
        title: section.title,
        content: section.content,
        isCompleted: true,
        wordCount: section.content ? section.content.trim().split(/\s+/).length : 0
      }));

      setDocumentSections(mapped);
    } catch (err) {
      console.error("Failed to fetch latest document:", err);
    }
  }, []);

  const loadSession = useCallback(async (sessionId) => {
    try {
      setError(null);
      setIsTyping(true);
      setActiveSessionId(sessionId);
      const data = await fetchSessionData(sessionId);
      const [messageCount] = await Promise.all([
        fetchSessionMessages(sessionId),
        fetchLatestDocument(sessionId),
      ]);
      if (!messageCount) {
        setMessages([{
          id: Date.now(),
          role: 'assistant',
          content: 'Session loaded. You can continue with refinements or downloads.',
          timestamp: Date.now(),
          isStatus: true
        }]);
      }
      setIsTyping(false);
      return data;
    } catch (err) {
      console.error("Failed to load session:", err);
      setError("Failed to load the selected session.");
      setIsTyping(false);
      throw err;
    }
  }, [fetchSessionData, fetchSessionMessages, fetchLatestDocument]);

  const handleStartSession = async (text, template, options = {}) => {
    const validation = AgentSessionStartSchema.safeParse({
      prompt: text,
      template,
      config: options,
    });
    if (!validation.success) {
      const message = getFirstZodError(validation.error?.issues, 'Invalid session input.');
      setError(message);
      throw new Error(message);
    }

    const { prompt, template: validatedTemplate, config } = validation.data;
    const mergedConfig = { ...(config || {}), ...(selectedModel ? { model: selectedModel } : {}) };
    setSessionState('parsing');
    setIsTyping(true);
    setError(null);
    setLastPrompt(prompt);
    setDocumentSections([]);
    
    // Add the initiating prompt plus a status message so the first turn is visible.
    const messageTimestamp = Date.now();
    setMessages(prev => [...prev, {
      id: messageTimestamp,
      role: 'user',
      content: prompt,
      timestamp: messageTimestamp
    }, {
      id: messageTimestamp + 1,
      role: 'assistant', 
      content: 'Parsing your request and preparing an outline...',
      timestamp: messageTimestamp + 1,
      isStatus: true
    }]);

    try {
      const response = await createAgentSession(prompt, validatedTemplate, mergedConfig);
      const sessionId = response?.session_id || response?.id || response?.sessionId;
      if (!sessionId) throw new Error('No session ID returned from server.');
      
      setActiveSessionId(sessionId);
      trackEvent('generator_session_started', {
        session_id: sessionId,
        template: String(validatedTemplate || selectedTemplate || '').toLowerCase(),
        prompt_length: String(prompt || '').trim().length,
        has_options: Boolean(config && Object.keys(config).length > 0),
      });
      return sessionId;
    } catch (err) {
      setIsTyping(false);
      setError(err.message || 'Failed to start the session.');
      throw err;
    }
  };

  const handleSendMessage = async (text) => {
    const validation = AgentMessageSchema.safeParse({ content: text });
    if (!validation.success) {
      setError(getFirstZodError(validation.error?.issues, 'Invalid message input.'));
      return;
    }
    const cleanText = validation.data.content;

    setMessages(prev => [...prev, { id: Date.now(), role: 'user', content: cleanText, timestamp: Date.now() }]);
    setIsTyping(true);
    setError(null);

    try {
      const res = await sendMessage(activeSessionId, cleanText, selectedModel);
      if (res && res.content) {
        setMessages(prev => [...prev, { 
          id: Date.now(), 
          role: res.role || 'assistant', 
          content: res.content,
          sources: res.sources || [],
          timestamp: res.created_at || Date.now() 
        }]);
      } else {
        setMessages(prev => [...prev, { role: 'assistant', content: "I couldn't generate a response.", timestamp: Date.now() }]);
      }
      await fetchLatestDocument(activeSessionId);
    } catch (err) {
      setError(err.message || "An error occurred while communicating with the agent.");
    } finally {
      setIsTyping(false);
    }
  };

  const handleStop = async () => {
    if (!activeSessionId) return;
    try {
      await stopSession(activeSessionId);
      setMessages(prev => [...prev, {
        id: Date.now(),
        role: 'assistant',
        content: 'I have stopped the current task as requested.',
        timestamp: Date.now(),
        isStatus: true
      }]);
      setSessionState('idle');
      setIsTyping(false);
    } catch (err) {
      setError(err.message || 'Failed to stop session.');
    }
  };

  const handleApprove = async (modifiedOutline) => {
    if (!activeSessionId) return;
    setOutlineData(modifiedOutline);
    setSessionState('generating');
    setDocumentSections([]);
    
    setMessages(prev => [...prev, { 
      id: Date.now(), 
      role: 'user', 
      content: 'I have approved the outline. Please proceed with writing.', 
      timestamp: Date.now() 
    }, {
      id: Date.now() + 1,
      role: 'assistant',
      content: 'Starting document generation based on the approved outline. You can watch the progress in the right panel.',
      timestamp: Date.now() + 100,
      isStatus: true
    }]);

    try {
      await approveOutline(activeSessionId, modifiedOutline);
    } catch (err) {
      setError(err.message || 'Failed to approve outline.');
    }
  };

  return {
    activeSessionId,
    setActiveSessionId,
    sessionState,
    setSessionState,
    messages,
    setMessages,
    outlineData,
    setOutlineData,
    qualityScore,
    setQualityScore,
    isTyping,
    setIsTyping,
    error,
    setError,
    lastPrompt,
    setLastPrompt,
    documentSections,
    setDocumentSections,
    selectedTemplate,
    setSelectedTemplate,
    selectedModel,
    setSelectedModel,
    loadSession,
    handleStartSession,
    handleSendMessage,
    handleStop,
    handleApprove,
    fetchSessionData,
    fetchLatestDocument
  };
};
