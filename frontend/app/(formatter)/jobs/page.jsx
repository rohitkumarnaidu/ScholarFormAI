// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

// /jobs has no index page — jobs are only accessible via /jobs/[jobId]/...
// Redirect to /history where users can browse all their jobs.
export default function JobsIndex() {
    const router = useRouter();
    useEffect(() => {
        router.replace('/history');
    }, [router]);
    return null;
}
