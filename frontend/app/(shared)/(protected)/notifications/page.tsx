'use client';

import React from 'react';
import { useNotifications } from '@/context/NotificationContext';
import { formatDistanceToNow } from 'date-fns';
import { Bell, Shield, Receipt, Bot } from 'lucide-react';
import Button from '@/src/components/ui/Button';

export default function NotificationsPage() {
  const { notifications, markAsRead, markAllAsRead, fetchHistory } = useNotifications();

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Notification Center</h1>
        <div className="flex gap-4">
          <Button onClick={markAllAsRead} variant="outline" size="sm">
            Mark all as read
          </Button>
          <Button onClick={fetchHistory} variant="secondary" size="sm">
            Refresh
          </Button>
        </div>
      </div>

      {notifications.length === 0 ? (
        <div className="text-center py-20 bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700">
          <Bell className="text-6xl text-slate-300 dark:text-slate-600 mb-4 block" />
          <h3 className="text-lg font-medium text-slate-900 dark:text-white">You're all caught up!</h3>
          <p className="text-slate-500 mt-1">No new notifications to display.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {notifications.map((notif) => {
            const Icon = notif.type === 'security' ? Shield :
                         notif.type === 'billing' ? Receipt :
                         notif.type === 'ai' ? Bot : Bell;
            return (
            <div 
              key={notif.id} 
              onClick={() => markAsRead(notif.id)}
              className={`p-5 rounded-xl border transition-all cursor-pointer ${
                notif.read_at 
                  ? 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700' 
                  : 'bg-blue-50/50 dark:bg-blue-900/10 border-blue-200 dark:border-blue-800 shadow-sm'
              }`}
            >
              <div className="flex justify-between items-start gap-4">
                <div className="flex gap-4 items-start">
                  <div className={`p-2 rounded-lg ${notif.read_at ? 'bg-slate-100 dark:bg-slate-700 text-slate-500' : 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'}`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className={`font-semibold ${notif.read_at ? 'text-slate-700 dark:text-slate-300' : 'text-slate-900 dark:text-white'}`}>
                      {notif.title || notif.type.toUpperCase()}
                    </h3>
                    <p className={`mt-1 text-sm ${notif.read_at ? 'text-slate-500' : 'text-slate-700 dark:text-slate-200'}`}>
                      {notif.body}
                    </p>
                  </div>
                </div>
                <div className="text-xs text-slate-400 whitespace-nowrap">
                  {formatDistanceToNow(new Date(notif.created_at), { addSuffix: true })}
                </div>
              </div>
            </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
