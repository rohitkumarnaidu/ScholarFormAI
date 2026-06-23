// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2, Send, Download, FileText, CheckCircle, MessageSquare } from 'lucide-react';
import MultiUploadPanel from '@/src/components/generator/MultiUploadPanel';
import SynthesisStageTimeline from '@/src/components/generator/SynthesisStageTimeline';
import { createSynthesisSession, sendSynthesisMessage } from '@/src/services/api.synthesis';
import { useSynthesisSessionStream } from '@/src/hooks/useSynthesisSessionStream';
import { useAuth } from '@/src/context/AuthContext';
import { canAccess } from '@/src/lib/planTier';
import UpgradeModal from '@/src/components/UpgradeModal';
import { AgentMessageSchema, SynthesisSessionStartSchema, getFirstZodError } from '@/src/lib/schemas';

export default function MultiUploadPage() {
    const router = useRouter();
    const [isSynthesizing, setIsSynthesizing] = useState(false);
    const [sessionId, setSessionId] = useState(null);
    const [createError, setCreateError] = useState('');
    const [chatMessages, setChatMessages] = useState([]);
    const [chatInput, setChatInput] = useState('');
    const [isSending, setIsSending] = useState(false);
    
    const messagesEndRef = useRef(null);
    const { stages, currentStage, isComplete, error: streamError } = useSynthesisSessionStream(sessionId);

    const { user } = useAuth();
    const [showUpgradeModal, setShowUpgradeModal] = useState(false);

    useEffect(() => {
        if (user && !canAccess(user, 'generator_multi_doc')) {
            setShowUpgradeModal(true);
        }
    }, [user]);

    // Auto-scroll chat to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [chatMessages]);

    const handleStartSynthesis = async (files, templateId) => {
        const validation = SynthesisSessionStartSchema.safeParse({
            files,
            template: templateId,
            config: {
                preserve_citations: true,
                focus_areas: ['methodology', 'results'],
            },
        });
        if (!validation.success) {
            setCreateError(getFirstZodError(validation.error?.issues, 'Invalid synthesis request.'));
            return;
        }

        const { files: validatedFiles, template: validatedTemplate, config: validatedConfig } = validation.data;

        setIsSynthesizing(true);
        setCreateError('');
        try {
            const res = await createSynthesisSession(validatedFiles, validatedTemplate, validatedConfig || {});
            
            if (res && (res.id || res.session_id)) {
                setSessionId(res.id || res.session_id);
            } else {
                setCreateError("Could not retrieve session ID from the server.");
                setIsSynthesizing(false);
            }
        } catch (err) {
            console.error(err);
            setCreateError(err.message || 'Failed to start synthesis.');
            setIsSynthesizing(false);
        }
    };

    const handleSendMessage = async (e) => {
        e.preventDefault();
        if (!chatInput.trim() || !sessionId || isSending) return;

        const validation = AgentMessageSchema.safeParse({ content: chatInput });
        if (!validation.success) {
            setChatMessages(prev => [...prev, {
                role: 'assistant',
                content: getFirstZodError(validation.error?.issues, 'Invalid message input.'),
                isError: true
            }]);
            return;
        }

        const text = validation.data.content;
        setChatInput('');
        setChatMessages(prev => [...prev, { role: 'user', content: text }]);
        setIsSending(true);
        
        try {
            const res = await sendSynthesisMessage(sessionId, text);
            // Append assistant response
            if (res && res.response) {
                setChatMessages(prev => [...prev, { 
                    role: 'assistant', 
                    content: res.response,
                    sources: res.sources || [] 
                }]);
            } else {
                setChatMessages(prev => [...prev, { role: 'assistant', content: "I couldn't generate a response." }]);
            }
        } catch (err) {
            setChatMessages(prev => [...prev, { 
                role: 'assistant', 
                content: "Error: Could not send message.", 
                isError: true 
            }]);
        } finally {
            setIsSending(false);
        }
    };

    const handleViewResults = () => {
        if (sessionId) {
            router.push(`/synthesis?session=${sessionId}`);
        }
    };

    if (!isSynthesizing) {
        return (
            <div className="min-h-[calc(100vh-4rem)] bg-slate-50 dark:bg-slate-900 py-12 px-4 sm:px-6 lg:px-8">
                <div className="max-w-4xl mx-auto mb-8 text-center">
                    <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white sm:text-4xl">
                        Multi-Document Synthesis
                    </h1>
                    <p className="mt-4 text-lg text-slate-600 dark:text-slate-300">
                        Upload multiple documents to generate a comprehensive, cohesive synthesis. Our AI will align citations, merge sections, and format the final output.
                    </p>
                </div>
                
                
                {createError && (
                    <div className="max-w-4xl mx-auto mb-6 p-4 bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-400 rounded-xl">
                        {createError}
                    </div>
                )}
                
                <UpgradeModal 
                    isOpen={showUpgradeModal} 
                    onClose={() => setShowUpgradeModal(false)} 
                    title="Upgrade to Pro for Multi-Document Synthesis" 
                />

                {!canAccess(user, 'generator_multi_doc') ? (
                    <div className="max-w-4xl mx-auto mt-12 p-8 bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 text-center shadow-sm">
                        <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-200 mb-4">Multi-Document Synthesis is a Pro Feature</h2>
                        <p className="text-slate-600 dark:text-slate-400 mb-6">Upgrade to our Pro plan to merge multiple documents into a single cohesive manuscript using our AI Agent.</p>
                        <button onClick={() => setShowUpgradeModal(true)} className="px-6 py-3 bg-indigo-600 text-white font-medium rounded-xl hover:bg-indigo-700">
                            View Plans
                        </button>
                    </div>
                ) : (
                    <MultiUploadPanel onStart={handleStartSynthesis} />
                )}
            </div>
        );
    }

    // Split Layout View
    return (
        <div className="flex flex-col lg:flex-row h-[calc(100vh-4rem)] bg-slate-50 dark:bg-slate-900 overflow-hidden">
            {/* Left Panel: Progress Timeline & Chat */}
            <div className="w-full lg:w-1/3 flex flex-col h-full border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
                <div className="flex-1 p-6 overflow-hidden flex flex-col">
                    <div className="flex items-center justify-between mb-4 shrink-0">
                        <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center">
                            <Loader2 className={`w-5 h-5 mr-3 ${isComplete ? 'hidden' : 'animate-spin text-indigo-500'}`} />
                            {isComplete ? 'Synthesis Complete' : 'Generating Content...'}
                        </h2>
                        {isComplete && <CheckCircle className="w-6 h-6 text-green-500" />}
                    </div>
                    
                    {/* Stage Timeline */}
                    <div className="flex-1 overflow-y-auto mb-6 min-h-[300px]">
                        <SynthesisStageTimeline stages={stages} currentStage={currentStage} />
                        {streamError && (
                            <div className="mt-4 p-3 bg-red-50 text-red-600 text-sm rounded-lg">
                                {streamError.message}
                            </div>
                        )}
                    </div>

                    {/* Chat Q&A interface inside the left pane */}
                    <div className="flex flex-col h-[40%] bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
                        <div className="bg-slate-100 dark:bg-slate-700/50 p-3 border-b border-slate-200 dark:border-slate-700 flex items-center shrink-0">
                            <MessageSquare className="w-4 h-4 text-indigo-500 mr-2" />
                            <h3 className="font-semibold text-sm text-slate-800 dark:text-slate-200">Doc Q&A Context</h3>
                        </div>
                        
                        <div className="flex-1 overflow-y-auto p-4 space-y-4">
                            {chatMessages.length === 0 ? (
                                <p className="text-sm text-center text-slate-500 my-auto">
                                    Ask questions about the uploaded documents while synthesis is running.
                                </p>
                            ) : (
                                chatMessages.map((msg, i) => (
                                    <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                        <div className={`max-w-[85%] rounded-lg p-3 text-sm ${
                                            msg.role === 'user' 
                                            ? 'bg-indigo-600 text-white' 
                                            : msg.isError 
                                                ? 'bg-red-100 text-red-700 dark:bg-red-900/30' 
                                                : 'bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 text-slate-800 dark:text-slate-200 shadow-sm'
                                        }`}>
                                            <p>{msg.content}</p>
                                            {msg.sources && msg.sources.length > 0 && (
                                                <div className="mt-2 flex flex-wrap gap-1">
                                                    {msg.sources.map((src, idx) => (
                                                        <span key={idx} className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-indigo-700 dark:bg-slate-800 dark:text-indigo-400 border border-indigo-100 dark:border-indigo-800/50">
                                                            From: {src.filename || 'Source'} {src.section ? `(${src.section})` : ''}
                                                        </span>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                ))
                            )}
                            {isSending && (
                                <div className="flex justify-start">
                                    <div className="bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg p-3 shadow-sm flex space-x-1.5">
                                        <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce"></div>
                                        <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce delay-100"></div>
                                        <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce delay-200"></div>
                                    </div>
                                </div>
                            )}
                            <div ref={messagesEndRef} />
                        </div>
                        
                        <form onSubmit={handleSendMessage} className="p-3 bg-white dark:bg-slate-800 border-t border-slate-200 dark:border-slate-700 shrink-0">
                            <div className="relative flex items-center">
                                <input 
                                    type="text"
                                    value={chatInput}
                                    onChange={(e) => setChatInput(e.target.value)}
                                    placeholder="What methods were used across the papers?"
                                    className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-full pl-4 pr-12 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                                    disabled={!sessionId || isSending}
                                />
                                <button
                                    type="submit"
                                    disabled={!chatInput.trim() || !sessionId || isSending}
                                    className="absolute right-1 p-1.5 bg-indigo-600 text-white rounded-full hover:bg-indigo-700 disabled:opacity-50 transition"
                                >
                                    <Send className="w-4 h-4" />
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
            
            {/* Right Panel: Document Preview / Status */}
            <div className="w-full lg:w-2/3 h-full bg-slate-100 dark:bg-slate-900/50 flex flex-col items-center justify-center p-8 relative overflow-hidden">
                {!isComplete ? (
                    <div className="text-center group max-w-lg relative z-10 p-8 rounded-2xl bg-white/50 dark:bg-slate-800/50 backdrop-blur-sm border border-slate-200/50 dark:border-slate-700/50">
                        <div className="relative w-24 h-32 mx-auto mb-6">
                            <div className="absolute inset-0 bg-indigo-500 rounded-lg shadow-lg rotate-[-6deg] opacity-20"></div>
                            <div className="absolute inset-0 bg-indigo-400 rounded-lg shadow-lg rotate-[3deg] opacity-30"></div>
                            <div className="absolute inset-0 bg-white dark:bg-slate-800 border-2 border-slate-200 dark:border-slate-600 rounded-lg shadow-xl p-3 flex flex-col justify-center animate-pulse">
                                <div className="h-2 bg-slate-200 dark:bg-slate-700 rounded w-full mb-3"></div>
                                <div className="h-2 bg-slate-200 dark:bg-slate-700 rounded w-5/6 mb-3"></div>
                                <div className="h-2 bg-slate-200 dark:bg-slate-700 rounded w-4/6"></div>
                            </div>
                        </div>
                        <h3 className="text-2xl font-bold text-slate-800 dark:text-white mb-2">Building Document</h3>
                        <p className="text-slate-500 dark:text-slate-400">
                            We are analyzing your documents, discovering structural overlaps, and intelligently generating the synthesized manuscript.
                        </p>
                    </div>
                ) : (
                    <div className="text-center bg-white dark:bg-slate-800 p-10 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-700 max-w-xl mx-auto w-full">
                        <div className="mx-auto w-20 h-20 bg-green-100 dark:bg-green-900/30 text-green-500 rounded-full flex items-center justify-center mb-6 shadow-sm border border-green-200 dark:border-green-800/50">
                            <CheckCircle className="w-10 h-10" />
                        </div>
                        <h3 className="text-3xl font-extrabold text-slate-900 dark:text-white mb-3">
                            Synthesis Complete!
                        </h3>
                        <p className="text-slate-600 dark:text-slate-300 mb-8 whitespace-pre-wrap">
                            Your sources have been successfully merged. Formatting and citations are finalized.
                        </p>
                        
                        <div className="flex flex-col sm:flex-row gap-4 justify-center">
                            <button 
                                onClick={handleViewResults}
                                className="flex-1 inline-flex justify-center items-center px-6 py-3 border border-transparent text-base font-medium rounded-xl text-white bg-indigo-600 hover:bg-indigo-700 shadow-sm"
                            >
                                <FileText className="w-5 h-5 mr-2" />
                                View Final Results
                            </button>
                            <div className="flex gap-2">
                                <a href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/generator/sessions/${sessionId}/export/docx`} 
                                   download
                                   className="inline-flex justify-center items-center p-3 border border-slate-300 dark:border-slate-600 rounded-xl text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 shadow-sm"
                                   title="Download DOCX">
                                    <Download className="w-5 h-5 text-indigo-500" />
                                    <span className="sr-only">DOCX</span>
                                </a>
                                <a href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/generator/sessions/${sessionId}/export/pdf`} 
                                   download
                                   className="inline-flex justify-center items-center p-3 border border-slate-300 dark:border-slate-600 rounded-xl text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 shadow-sm"
                                   title="Download PDF">
                                    <Download className="w-5 h-5 text-red-500" />
                                    <span className="sr-only">PDF</span>
                                </a>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
