// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import AuthGuard from '@/src/components/layout/AuthGuard';
import AppShell from '@/src/components/layout/AppShell';
import { ToastProvider } from '@/src/components/Toast';
import { ConfirmProvider } from '@/src/components/ConfirmDialog';

export default function SharedProtectedLayout({ children }) {
    return (
        <AuthGuard>
            <AppShell section="shared">
                <ToastProvider>
                    <ConfirmProvider>
                        {children}
                    </ConfirmProvider>
                </ToastProvider>
            </AppShell>
        </AuthGuard>
    );
}
