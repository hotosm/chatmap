import {useCallback, useEffect, useState} from 'react';

import {connectivity, useConnectivity} from '../connectivity/connectivity';
import {fetchHistory, type HistoryPoint} from '../contributor/history';
import {refreshMaps} from '../contributor/refreshMaps';
import {onQueueChanged} from '../queue/events';

type Status = 'idle' | 'forbidden' | 'error';

type History = {
    points: HistoryPoint[];
    next: string | null;
};

const RELOAD_DELAY_MS = 800;

function newestFirst(a: HistoryPoint, b: HistoryPoint): number {
    return Date.parse(b.time) - Date.parse(a.time) || (a.id < b.id ? 1 : -1);
}

function merge(...lists: HistoryPoint[][]): HistoryPoint[] {
    const seen = new Set<string>();
    const merged: HistoryPoint[] = [];

    for (const point of lists.flat().sort(newestFirst)) {
        if (!seen.has(point.id)) {
            seen.add(point.id);
            merged.push(point);
        }
    }

    return merged;
}

export function useHistory(mapId: string) {
    const [history, setHistory] = useState<History>({points: [], next: null});
    const [status, setStatus] = useState<Status>('idle');
    const [loadingOlder, setLoadingOlder] = useState(false);
    const online = useConnectivity() === 'online';

    const reload = useCallback(
        () =>
            fetchHistory(mapId, null)
                .then((result) => {
                    if (result.status === 'forbidden') {
                        setStatus('forbidden');
                        refreshMaps().catch((error) => console.warn('Refreshing the maps failed', error));
                        return;
                    }

                    setHistory((current) => {
                        const oldest = result.page.points.at(-1);
                        const older = oldest
                            ? current.points.filter((point) => Date.parse(point.time) <= Date.parse(oldest.time))
                            : [];

                        if (older.length > 0 && result.page.next !== null) {
                            return {points: merge(result.page.points, older), next: current.next};
                        }

                        return {points: result.page.points, next: result.page.next};
                    });
                    setStatus('idle');
                })
                .catch((error) => {
                    console.warn('Loading the history failed', error);
                    setStatus('error');
                }),
        [mapId],
    );

    const loadOlder = useCallback(async () => {
        if (history.next === null || loadingOlder) {
            return;
        }

        setLoadingOlder(true);

        try {
            const result = await fetchHistory(mapId, history.next);

            if (result.status === 'ok') {
                setHistory((current) => ({points: merge(current.points, result.page.points), next: result.page.next}));
            }
        } catch (error) {
            console.warn('Loading older history failed', error);
        } finally {
            setLoadingOlder(false);
        }
    }, [mapId, history.next, loadingOlder]);

    useEffect(() => {
        if (online) {
            void reload();
        }
    }, [online, reload]);

    useEffect(() => {
        let timer: ReturnType<typeof setTimeout> | null = null;

        const unsubscribe = onQueueChanged(() => {
            if (connectivity.getState() !== 'online') {
                return;
            }

            if (timer !== null) {
                clearTimeout(timer);
            }

            timer = setTimeout(() => void reload(), RELOAD_DELAY_MS);
        });

        return () => {
            unsubscribe();

            if (timer !== null) {
                clearTimeout(timer);
            }
        };
    }, [reload]);

    return {points: history.points, hasOlder: history.next !== null, status, loadingOlder, loadOlder, reload, online};
}
