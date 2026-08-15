'use client';

import React, { useState } from 'react';

export default function IssueSettingsPage() {
  const [triageModel, setTriageModel] = useState('gpt-4o-mini');
  const [reasoningModel, setReasoningModel] = useState('claude-3-5-sonnet');
  const [slackUrl, setSlackUrl] = useState('');

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    // Logic to save settings via API
    alert('Enterprise issue settings saved.');
  };

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Issue Ecosystem Settings</h1>
        <p className="text-gray-600 dark:text-gray-400">Configure AI capabilities and webhooks for the reporting ecosystem.</p>
      </div>

      <form onSubmit={handleSave} className="space-y-8">
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-200 dark:border-gray-700 space-y-4">
          <h2 className="text-xl font-semibold border-b pb-2">AI Model Capabilities</h2>
          
          <div>
            <label className="block text-sm font-medium mb-1">Triage & Categorization (Fast)</label>
            <select 
              value={triageModel} 
              onChange={e => setTriageModel(e.target.value)}
              className="w-full border-gray-300 rounded p-2 text-sm"
            >
              <option value="gpt-4o-mini">GPT-4o Mini (Recommended)</option>
              <option value="llama-3-8b">Llama 3 8B</option>
            </select>
            <p className="text-xs text-gray-500 mt-1">Used for spam detection and auto-labeling.</p>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Complex Reasoning (Suggested Fixes)</label>
            <select 
              value={reasoningModel} 
              onChange={e => setReasoningModel(e.target.value)}
              className="w-full border-gray-300 rounded p-2 text-sm"
            >
              <option value="claude-3-5-sonnet">Claude 3.5 Sonnet (Recommended)</option>
              <option value="gpt-4o">GPT-4o</option>
              <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
              <option value="llama-3-8b">Llama 3 8B (Not Recommended)</option>
            </select>
            {reasoningModel === 'llama-3-8b' && (
              <p className="text-xs text-red-500 mt-1 font-semibold">
                Warning: This model is not recommended for code-level reasoning. For accurate 'Suggested Fixes', please select a frontier model.
              </p>
            )}
            <p className="text-xs text-gray-500 mt-1">Used for analyzing stack traces and proposing code fixes.</p>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border border-gray-200 dark:border-gray-700 space-y-4">
          <h2 className="text-xl font-semibold border-b pb-2">Integrations</h2>
          
          <div>
            <label className="block text-sm font-medium mb-1">Slack Webhook URL</label>
            <input 
              type="url"
              value={slackUrl}
              onChange={e => setSlackUrl(e.target.value)}
              placeholder="https://hooks.slack.com/services/..."
              className="w-full border-gray-300 rounded p-2 text-sm"
            />
          </div>
        </div>

        <div className="flex justify-end">
          <button type="submit" className="bg-blue-600 text-white px-6 py-2 rounded font-medium hover:bg-blue-700">
            Save Settings
          </button>
        </div>
      </form>
    </div>
  );
}
