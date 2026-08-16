// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from '@/context/ThemeContext';
import { AuthProvider } from '@/context/AuthContext';
import { ToastProvider } from '@/context/ToastContext';
import { DocumentProvider } from '@/context/DocumentContext';
import { UserPreferencesProvider } from '@/context/UserPreferencesContext';
import { NotificationProvider } from '@/context/NotificationContext';
import FocusManager from '@/components/layout/FocusManager';
import DynamicMeta from '@/components/layout/DynamicMeta';
import { useState } from 'react';
export default function ClientProviders({ children }) {
    const [queryClient] = useState(() => new QueryClient({
        defaultOptions: {
            queries: {
                staleTime: 10000,
                refetchOnWindowFocus: false,
                retry: 1,
            },
        },
    }));

    return (
        <QueryClientProvider client={queryClient}>
            <ThemeProvider>
                <ToastProvider>
                    <AuthProvider>
                        <UserPreferencesProvider>
                            <NotificationProvider>
                                <DocumentProvider>
                                    <FocusManager />
                                    <DynamicMeta />
                                    {children}
                                </DocumentProvider>
                            </NotificationProvider>
                        </UserPreferencesProvider>
                    </AuthProvider>
                </ToastProvider>
            </ThemeProvider>
        </QueryClientProvider>
    );
}
