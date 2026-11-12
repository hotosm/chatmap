import {apiFetch} from '../api/client';
import type {StoredMap} from '../storage/maps';
import {getSecret} from './secret';

export type JoinedMap = Pick<StoredMap, 'mapId' | 'mapName'>;

export type JoinOutcome =
    | {status: 'joined'; map: JoinedMap}
    | {status: 'already-member'; map: JoinedMap}
    | {status: 'invalid-invitation'}
    | {status: 'removed'};

type JoinResponse = {
    contributor_id: string;
    map_id: string;
    map_name: string;
};

async function readMap(response: Response): Promise<JoinedMap> {
    const body: JoinResponse = await response.json();

    return {mapId: body.map_id, mapName: body.map_name};
}

export async function joinMap(token: string, nickname: string): Promise<JoinOutcome> {
    const response = await apiFetch('/v2/invitations/join', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({token, nickname, secret: await getSecret()}),
    });

    if (response.status === 201) {
        return {status: 'joined', map: await readMap(response)};
    }

    if (response.status === 200) {
        return {status: 'already-member', map: await readMap(response)};
    }

    if (response.status === 404) {
        return {status: 'invalid-invitation'};
    }

    if (response.status === 403) {
        return {status: 'removed'};
    }

    throw new Error(`Unexpected response joining a map (${response.status})`);
}
