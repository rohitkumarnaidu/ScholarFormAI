// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import { useDocument } from '../context/DocumentContext';
import { getJobSummary } from '@/services/api';

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
    const { jobId } = useParams();
    const { job, setJob } = useDocument();
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');

    const hasMatchingJobInContext = useMemo(
        () => Boolean(jobId && job?.id && String(job.id) === String(jobId)),
        [job?.id, jobId]
    );

    useEffect(() => {
        let isCancelled = false;

        if (!jobId) {
            setIsLoading(false);
            setError('');
            return undefined;
        }

        if (hasMatchingJobInContext) {
            setIsLoading(false);
            setError('');
            return undefined;
        }

        setIsLoading(true);
        setError('');

        getJobSummary(jobId)
            .then((summary) => {
                if (isCancelled) {
                    return;
                }
                setJob(normalizeSummaryToJob(summary, jobId));
            })
            .catch((fetchError) => {
                if (isCancelled) {
                    return;
                }
                const message = typeof fetchError?.message === 'string'
                    ? fetchError.message
                    : 'Unable to load document details.';
                setError(message);
            })
            .finally(() => {
                if (!isCancelled) {
                    setIsLoading(false);
                }
            });

        return () => {
            isCancelled = true;
        };
    }, [hasMatchingJobInContext, jobId, setJob]);

    if (!jobId) {
        return { job, isLoading: false, error: '' };
    }

    return {
        job: hasMatchingJobInContext ? job : null,
        isLoading,
        error,
    };
}
