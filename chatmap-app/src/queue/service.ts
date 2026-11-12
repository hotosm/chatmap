import {getDatabase} from '../storage/database';
import {requestSync} from '../sync';
import {emitQueueChanged} from './events';
import {deleteMedia, exclusiveMedia, persistMedia} from './media';
import {closeItem, closeMap, openPoint} from './open';
import {attachMedia, deleteItem, enqueuePoint} from './store';

export async function capturePoint(mapId: string, latitude: number, longitude: number): Promise<number> {
    const id = await enqueuePoint(await getDatabase(), {
        mapId,
        capturedAt: new Date().toISOString(),
        latitude,
        longitude,
        message: null,
    });

    openPoint(mapId, id);
    emitQueueChanged();
    requestSync();

    return id;
}

export async function addMedia(itemId: number, temporaryUri: string): Promise<boolean> {
    const capturedAt = new Date().toISOString();

    const attached = await exclusiveMedia(async () => {
        const uri = await persistMedia(temporaryUri);
        const done = await attachMedia(await getDatabase(), itemId, uri, capturedAt);

        if (!done) {
            deleteMedia(uri);
        }

        return done;
    });

    deleteMedia(temporaryUri);
    closeItem(itemId);
    emitQueueChanged();
    requestSync();

    return attached;
}

export function leaveMap(mapId: string): void {
    closeMap(mapId);
    requestSync();
}

export async function dismissItem(itemId: number): Promise<void> {
    const uri = await deleteItem(await getDatabase(), itemId);

    if (uri) {
        deleteMedia(uri);
    }

    closeItem(itemId);
    emitQueueChanged();
}
