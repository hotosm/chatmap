import {useEffect, useState} from 'react';

import type {Entry} from '../components/map/PointEntry';
import {API_URL} from '../config';
import {getSecret} from '../contributor/secret';
import {kindOfContentType, kindOfUri} from '../queue/media';
import type {QueueItem} from '../queue/store';
import {useHistory} from './useHistory';
import {useQueue} from './useQueue';

// Delivered items that already left the queue, by point id, so the screen can keep showing them
// until the history brings them back from the server
type Held = Map<string, QueueItem>;

function useAuthorization(): Record<string, string> | null {
    const [headers, setHeaders] = useState<Record<string, string> | null>(null);

    useEffect(() => {
        getSecret()
            .then((secret) => setHeaders({Authorization: `Contributor ${secret}`}))
            .catch((error) => console.warn('Reading the contributor secret failed', error));
    }, []);

    return headers;
}

function isDelivered(item: QueueItem): boolean {
    return item.pointState === 'created' && (item.mediaState === null || item.mediaState === 'uploaded');
}

function holdDelivered(held: Held, previous: QueueItem[], current: QueueItem[]): Held {
    const remaining = new Set(current.map((item) => item.id));
    const left = previous.filter((item) => !remaining.has(item.id) && item.pointId !== null && isDelivered(item));

    if (left.length === 0) {
        return held;
    }

    const next = new Map(held);

    for (const item of left) {
        next.set(item.pointId as string, item);
    }

    return next;
}

function queueEntry(item: QueueItem): Entry {
    return {
        key: `queue:${item.id}`,
        time: Date.parse(item.capturedAt),
        latitude: item.latitude,
        longitude: item.longitude,
        point: item.pointState,
        media: item.mediaUri
            ? {
                kind: kindOfUri(item.mediaUri),
                source: {uri: item.mediaUri},
                time: item.mediaCapturedAt ? Date.parse(item.mediaCapturedAt) : null,
                state: item.mediaState ?? 'waiting',
            }
            : null,
        rejection: item.rejection,
        queueId: item.id,
    };
}

export function useEntries(mapId: string) {
    const queued = useQueue(mapId);
    const history = useHistory(mapId);
    const headers = useAuthorization();
    const [previousQueue, setPreviousQueue] = useState(queued);
    const [held, setHeld] = useState<Held>(() => new Map());

    if (queued !== previousQueue) {
        setPreviousQueue(queued);
        setHeld(holdDelivered(held, previousQueue, queued));
    }

    const queuedPointIds = new Set(queued.flatMap((item) => (item.pointId ? [item.pointId] : [])));

    const fromServer: Entry[] = headers
        ? history.points
            .filter((point) => !queuedPointIds.has(point.id))
            .map((point) => ({
                // Same key as while it was queued, so the bubble updates in place instead of remounting
                key: held.has(point.id) ? `queue:${held.get(point.id)?.id}` : `server:${point.id}`,
                time: Date.parse(point.time),
                latitude: point.latitude,
                longitude: point.longitude,
                point: 'created',
                media: point.media
                    ? {
                        kind: kindOfContentType(point.media.contentType),
                        source: {uri: `${API_URL}/v2/media/${encodeURIComponent(point.media.id)}`, headers},
                        time: point.media.capturedAt ? Date.parse(point.media.capturedAt) : null,
                        state: 'uploaded',
                    }
                    : null,
                rejection: null,
                queueId: null,
            }))
        : [];

    const shownFromServer = new Set(fromServer.map((entry) => entry.key));

    const fromHeld: Entry[] = [...held.values()]
        .map((item) => ({...queueEntry(item), queueId: null}))
        .filter((entry) => !shownFromServer.has(entry.key));

    const entries = [...fromServer, ...fromHeld, ...queued.map(queueEntry)].sort((a, b) => a.time - b.time);

    return {
        entries,
        hasOlder: history.hasOlder,
        status: history.status,
        loadingOlder: history.loadingOlder,
        loadOlder: history.loadOlder,
        reload: history.reload,
        online: history.online,
    };
}
