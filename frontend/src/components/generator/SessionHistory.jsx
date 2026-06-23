// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import React, { useState, useEffect, useCallback } from 'react';
import { Clock, Trash2, ChevronRight, File, Loader2 } from 'lucide-react';
import { supabase } from '../../lib/supabaseClient';
import { getGeneratorSessions, deleteGeneratorSession } from '../../services/api.v1';

const SessionHistory = React.memo(({ activeSessionId, onSelectSession }) => {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(null);

  const fetchSessions = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getGeneratorSessions();
      setSessions(data?.sessions || []);
    } catch (err) {
      console.warn("Falling back to mock sessions:", err);
      // Mock data for development/Alpha if API missing
      setSessions([
        { id: 'sess-1', title: 'IEEE Paper on AI Education', date: new Date().toISOString(), status: 'completed', template: 'IEEE', prompt: 'AI in education' },
        { id: 'sess-2', title: 'Literature Review: Transformer Models', date: new Date(Date.now() - 86400000).toISOString(), status: 'draft', template: 'Nature', prompt: 'Transformer models' }
      ]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const checkAuthAndLoad = async () => {
      if (!supabase) {
        setLoading(false);
        return;
      }

      const { data: { user: currentUser } } = await supabase.auth.getUser();
      setUser(currentUser);
      
      if (currentUser) {
        fetchSessions();
      } else {
        setLoading(false);
      }
    };
    
    checkAuthAndLoad();
  }, [fetchSessions]);

  const handleDelete = async (e, id) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this session?')) return;

    try {
      setSessions(prev => prev.filter(s => s.id !== id));
      await deleteGeneratorSession(id);
    } catch (err) {
      console.error('Failed to delete session:', err);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown date';
    const d = new Date(dateString);
    const today = new Date();
    
    if (d.toDateString() === today.toDateString()) {
      return `Today at ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    }
    return d.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' });
  };

  if (!user) {
    return (
      <div className="flex flex-col h-full bg-zinc-50 dark:bg-zinc-900 border-r border-zinc-200 dark:border-zinc-800 p-4">
        <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 flex items-center gap-2 mb-4 px-2">
          <Clock className="w-4 h-4 text-zinc-500" />
          History
        </h2>
        <div className="flex-1 flex flex-col items-center justify-center text-center p-6 bg-white dark:bg-zinc-950 rounded-xl border border-zinc-200 dark:border-zinc-800 border-dashed">
          <p className="text-sm font-medium text-zinc-600 dark:text-zinc-400">Sign in required</p>
          <p className="text-xs text-zinc-500 mt-1 max-w-[150px]">
            Please sign in to view and save your session history.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-zinc-50 dark:bg-zinc-900 border-r border-zinc-200 dark:border-zinc-800">
      <div className="p-4 border-b border-zinc-200 dark:border-zinc-800">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400 flex items-center gap-2">
          <Clock className="w-3.5 h-3.5" />
          Recent Sessions
        </h2>
      </div>

      <div className="flex-1 overflow-y-auto px-2 py-3 custom-scrollbar">
        {loading ? (
          <div className="flex justify-center p-4">
            <Loader2 className="w-5 h-5 animate-spin text-zinc-400" />
          </div>
        ) : sessions.length === 0 ? (
          <div className="text-center p-4">
            <p className="text-sm text-zinc-500">No recent sessions.</p>
          </div>
        ) : (
          <div className="space-y-1">
            {sessions.map(session => (
              <div 
                key={session.id}
                onClick={() => onSelectSession(session.id)}
                className={`group flex items-center justify-between p-3 rounded-xl cursor-pointer transition-all ${
                  activeSessionId === session.id 
                    ? 'bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-100 dark:border-indigo-500/20' 
                    : 'hover:bg-zinc-100 dark:hover:bg-zinc-800/50 border border-transparent'
                }`}
              >
                <div className="flex items-start gap-3 min-w-0">
                  <div className={`mt-0.5 w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                    activeSessionId === session.id
                      ? 'bg-indigo-100 dark:bg-indigo-500/20 text-indigo-600 dark:text-indigo-400'
                      : 'bg-white dark:bg-zinc-800 text-zinc-500 border border-zinc-200 dark:border-zinc-700'
                  }`}>
                    <File className="w-4 h-4" />
                  </div>
                  
                  <div className="min-w-0">
                    <h3 className={`text-sm font-medium truncate ${
                      activeSessionId === session.id ? 'text-indigo-900 dark:text-indigo-100' : 'text-zinc-900 dark:text-zinc-100'
                    }`}>
                      {session.title || session.prompt || session.user_prompt || 'Untitled Session'}
                    </h3>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-xs text-zinc-500 truncate">
                        {formatDate(session.date || session.created_at || session.updated_at)}
                      </span>
                      {session.status === 'completed' && (
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
                      )}
                    </div>
                    {(session.template || session.template_id || session.config?.template || session.config?.template_id) && (
                      <div className="mt-1 text-[10px] uppercase tracking-wide text-zinc-400">
                        {session.template || session.template_id || session.config?.template || session.config?.template_id}
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity pl-2">
                  <button 
                    onClick={(e) => handleDelete(e, session.id)}
                    className="p-1.5 text-zinc-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10 rounded-md transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                  <ChevronRight className="w-4 h-4 text-zinc-400 shrink-0" />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
});

SessionHistory.displayName = 'SessionHistory';

export default SessionHistory;
