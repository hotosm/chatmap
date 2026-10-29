const apiUrl = process.env.EXPO_PUBLIC_API_URL;

if (!apiUrl) {
    throw new Error('EXPO_PUBLIC_API_URL is not set. Copy .env.example to .env.local and set the server address.');
}

export const API_URL = apiUrl.replace(/\/+$/, '');

function positiveNumber(value: string | undefined, fallback: number): number {
    const parsed = Number(value);

    return value && Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

export const HEALTH = {
    intervalMs: positiveNumber(process.env.EXPO_PUBLIC_HEALTH_INTERVAL_MS, 30000),
    timeoutMs: positiveNumber(process.env.EXPO_PUBLIC_HEALTH_TIMEOUT_MS, 5000),
    failuresToOffline: positiveNumber(process.env.EXPO_PUBLIC_HEALTH_FAILURES_TO_OFFLINE, 2),
    retryMinMs: positiveNumber(process.env.EXPO_PUBLIC_HEALTH_RETRY_MIN_MS, 5000),
    retryMaxMs: positiveNumber(process.env.EXPO_PUBLIC_HEALTH_RETRY_MAX_MS, 60000),
};
