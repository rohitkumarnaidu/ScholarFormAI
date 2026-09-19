'use client';

import React, { createContext, useContext, useEffect, useRef } from 'react';
import { useAuth } from './AuthContext';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getNotifications, markNotificationAsRead, type Notification } from '../services/api.notifications';

interface NotificationContextType {
  notifications: Notification[];
  unreadCount: number;
  markAsRead: (id: string) => Promise<void>;
  markAllAsRead: () => Promise<void>;
  fetchHistory: () => Promise<void>;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export const NotificationProvider = ({ children }: { children: React.ReactNode }) => {
  const { session, user } = useAuth();
  const queryClient = useQueryClient();
  const ws = useRef<WebSocket | null>(null);

  const { data: notifications = [] } = useQuery({
    queryKey: ['notifications'],
    queryFn: getNotifications,
    enabled: !!session?.access_token && !!user?.id,
  });

  const markAsReadMutation = useMutation({
    mutationFn: markNotificationAsRead,
    onSuccess: (_, id) => {
      queryClient.setQueryData<Notification[]>(['notifications'], (old = []) => 
        old.map(n => n.id === id ? { ...n, read_at: new Date().toISOString() } : n)
      );
    }
  });

  const fetchHistory = async () => {
    await queryClient.refetchQueries({ queryKey: ['notifications'] });
  };

  const markAllAsRead = async () => {
    queryClient.setQueryData<Notification[]>(['notifications'], (old = []) => 
      old.map(n => ({ ...n, read_at: new Date().toISOString() }))
    );
  };

  const markAsRead = async (id: string) => {
    await markAsReadMutation.mutateAsync(id);
  };

  useEffect(() => {
    if (!user?.id || !session?.access_token) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/v1/notifications/ws?token=${user.id}`;
    
    const connect = () => {
      ws.current = new WebSocket(wsUrl);

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.event_type === 'notification_received') {
            queryClient.setQueryData<Notification[]>(['notifications'], (old = []) => [data.payload, ...old]);
            
            if (typeof window !== 'undefined' && 'Notification' in window && Notification.permission === 'granted') {
              new Notification(data.payload.title, { body: data.payload.body });
            }
          }
        } catch (err) {
          console.error('WebSocket parse error', err);
        }
      };

      ws.current.onclose = () => {
        if(process.env.NODE_ENV === "development") console.log('Notification WebSocket closed, reconnecting in 5s...');
        setTimeout(connect, 5000);
      };
    };

    connect();

    if (typeof window !== 'undefined' && 'Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
    
    return () => {
      if (ws.current) {
        ws.current.onclose = null;
        ws.current.close();
      }
    };
  }, [user, session, queryClient]);

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
