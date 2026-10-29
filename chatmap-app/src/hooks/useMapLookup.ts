import {useCallback, useEffect, useState} from 'react';

import {onMapsChanged} from '../contributor/refreshMaps';
import {getDatabase} from '../storage/database';
import {listMaps, type StoredMap} from '../storage/maps';

type Lookup =
    | {status: 'loading'}
    | {status: 'found'; map: StoredMap}
    | {status: 'missing'};

export function useMapLookup(mapId: string): Lookup {
    const [lookup, setLookup] = useState<Lookup>({status: 'loading'});

    const load = useCallback(async () => {
        const map = (await listMaps(await getDatabase())).find((stored) => stored.mapId === mapId);

        setLookup(map ? {status: 'found', map} : {status: 'missing'});
    }, [mapId]);

    useEffect(() => {
        const reload = () => load().catch((error) => console.warn('Looking the map up failed', error));

        reload();

        return onMapsChanged(reload);
    }, [load]);

    return lookup;
}
