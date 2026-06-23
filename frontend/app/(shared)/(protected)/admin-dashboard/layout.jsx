// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import AuthGuard from '@/src/components/layout/AuthGuard';

export default function AdminDashboardLayout({ children }) {
    return <AuthGuard requireAdmin>{children}</AuthGuard>;
}
