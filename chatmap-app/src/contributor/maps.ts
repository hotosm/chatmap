import {apiFetch} from '../api/client';
import type {StoredMap} from '../storage/maps';
import {getSecret} from './secret';

type MapsResponse = {
    maps: {
        map_id: string;
        map_name: string | null;
        role: 'owner' | 'contributor';
        nickname: string | null;
    }[];
};

export async function fetchMaps(signal?: AbortSignal): Promise<StoredMap[]> {
    const response = await apiFetch('/v2/maps', {
        headers: {Authorization: `Contributor ${await getSecret()}`},
        signal,
    });

    if (!response.ok) {
        throw new Error(`Unexpected response listing maps (${response.status})`);
    }

    const body: MapsResponse = await response.json();

    return body.maps.flatMap((map) =>
        map.role === 'contributor' && map.nickname !== null
            ? [{mapId: map.map_id, mapName: map.map_name, nickname: map.nickname}]
            : [],
    );
}
