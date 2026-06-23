// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { notFound } from 'next/navigation';
import React from 'react';

import DownloadPage from '@/app/(formatter)/download/page';
import ComparePage from '@/app/(formatter)/compare/page';
import EditPage from '@/app/(formatter)/edit/page';
import ValidationResultsPage from '@/app/(formatter)/results/page';
import PreviewPage from '@/app/(formatter)/preview/page';

// Next.js 15: params is a Promise — must be awaited in async server components
export default async function JobStepPage({ params }) {
    const { step } = await params;
    const stepStr = String(step || '');

    const allowedSteps = ['download', 'compare', 'edit', 'results', 'preview'];

    if (!allowedSteps.includes(stepStr)) {
        notFound();
    }

    switch (stepStr) {
        case 'download':
            return <DownloadPage />;
        case 'compare':
            return <ComparePage />;
        case 'edit':
            return <EditPage />;
        case 'results':
            return <ValidationResultsPage />;
        case 'preview':
            return <PreviewPage />;
        default:
            notFound();
    }
}
