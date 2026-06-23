// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import AuthGuard from '@/src/components/layout/AuthGuard';

export default function GeneratorProtectedLayout({ children }) {
    return <AuthGuard>{children}</AuthGuard>;
}
