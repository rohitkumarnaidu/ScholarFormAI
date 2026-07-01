'use client';

const RETRYABLE_STATUSES = new Set([429, 502, 503, 504]);
const MAX_RETRIES = 3;
const BASE_DELAY = 1000;

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

export async function fetchWithRetry(url, options = {}, retries = MAX_RETRIES) {
    for (let attempt = 0; attempt <= retries; attempt++) {
        try {
            const res = await fetch(url, options);
            if (res.ok || !RETRYABLE_STATUSES.has(res.status)) {
                return res;
            }
            if (attempt === retries) {
                return res;
            }
            const retryAfter = parseInt(res.headers.get('Retry-After') || '0', 10);
            const delay = retryAfter > 0 ? retryAfter * 1000 : BASE_DELAY * Math.pow(2, attempt) + Math.random() * 500;
            await sleep(delay);
        } catch (err) {
            if (attempt === retries) throw err;
            const delay = BASE_DELAY * Math.pow(2, attempt) + Math.random() * 500;
            await sleep(delay);
        }
    }
}
