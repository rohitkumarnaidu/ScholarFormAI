// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

'use client';

import React, { useEffect } from 'react';
import Button from '@/src/components/ui/Button';
import EmptyState from '@/src/components/ui/EmptyState';
import { AlertCircle } from 'lucide-react';

export default function Error({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    useEffect(() => {
        console.error('Job error:', error);
    }, [error]);

    return (
        <div className="flex flex-col items-center justify-center min-h-[400px] p-6">
            <EmptyState
                icon={AlertCircle}
                title="Job Error"
                description={error.message || "An unexpected error occurred while loading this job."}
                action={
                    <div className="flex gap-4 mt-2">
                        <Button variant="secondary" onClick={() => window.history.back()}>
                            Go Back
                        </Button>
                        <Button onClick={() => reset()}>
                            Try Again
                        </Button>
                    </div>
                }
            />
        </div>
    );
}
