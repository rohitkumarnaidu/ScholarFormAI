// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { useMemo } from 'react';
import { useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { useDocument } from '../context/DocumentContext';
import { getJobSummary } from '@/services/api.documents';

const normalizeSummaryToJob = (summary, fallbackId) => {
    const filename = summary?.filename
        || summary?.original_file_name
        || summary?.originalFileName
        || 'Untitled';
    const createdAt = summary?.created_at || summary?.timestamp || summary?.updated_at || new Date().toISOString();

    return {
        ...summary,
        id: String(summary?.id || fallbackId || ''),
        filename,
        original_file_name: summary?.original_file_name || filename,
        originalFileName: filename,
        created_at: summary?.created_at || createdAt,
        timestamp: createdAt,
        outputPath: summary?.output_path || summary?.outputPath || null,
    };
};

export default function useJobFromUrl() {
    const searchParams = useSearchParams();
    const jobId = searchParams?.get('jobId') || null;
    const { job, setJob } = useDocument();

    const hasMatchingJobInContext = useMemo(
        () => Boolean(jobId && job?.id && String(job.id) === String(jobId)),
        [job?.id, jobId]
    );

    const { data, isLoading, error } = useQuery({
        queryKey: ['jobSummary', jobId],
        queryFn: () => getJobSummary(jobId),
        enabled: Boolean(jobId) && !hasMatchingJobInContext,
        staleTime: 5 * 60 * 1000, // 5 minutes
    });

    // Sync fetched data to context
    useMemo(() => {
        if (data && !hasMatchingJobInContext) {
            setJob(normalizeSummaryToJob(data, jobId));
        }
    }, [data, hasMatchingJobInContext, jobId, setJob]);

    if (!jobId) {
        return { job, isLoading: false, error: '' };
    }

    const resolvedError = error ? (typeof error.message === 'string' ? error.message : 'Unable to load document details.') : '';

    return {
        job: hasMatchingJobInContext ? job : normalizeSummaryToJob(data, jobId),
        isLoading,
        error: resolvedError,
    };
}
