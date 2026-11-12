import {getDatabase} from '../storage/database';
import {replaceMaps, type MapRemoval, type StoredMap} from '../storage/maps';
import {fetchMaps} from './maps';

const REFRESH_TIMEOUT_MS = 10000;

const listeners = new Set<() => void>();
const removalListeners = new Set<(removed: MapRemoval[]) => void>();
let inFlight: Promise<void> | null = null;

export function onMapsChanged(listener: () => void): () => void {
    listeners.add(listener);

    return () => {
        listeners.delete(listener);
    };
}

export function onMapsRemoved(listener: (removed: MapRemoval[]) => void): () => void {
    removalListeners.add(listener);

    return () => {
        removalListeners.delete(listener);
    };
}

async function fetchWithTimeout(): Promise<StoredMap[]> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), REFRESH_TIMEOUT_MS);

    try {
        return await fetchMaps(controller.signal);
    } finally {
        clearTimeout(timer);
    }
}

async function run(): Promise<void> {
    const fetched = await fetchWithTimeout();

    const removed = await replaceMaps(await getDatabase(), fetched, new Date());

    for (const listener of listeners) {
        listener();
    }

    if (removed.length > 0) {
        for (const listener of removalListeners) {
            listener(removed);
        }
    }
}

export function refreshMaps(): Promise<void> {
    inFlight ??= run().finally(() => {
        inFlight = null;
    });

    return inFlight;
}
