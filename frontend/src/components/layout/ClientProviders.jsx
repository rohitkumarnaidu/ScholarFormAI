// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from '@/src/context/ThemeContext';
import { AuthProvider } from '@/src/context/AuthContext';
import { ToastProvider } from '@/src/context/ToastContext';
import { DocumentProvider } from '@/src/context/DocumentContext';
import { UserPreferencesProvider } from '@/src/context/UserPreferencesContext';
import FocusManager from '@/src/components/layout/FocusManager';
import DynamicMeta from '@/src/components/layout/DynamicMeta';
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
                            <DocumentProvider>
                                <FocusManager />
                                <DynamicMeta />
                                {children}
                            </DocumentProvider>
                        </UserPreferencesProvider>
                    </AuthProvider>
                </ToastProvider>
            </ThemeProvider>
        </QueryClientProvider>
    );
}
