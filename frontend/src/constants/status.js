// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI

export const STATUS = {
    PENDING: 'PENDING',
    PROCESSING: 'PROCESSING',
    COMPLETED: 'COMPLETED',
    COMPLETED_WITH_WARNINGS: 'COMPLETED_WITH_WARNINGS',
    FAILED: 'FAILED',
    CANCELLED: 'CANCELLED',
};

export function isCompleted(status) {
    return status?.toUpperCase() === STATUS.COMPLETED
        || status?.toUpperCase() === STATUS.COMPLETED_WITH_WARNINGS;
}

export function isProcessing(status) {
    const s = status?.toUpperCase();
    return s === STATUS.PROCESSING;
}

export function isFailed(status) {
    return status?.toUpperCase() === STATUS.FAILED;
}
