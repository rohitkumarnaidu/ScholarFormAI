// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

const METRIC_NAME = 'http_request_duration_seconds';
const METRIC_HELP = 'Duration of HTTP requests in seconds';
const METRIC_TYPE = 'histogram';
const METRIC_CONTENT_TYPE = 'text/plain; version=0.0.4; charset=utf-8';
const BUCKETS = [0.1, 0.3, 0.5, 0.7, 1, 3, 5, 7, 10];

const histogramStore = new Map();

const sanitizeLabelValue = (value) => (
    String(value ?? 'unknown')
        .replace(/\\/g, '\\\\')
        .replace(/"/g, '\\"')
        .replace(/\n/g, '\\n')
);

const getLabelKey = ({ method, route, status_code: statusCode }) => (
    `${method}|${route}|${statusCode}`
);

const parseLabelKey = (key) => {
    const [method, route, statusCode] = String(key).split('|');
    return {
        method,
        route,
        status_code: statusCode,
    };
};

const buildLabels = (labels = {}, extra = {}) => {
    const combined = {
        method: sanitizeLabelValue(labels.method),
        route: sanitizeLabelValue(labels.route),
        status_code: sanitizeLabelValue(labels.status_code),
        ...extra,
    };

    return `{method="${combined.method}",route="${combined.route}",status_code="${combined.status_code}"${extra.le !== undefined ? `,le="${combined.le}"` : ''}}`;
};

const ensureEntry = (labels) => {
    const key = getLabelKey(labels);
    if (!histogramStore.has(key)) {
        histogramStore.set(key, {
            count: 0,
            sum: 0,
            bucketCounts: BUCKETS.map(() => 0),
        });
    }
    return histogramStore.get(key);
};

export const httpRequestDurationMicroseconds = {
    observe(labels = {}, durationSeconds = 0) {
        const normalizedLabels = {
            method: sanitizeLabelValue(labels.method),
            route: sanitizeLabelValue(labels.route),
            status_code: sanitizeLabelValue(labels.status_code),
        };

        const numericDuration = Number(durationSeconds);
        const value = Number.isFinite(numericDuration) && numericDuration >= 0 ? numericDuration : 0;
        const entry = ensureEntry(normalizedLabels);

        entry.count += 1;
        entry.sum += value;

        BUCKETS.forEach((bucket, index) => {
            if (value <= bucket) {
                entry.bucketCounts[index] += 1;
            }
        });
    },
};

const renderHistogramMetric = () => {
    const lines = [
        `# HELP ${METRIC_NAME} ${METRIC_HELP}`,
        `# TYPE ${METRIC_NAME} ${METRIC_TYPE}`,
    ];

    for (const [key, entry] of histogramStore.entries()) {
        const labels = parseLabelKey(key);
        let cumulative = 0;

        BUCKETS.forEach((bucket, index) => {
            cumulative = entry.bucketCounts[index];
            lines.push(`${METRIC_NAME}_bucket${buildLabels(labels, { le: bucket })} ${cumulative}`);
        });

        lines.push(`${METRIC_NAME}_bucket${buildLabels(labels, { le: '+Inf' })} ${entry.count}`);
        lines.push(`${METRIC_NAME}_sum${buildLabels(labels)} ${entry.sum}`);
        lines.push(`${METRIC_NAME}_count${buildLabels(labels)} ${entry.count}`);
    }

    return lines.join('\n');
};

const registry = {
    contentType: METRIC_CONTENT_TYPE,
    async metrics() {
        return renderHistogramMetric();
    },
};

export default registry;
