'use client';

import React, { useState, useEffect, useRef } from 'react';
import * as rrweb from 'rrweb';
import html2canvas from 'html2canvas';

interface FeedbackWidgetProps {
  apiEndpoint?: string;
}

export const FeedbackWidget: React.FC<FeedbackWidgetProps> = ({ 
  apiEndpoint = '/api/v1/issues' 
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('bug');
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // Session recording
  const eventsRef = useRef<any[]>([]);
  const stopRecordingRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    // Start rrweb recording
    stopRecordingRef.current = rrweb.record({
      emit(event: any) {
        eventsRef.current.push(event);
        // Keep only last 2 minutes (approx)
        if (eventsRef.current.length > 2000) {
          eventsRef.current.shift();
        }
      },
    }) as any;

    return () => {
      if (stopRecordingRef.current) {
        stopRecordingRef.current();
      }
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      // Capture screenshot
      const canvas = await html2canvas(document.body);
      const screenshot = canvas.toDataURL('image/png');

      const payload = {
        title,
        description,
        category,
        severity: 'medium',
        source: 'feedback-widget',
        system_info: {
          userAgent: navigator.userAgent,
          language: navigator.language,
          screen: `${window.screen.width}x${window.screen.height}`,
          rrweb_events: eventsRef.current
        },
        screenshots: [screenshot]
      };

      const response = await fetch(apiEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) throw new Error('Submission failed');

      setIsOpen(false);
      setTitle('');
      setDescription('');
      alert('Issue submitted successfully. Thank you!');
    } catch (error) {
      console.error(error);
      alert('Failed to submit issue.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) {
    return (
      <button 
        onClick={() => setIsOpen(true)}
        className="fixed bottom-4 right-4 bg-blue-600 text-white p-3 rounded-full shadow-lg hover:bg-blue-700 z-50 transition-all"
      >
        Feedback
      </button>
    );
  }

  return (
    <div className="fixed bottom-4 right-4 w-80 bg-white dark:bg-slate-800 rounded-lg shadow-2xl border border-slate-200 dark:border-slate-700 z-50 overflow-hidden flex flex-col">
      <div className="bg-slate-50 dark:bg-slate-900 p-4 border-b border-slate-200 dark:border-slate-700 flex justify-between items-center">
        <h3 className="font-semibold text-slate-900 dark:text-white">Report an Issue</h3>
        <button onClick={() => setIsOpen(false)} className="text-slate-500 hover:text-slate-700 dark:hover:text-slate-300">
          &times;
        </button>
      </div>
      
      <form onSubmit={handleSubmit} className="p-4 space-y-4 flex-1 overflow-y-auto">
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Type</label>
          <select 
            value={category} 
            onChange={(e) => setCategory(e.target.value)}
            className="w-full bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-md p-2 text-sm"
          >
            <option value="bug">Bug Report</option>
            <option value="feature-request">Feature Request</option>
            <option value="general-feedback">General Feedback</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Title</label>
          <input 
            type="text" 
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-md p-2 text-sm"
            placeholder="Brief description"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Details</label>
          <textarea 
            required
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-md p-2 text-sm h-24 resize-none"
            placeholder="Please provide steps to reproduce or details..."
          />
        </div>
        
        <p className="text-xs text-slate-500">
          A screenshot and short screen recording will be automatically attached to help us debug.
        </p>

        <button 
          type="submit" 
          disabled={isSubmitting}
          className="w-full bg-blue-600 text-white rounded-md p-2 font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {isSubmitting ? 'Submitting...' : 'Submit'}
        </button>
      </form>
    </div>
  );
};
