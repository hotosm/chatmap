import {useFocusEffect} from 'expo-router';
import {useCallback, useEffect, useState} from 'react';

import {connectivity} from '../connectivity/connectivity';
import {onMapsChanged, refreshMaps} from '../contributor/refreshMaps';
import {getDatabase} from '../storage/database';
import {lastRefresh, listMaps, type StoredMap} from '../storage/maps';

export function useMaps() {
    const [maps, setMaps] = useState<StoredMap[]>([]);
    const [refreshedAt, setRefreshedAt] = useState<Date | null>(null);
    const [loaded, setLoaded] = useState(false);
    const [refreshing, setRefreshing] = useState(false);
    const [failed, setFailed] = useState(false);

    const load = useCallback(async () => {
        const db = await getDatabase();

        setMaps(await listMaps(db));
        setRefreshedAt(await lastRefresh(db));
        setLoaded(true);
    }, []);

    const refresh = useCallback(async () => {
        setRefreshing(true);
        setFailed(false);

        try {
            await refreshMaps();
        } catch (error) {
            console.warn('Refreshing the maps failed', error);
            setFailed(true);
        } finally {
            setRefreshing(false);
        }
    }, []);

    useEffect(
        () => onMapsChanged(() => {
            load().catch((error) => console.warn('Loading the saved maps failed', error));
        }),
        [load],
    );

    useFocusEffect(
        useCallback(() => {
            load().catch((error) => console.warn('Loading the saved maps failed', error));

            if (connectivity.getState() === 'online') {
                void refresh();
            }
        }, [load, refresh]),
    );

    return {maps, refreshedAt, loaded, refreshing, failed, refresh};
}
