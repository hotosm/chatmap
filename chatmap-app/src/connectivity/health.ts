import {API_URL, HEALTH} from '../config';

export async function checkHealth(): Promise<boolean> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), HEALTH.timeoutMs);

    try {
        const response = await fetch(`${API_URL}/v2/health`, {
            headers: {'Cache-Control': 'no-cache'},
            signal: controller.signal,
        });

        return response.ok;
    } catch {
        return false;
    } finally {
        clearTimeout(timer);
    }
}
