import {fetch as expoFetch} from 'expo/fetch';

import {API_URL} from '../config';
import {connectivity} from '../connectivity/connectivity';

type UploadInit = NonNullable<Parameters<typeof expoFetch>[1]>;

async function tracked<T>(request: () => Promise<T>): Promise<T> {
    let response: T;

    try {
        response = await request();
    } catch (error) {
        connectivity.reportUnreachable();
        throw error;
    }

    connectivity.reportReachable();

    return response;
}

export function apiFetch(path: string, init?: RequestInit): Promise<Response> {
    return tracked(() => fetch(`${API_URL}${path}`, init));
}

export function apiUpload(path: string, init: UploadInit) {
    return tracked(() => expoFetch(`${API_URL}${path}`, init));
}

export function withTimeout<T>(ms: number, run: (signal: AbortSignal) => Promise<T>): Promise<T> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), ms);

    return run(controller.signal).finally(() => clearTimeout(timer));
}
