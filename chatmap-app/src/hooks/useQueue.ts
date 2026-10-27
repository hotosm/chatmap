import {useCallback, useEffect, useState} from 'react';

import {onQueueChanged} from '../queue/events';
import {listForMap, type QueueItem} from '../queue/store';
import {getDatabase} from '../storage/database';

export function useQueue(mapId: string): QueueItem[] {
    const [items, setItems] = useState<QueueItem[]>([]);

    const load = useCallback(async () => {
        setItems(await listForMap(await getDatabase(), mapId));
    }, [mapId]);

    useEffect(() => {
        const reload = () => load().catch((error) => console.warn('Loading the queue failed', error));

        reload();

        return onQueueChanged(reload);
    }, [load]);

    return items;
}
