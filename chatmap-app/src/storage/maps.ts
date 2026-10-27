import {PENDING_WORK} from '../queue/store';
import type {Database} from './schema';

export type StoredMap = {
    mapId: string;
    mapName: string | null;
    nickname: string;
};

export type MapRemoval = {
    map: StoredMap;
    discarded: number;
};

type MapRow = {
    map_id: string;
    map_name: string | null;
    nickname: string;
};

const MAP_COLUMNS = 'map_id, map_name, nickname';

const REFRESHED_AT_KEY = 'maps_refreshed_at';

function toMap(row: MapRow): StoredMap {
    return {mapId: row.map_id, mapName: row.map_name, nickname: row.nickname};
}

export async function listMaps(db: Database): Promise<StoredMap[]> {
    const rows = await db.getAllAsync<MapRow>(`SELECT ${MAP_COLUMNS} FROM maps ORDER BY position`);

    return rows.map(toMap);
}

export async function lastRefresh(db: Database): Promise<Date | null> {
    const row = await db.getFirstAsync<{value: string}>('SELECT value FROM meta WHERE key = ?', REFRESHED_AT_KEY);

    return row ? new Date(row.value) : null;
}

export async function replaceMaps(db: Database, maps: StoredMap[], refreshedAt: Date): Promise<MapRemoval[]> {
    const kept = new Set(maps.map((map) => map.mapId));
    const removed: MapRemoval[] = [];

    await db.withExclusiveTransactionAsync(async (txn) => {
        const stored = await txn.getAllAsync<MapRow>(`SELECT ${MAP_COLUMNS} FROM maps`);

        for (const row of stored) {
            if (kept.has(row.map_id)) {
                continue;
            }

            const pending = await txn.getFirstAsync<{count: number}>(
                `SELECT COUNT(*) AS count FROM queue WHERE map_id = ? AND ${PENDING_WORK}`,
                row.map_id,
            );

            await txn.runAsync('DELETE FROM maps WHERE map_id = ?', row.map_id);
            removed.push({map: toMap(row), discarded: pending?.count ?? 0});
        }

        for (const [position, map] of maps.entries()) {
            await txn.runAsync(
                `INSERT INTO maps (map_id, map_name, nickname, position) VALUES (?, ?, ?, ?)
                 ON CONFLICT (map_id) DO UPDATE SET
                    map_name = excluded.map_name,
                    nickname = excluded.nickname,
                    position = excluded.position`,
                map.mapId,
                map.mapName,
                map.nickname,
                position,
            );
        }

        await txn.runAsync(
            `INSERT INTO meta (key, value) VALUES (?, ?)
             ON CONFLICT (key) DO UPDATE SET value = excluded.value`,
            REFRESHED_AT_KEY,
            refreshedAt.toISOString(),
        );
    });

    return removed;
}

export async function addMap(db: Database, map: StoredMap): Promise<void> {
    await db.runAsync(
        `INSERT INTO maps (map_id, map_name, nickname, position)
         VALUES (?, ?, ?, COALESCE((SELECT MAX(position) FROM maps), -1) + 1)
         ON CONFLICT (map_id) DO UPDATE SET
            map_name = excluded.map_name,
            nickname = excluded.nickname`,
        map.mapId,
        map.mapName,
        map.nickname,
    );
}
