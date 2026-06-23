// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

import { fetchWithAuth, sanitizePayload, sendFrontendErrorLog } from './api.core';

import { getV1, unwrapResponse } from './api.v1';

const formatStatusLabel = (value) => String(value || 'unknown').replace(/_/g, ' ');

const normalizeIndicatorStatus = (value) => {
    const normalized = String(value || 'unknown').toLowerCase();

    if (['healthy', 'ready', 'loaded', 'connected', 'success'].includes(normalized)) {
        return 'healthy';
    }

    if (['degraded', 'partial', 'warning', 'model_missing'].includes(normalized)) {
        return 'degraded';
    }

    if (['unavailable', 'unhealthy', 'failed', 'error', 'not_loaded', 'disconnected'].includes(normalized)) {
        return 'unavailable';
    }

    return 'unknown';
};

const summarizeProviders = (providers) => {
    const entries = Object.entries(providers || {});
    if (!entries.length) {
        return 'No provider data';
    }

    return entries
        .map(([name, status]) => `${name.toUpperCase()}: ${formatStatusLabel(status)}`)
        .join(' | ');
};

const normalizeHealthPayload = (payload) => {
    const checks = payload?.checks || {};
    const llmStatus = checks.llm_status || {};
    const aiModelsStatus = normalizeIndicatorStatus(checks.ai_models);
    const providerStatuses = Object.values(llmStatus).map(normalizeIndicatorStatus);

    let aiServicesStatus = aiModelsStatus;
    if (aiModelsStatus === 'healthy' && providerStatuses.some((status) => status === 'healthy')) {
        aiServicesStatus = 'healthy';
    } else if (providerStatuses.some((status) => status === 'healthy' || status === 'degraded')) {
        aiServicesStatus = 'degraded';
    } else if (providerStatuses.length) {
        aiServicesStatus = 'unavailable';
    }

    const readinessDetails = [
        payload?.ready ? 'Ready for traffic' : 'Readiness checks degraded',
        `Database ${formatStatusLabel(checks.database)}`,
        `Models ${formatStatusLabel(checks.ai_models)}`,
    ].join(' | ');

    return {
        ...payload,
        status: payload?.ready ? 'healthy' : 'degraded',
        details: readinessDetails,
        aiServicesStatus,
        aiServicesDetails: summarizeProviders(llmStatus),
        grobidStatus: normalizeIndicatorStatus(checks.grobid),
        grobidDetails: `Parser ${formatStatusLabel(checks.grobid)}`,
    };
};

const average = (values) => {
    if (!values.length) {
        return null;
    }
    return values.reduce((sum, value) => sum + value, 0) / values.length;
};

const normalizeDashboardPayload = (payload) => {
    const summary = payload?.live_metrics_summary || {};
    const comparison = payload?.live_model_comparison || {};
    const modelStats = summary.models || {};
    const modelEntries = Object.entries(modelStats);

    const totalProcessed = modelEntries.reduce(
        (sum, [, stats]) => sum + (Number(stats?.total_calls) || 0),
        0
    );
    const totalSuccessful = modelEntries.reduce(
        (sum, [, stats]) => sum + (Number(stats?.successful_calls) || 0),
        0
    );
    const totalFailed = modelEntries.reduce(
        (sum, [, stats]) => sum + (Number(stats?.failed_calls) || 0),
        0
    );
    const latencyValues = modelEntries
        .filter(([, stats]) => Number(stats?.total_calls) > 0)
        .map(([, stats]) => Number(stats?.avg_latency) || 0);
    const qualityValues = Object.values(summary.avg_quality_scores || {})
        .map((score) => Number(score))
        .filter((score) => Number.isFinite(score) && score > 0);

    const mostActiveModel = modelEntries.reduce((selected, entry) => {
        if (!selected) {
            return entry;
        }
        return (Number(entry[1]?.total_calls) || 0) > (Number(selected[1]?.total_calls) || 0) ? entry : selected;
    }, null);

    const abTestingSummary = payload?.live_ab_test_summary;

    return {
        ...payload,
        successRatePct: totalProcessed > 0 ? (totalSuccessful / totalProcessed) * 100 : null,
        avgConfidencePct: qualityValues.length ? average(qualityValues) * 100 : null,
        errorRatePct: totalProcessed > 0 ? (totalFailed / totalProcessed) * 100 : null,
        totalProcessed,
        avgProcessingTimeSeconds: average(latencyValues),
        modelLabel: mostActiveModel ? mostActiveModel[0].toUpperCase() : 'No model activity yet',
        automationLevel: comparison?.agent_vs_legacy?.automation_level || 'Unknown',
        fallbackRatePct: typeof summary.fallback_rate === 'number' ? summary.fallback_rate * 100 : null,
        abTesting: abTestingSummary && !abTestingSummary.message ? abTestingSummary : null,
    };
};

export const logFrontendError = async (errorInfo) => {
    await sendFrontendErrorLog(errorInfo);
};

export const submitFeedback = async (data) => {
    const sanitizedData = sanitizePayload(data);
    return fetchWithAuth('/api/v1/feedback/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(sanitizedData),
    });
};

export const getFeedbackSummary = async (jobId) => {
    return fetchWithAuth(`/api/v1/feedback/summary?document_id=${encodeURIComponent(jobId)}`);
};

export const getMetricsDb = async () => {
    try {
        return await fetchWithAuth('/api/v1/metrics/db', {
            suppressConsoleError: true,
            suppressMonitoring: true,
        });
    } catch {
        return null;
    }
};

export const getMetricsHealth = async () => {
    try {
        const res = await getV1('/health/ready', { suppressConsoleError: true });
        return normalizeHealthPayload(unwrapResponse(res));
    } catch {
        return null;
    }
};

export const getMetricsDashboard = async () => {
    try {
        const payload = await fetchWithAuth('/api/v1/metrics/dashboard', {
            suppressConsoleError: true,
            suppressMonitoring: true,
        });
        return normalizeDashboardPayload(payload);
    } catch {
        return null;
    }
};

export const getMetricsEnhancements = async () => {
    return fetchWithAuth('/api/v1/metrics/enhancements');
};
