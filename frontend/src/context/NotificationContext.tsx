'use client';

import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';
import { useAuth } from './AuthContext'; // assuming an AuthContext exists

export interface Notification {
  id: string;
  type: string;
  title: string;
  body: string;
  read_at: string | null;
  created_at: string;
  metadata: any;
}

interface NotificationContextType {
  notifications: Notification[];
  unreadCount: number;
  markAsRead: (id: string) => Promise<void>;
  markAllAsRead: () => Promise<void>;
  fetchHistory: () => Promise<void>;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export const NotificationProvider = ({ children }: { children: React.ReactNode }) => {
  const { session, user } = useAuth(); // using supabase session or similar
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const ws = useRef<WebSocket | null>(null);

  const fetchHistory = useCallback(async () => {
    if (!session?.access_token) return;
    try {
      const res = await fetch('/api/v1/notifications', {
        headers: { Authorization: `Bearer ${session.access_token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setNotifications(data);
      }
    } catch (e) {
      console.error('Failed to fetch notifications', e);
    }
  }, [session]);

  const connectWebSocket = useCallback(() => {
    if (!user?.id || !session?.access_token) return;

    // Use token as query param for auth as configured in the backend
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/v1/notifications/ws?token=${user.id}`;
    
    ws.current = new WebSocket(wsUrl);

    ws.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.event_type === 'notification_received') {
          // Prepend new notification
          setNotifications(prev => [data.payload, ...prev]);
          
          // Optionally trigger browser native notification if permitted
          if (Notification.permission === 'granted') {
            new Notification(data.payload.title, { body: data.payload.body });
          }
        }
      } catch (err) {
        console.error('WebSocket parse error', err);
      }
    };

    ws.current.onclose = () => {
      console.log('Notification WebSocket closed, reconnecting in 5s...');
      setTimeout(connectWebSocket, 5000);
    };
  }, [user, session]);

  useEffect(() => {
    if (user && session) {
      fetchHistory();
      connectWebSocket();
      
      // Request native push permissions
      if (typeof window !== 'undefined' && 'Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
      }
    }
    
    return () => {
      if (ws.current) {
        ws.current.onclose = null; // prevent reconnect on unmount
        ws.current.close();
      }
    };
  }, [user, session, fetchHistory, connectWebSocket]);

  const markAsRead = async (id: string) => {
    if (!session?.access_token) return;
    try {
      await fetch(`/api/v1/notifications/${id}/read`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${session.access_token}` }
      });
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, read_at: new Date().toISOString() } : n));
    } catch (e) {
      console.error('Failed to mark as read', e);
    }
  };

  const markAllAsRead = async () => {
    // In a full implementation, we'd add an endpoint for mark-all-read. For now, mark local.
    setNotifications(prev => prev.map(n => ({ ...n, read_at: new Date().toISOString() })));
  };

  const unreadCount = notifications.filter(n => !n.read_at).length;

  return (
    <NotificationContext.Provider value={{ notifications, unreadCount, markAsRead, markAllAsRead, fetchHistory }}>
      {children}
    </NotificationContext.Provider>
  );
};

export const useNotifications = () => {
  const context = useContext(NotificationContext);
  if (context === undefined) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
};
