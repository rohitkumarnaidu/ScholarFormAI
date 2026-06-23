// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { useEffect, useRef } from 'react';

/**
 * Custom hook for managing Agent SSE events.
 * Handles outline chunks and stage updates.
 */
export const useAgentEvents = ({
  activeSessionId,
  setOutlineData,
  setSessionState,
  setIsTyping,
  setMessages,
  fetchSessionData,
  fetchLatestDocument,
  selectedTemplate,
  lastPrompt
}) => {
  const eventSourceRef = useRef(null);
  const outlineBufferRef = useRef('');
  const outlineReadyRef = useRef(false);
  const lastStageRef = useRef(null);

  useEffect(() => {
    if (!activeSessionId) return;

    outlineReadyRef.current = false;
    outlineBufferRef.current = '';
    
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    // Note: In production, withCredentials might need to be true if using cookies, 
    // but here we are using JWT in the URL usually (handled in Phase 4).
    const eventSource = new EventSource(`${apiUrl}/api/v1/generator/sessions/${activeSessionId}/events`, { withCredentials: true });
    eventSourceRef.current = eventSource;

    const handleOutlineChunk = (event) => {
      if (outlineReadyRef.current) return;
      try {
        const data = JSON.parse(event.data);
        const payload = data.payload || {};
        const chunk = payload.content || '';
        if (!chunk) return;
        
        outlineBufferRef.current += chunk;
        try {
          const parsed = JSON.parse(outlineBufferRef.current);
          if (parsed && parsed.sections) {
            outlineReadyRef.current = true;
            setOutlineData(parsed);
            setSessionState('outline_review');
            setIsTyping(false);
            
            const topic = parsed.title || lastPrompt || 'your topic';
            const sectionTitles = parsed.sections
              .map((s) => s.title || s.section || '')
              .filter(Boolean)
              .join(', ');
            
            const sectionsLine = sectionTitles 
              ? `with sections: ${sectionTitles}` 
              : 'with the recommended structure';
              
            setMessages(prev => [...prev, {
              id: Date.now(),
              role: 'assistant',
              content: `I'll draft a ${selectedTemplate.toUpperCase()} paper about ${topic} ${sectionsLine}. Review the outline above.`,
              timestamp: Date.now()
            }]);
          }
        } catch (err) {
          // Wait for more chunks (incomplete JSON)
        }
      } catch (error) {
        console.error("Error parsing outline_chunk SSE data:", error);
      }
    };

    const handleStageUpdate = async (event) => {
      try {
        const data = JSON.parse(event.data);
        const payload = data.payload || {};
        const stage = data.stage || payload.stage;
        const status = payload.status || data.status;

        if (stage && lastStageRef.current !== stage) {
          lastStageRef.current = stage;
        }

        if (stage === 'outline' || stage === 'awaiting_approval') {
          setSessionState('outline_review');
          if (!outlineReadyRef.current) {
            try {
              const sessionData = await fetchSessionData(activeSessionId);
              if (sessionData?.outline) {
                outlineReadyRef.current = true;
                setIsTyping(false);
              }
            } catch (err) {
              // no-op
            }
          }
        }

        if (['writing', 'citations', 'rendering', 'scoring', 'rewriting', 'quality_boost'].includes(stage)) {
          setSessionState('generating');
        }

        if (stage === 'stopped' || status === 'canceled') {
          setSessionState('idle');
          setIsTyping(false);
          lastStageRef.current = 'stopped';
        }

        if (stage === 'done' || status === 'completed') {
          setSessionState('complete');
          setIsTyping(false);
          await Promise.all([
            fetchSessionData(activeSessionId),
            fetchLatestDocument(activeSessionId),
          ]);
          setMessages(prev => [...prev, {
            id: Date.now(),
            role: 'assistant',
            content: 'Draft complete. Quality checks finished and the document is ready for download.',
            timestamp: Date.now()
          }]);
        }
      } catch (error) {
        console.error("Error parsing stage_update SSE data:", error);
      }
    };

    eventSource.addEventListener('outline_chunk', handleOutlineChunk);
    eventSource.addEventListener('stage_update', handleStageUpdate);

    eventSource.onerror = (err) => {
      console.error('SSE Error:', err);
    };

    return () => {
      eventSource.close();
    };
  }, [
    activeSessionId, 
    selectedTemplate, 
    lastPrompt, 
    setOutlineData, 
    setSessionState, 
    setIsTyping, 
    setMessages, 
    fetchSessionData, 
    fetchLatestDocument
  ]);

  return {
    eventSource: eventSourceRef.current,
    isOutlineReady: outlineReadyRef.current
  };
};
