import {AppState} from 'react-native';

import {HEALTH} from '../config';
import {connectivity} from '../connectivity/connectivity';
import {createPoint, uploadMedia} from '../contributor/points';
import {onMapsChanged, refreshMaps} from '../contributor/refreshMaps';
import {emitQueueChanged} from '../queue/events';
import {deleteMedia, exclusiveMedia, sweepMedia} from '../queue/media';
import {openItemIds} from '../queue/open';
import {
    deleteCompleted,
    markCreated,
    markMediaRejected,
    markMediaUploaded,
    markPointRejected,
    nextActionable,
    referencedMediaUris,
} from '../queue/store';
import {getDatabase} from '../storage/database';
import {SyncEngine} from './engine';

const engine = new SyncEngine(
    {
        isOnline: () => connectivity.getState() === 'online',
        next: async () => nextActionable(await getDatabase()),
        markCreated: async (id, pointId) => markCreated(await getDatabase(), id, pointId),
        markPointRejected: async (id, reason) => markPointRejected(await getDatabase(), id, reason),
        markMediaUploaded: async (id) => markMediaUploaded(await getDatabase(), id),
        markMediaRejected: async (id, reason) => markMediaRejected(await getDatabase(), id, reason),
        cleanup: async () => {
            const uris = await deleteCompleted(await getDatabase(), openItemIds());

            uris.forEach(deleteMedia);
        },
        createPoint,
        uploadMedia,
        onChange: emitQueueChanged,
        log: (message, error) => console.warn(message, error),
    },
    HEALTH,
);

export function requestSync(): void {
    engine.request();
}

async function sweepStoredMedia(): Promise<void> {
    await exclusiveMedia(async () => {
        sweepMedia(new Set(await referencedMediaUris(await getDatabase())));
    });
}

export function startSync(): () => void {
    const appState = AppState.addEventListener('change', (state) => {
        if (state === 'active') {
            engine.request();
        }
    });

    const reconnect = connectivity.onReconnect(() => {
        refreshMaps()
            .catch((error) => console.warn('Refreshing the maps after reconnecting failed', error))
            .finally(() => engine.restart());
    });

    const mapsChanged = onMapsChanged(() => {
        sweepStoredMedia().catch((error) => console.warn('Sweeping the stored media failed', error));
    });

    sweepStoredMedia().catch((error) => console.warn('Sweeping the stored media failed', error));
    engine.request();

    return () => {
        appState.remove();
        reconnect();
        mapsChanged();
    };
}
