'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';

export default function NotificationSettingsPage() {
  const { session } = useAuth();
  const [preferences, setPreferences] = useState<any>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (session?.access_token) {
      fetch('/api/v1/notifications/preferences', {
        headers: { Authorization: `Bearer ${session.access_token}` }
      })
      .then(res => res.json())
      .then(data => setPreferences(data))
      .catch(e => console.error(e));
    }
  }, [session]);

  const savePreferences = async (newPrefs: any) => {
    setSaving(true);
    try {
      await fetch('/api/v1/notifications/preferences', {
        method: 'PUT',
        headers: { 
          Authorization: `Bearer ${session?.access_token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(newPrefs)
      });
      setPreferences(newPrefs);
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  if (!preferences) return <div className="p-8 text-center text-slate-500">Loading preferences...</div>;

  return (
    <div className="max-w-3xl mx-auto p-6">
      <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-6">Notification Preferences</h1>
      
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
        
        {/* DND Settings */}
        <div className="p-6 border-b border-slate-200 dark:border-slate-700">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Do Not Disturb</h3>
              <p className="text-sm text-slate-500">Pause all non-critical notifications during these hours.</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input 
                type="checkbox" 
                className="sr-only peer" 
                checked={preferences.dnd_enabled || false}
                onChange={(e) => savePreferences({ ...preferences, dnd_enabled: e.target.checked })}
              />
              <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/20 dark:peer-focus:ring-primary/80 rounded-full peer dark:bg-slate-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-slate-600 peer-checked:bg-primary"></div>
            </label>
          </div>
          
          {preferences.dnd_enabled && (
            <div className="flex gap-4 items-center mt-4">
              <div className="flex-1">
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Start Time</label>
                <input 
                  type="time" 
                  className="w-full rounded-lg border-slate-300 dark:border-slate-600 dark:bg-slate-700 p-2"
                  value={preferences.dnd_start_time || '22:00'}
                  onChange={(e) => savePreferences({ ...preferences, dnd_start_time: e.target.value })}
                />
              </div>
              <span className="text-slate-500 mt-6">to</span>
              <div className="flex-1">
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">End Time</label>
                <input 
                  type="time" 
                  className="w-full rounded-lg border-slate-300 dark:border-slate-600 dark:bg-slate-700 p-2"
                  value={preferences.dnd_end_time || '08:00'}
                  onChange={(e) => savePreferences({ ...preferences, dnd_end_time: e.target.value })}
                />
              </div>
            </div>
          )}
        </div>

        {/* Channels */}
        <div className="p-6">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Delivery Channels</h3>
          <p className="text-sm text-slate-500 mb-6">Select how you want to receive notifications. In-app notifications are always enabled.</p>
          
          <div className="space-y-4">
            {['Email', 'Slack', 'Microsoft Teams', 'Discord', 'SMS', 'Push Notifications'].map((channel) => (
              <div key={channel} className="flex justify-between items-center p-4 rounded-lg bg-slate-50 dark:bg-slate-900/50 border border-slate-100 dark:border-slate-700">
                <div className="flex items-center gap-3">
                  <span className="material-symbols-outlined text-slate-400">
                    {channel === 'Email' ? 'mail' : channel === 'SMS' ? 'sms' : 'notifications_active'}
                  </span>
                  <span className="font-medium text-slate-700 dark:text-slate-300">{channel}</span>
                </div>
                <button className="text-sm text-primary font-medium hover:underline">
                  Configure
                </button>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
}
