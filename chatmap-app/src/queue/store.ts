import type {Database} from '../storage/schema';

export type PointState = 'unconfirmed' | 'created' | 'rejected';
export type MediaState = 'waiting' | 'uploaded' | 'rejected';

export type QueueItem = {
    id: number;
    mapId: string;
    capturedAt: string;
    latitude: number;
    longitude: number;
    message: string | null;
    mediaUri: string | null;
    mediaCapturedAt: string | null;
    pointState: PointState;
    mediaState: MediaState | null;
    pointId: string | null;
    rejection: string | null;
};

export type NewPoint = {
    mapId: string;
    capturedAt: string;
    latitude: number;
    longitude: number;
    message: string | null;
};

type QueueRow = {
    id: number;
    map_id: string;
    captured_at: string;
    latitude: number;
    longitude: number;
    message: string | null;
    media_uri: string | null;
    media_captured_at: string | null;
    point_state: PointState;
    media_state: MediaState | null;
    point_id: string | null;
    rejection: string | null;
};

const COLUMNS = `id, map_id, captured_at, latitude, longitude, message, media_uri, media_captured_at,
    point_state, media_state, point_id, rejection`;

export const PENDING_WORK = `(point_state = 'unconfirmed' OR (point_state = 'created' AND media_state = 'waiting'))`;

const COMPLETE = `point_state = 'created' AND (media_state IS NULL OR media_state = 'uploaded')`;

function toItem(row: QueueRow): QueueItem {
    return {
        id: row.id,
        mapId: row.map_id,
        capturedAt: row.captured_at,
        latitude: row.latitude,
        longitude: row.longitude,
        message: row.message,
        mediaUri: row.media_uri,
        mediaCapturedAt: row.media_captured_at,
        pointState: row.point_state,
        mediaState: row.media_state,
        pointId: row.point_id,
        rejection: row.rejection,
    };
}

export async function enqueuePoint(db: Database, point: NewPoint): Promise<number> {
    const result = await db.runAsync(
        'INSERT INTO queue (map_id, captured_at, latitude, longitude, message) VALUES (?, ?, ?, ?, ?)',
        point.mapId,
        point.capturedAt,
        point.latitude,
        point.longitude,
        point.message,
    );

    return result.lastInsertRowId;
}

export async function attachMedia(db: Database, id: number, mediaUri: string, capturedAt: string): Promise<boolean> {
    const result = await db.runAsync(
        `UPDATE queue SET media_uri = ?, media_captured_at = ?, media_state = 'waiting'
         WHERE id = ? AND media_uri IS NULL AND point_state != 'rejected'`,
        mediaUri,
        capturedAt,
        id,
    );

    return result.changes > 0;
}

export async function listForMap(db: Database, mapId: string): Promise<QueueItem[]> {
    const rows = await db.getAllAsync<QueueRow>(
        `SELECT ${COLUMNS} FROM queue WHERE map_id = ? ORDER BY captured_at, id`,
        mapId,
    );

    return rows.map(toItem);
}

export async function getItem(db: Database, id: number): Promise<QueueItem | null> {
    const row = await db.getFirstAsync<QueueRow>(`SELECT ${COLUMNS} FROM queue WHERE id = ?`, id);

    return row ? toItem(row) : null;
}

export async function nextActionable(db: Database): Promise<QueueItem | null> {
    const row = await db.getFirstAsync<QueueRow>(
        `SELECT ${COLUMNS} FROM queue
         WHERE ${PENDING_WORK}
         ORDER BY captured_at, id
         LIMIT 1`,
    );

    return row ? toItem(row) : null;
}

export async function markCreated(db: Database, id: number, pointId: string): Promise<void> {
    await db.runAsync(
        "UPDATE queue SET point_state = 'created', point_id = ?, rejection = NULL WHERE id = ?",
        pointId,
        id,
    );
}

export async function markPointRejected(db: Database, id: number, reason: string): Promise<void> {
    await db.runAsync("UPDATE queue SET point_state = 'rejected', rejection = ? WHERE id = ?", reason, id);
}

export async function markMediaUploaded(db: Database, id: number): Promise<void> {
    await db.runAsync("UPDATE queue SET media_state = 'uploaded' WHERE id = ?", id);
}

export async function markMediaRejected(db: Database, id: number, reason: string): Promise<void> {
    await db.runAsync("UPDATE queue SET media_state = 'rejected', rejection = ? WHERE id = ?", reason, id);
}

export async function deleteItem(db: Database, id: number): Promise<string | null> {
    let mediaUri: string | null = null;

    await db.withExclusiveTransactionAsync(async (txn) => {
        const row = await txn.getFirstAsync<{media_uri: string | null}>('SELECT media_uri FROM queue WHERE id = ?', id);
        await txn.runAsync('DELETE FROM queue WHERE id = ?', id);

        mediaUri = row?.media_uri ?? null;
    });

    return mediaUri;
}

export async function deleteCompleted(db: Database, keepIds: number[]): Promise<string[]> {
    const keep = keepIds.length > 0 ? `AND id NOT IN (${keepIds.map(() => '?').join(', ')})` : '';

    const uris: string[] = [];

    await db.withExclusiveTransactionAsync(async (txn) => {
        const rows = await txn.getAllAsync<{media_uri: string | null}>(
            `SELECT media_uri FROM queue WHERE ${COMPLETE} ${keep}`,
            ...keepIds,
        );

        await txn.runAsync(`DELETE FROM queue WHERE ${COMPLETE} ${keep}`, ...keepIds);

        for (const row of rows) {
            if (row.media_uri) {
                uris.push(row.media_uri);
            }
        }
    });

    return uris;
}

export async function referencedMediaUris(db: Database): Promise<string[]> {
    const rows = await db.getAllAsync<{media_uri: string}>('SELECT media_uri FROM queue WHERE media_uri IS NOT NULL');

    return rows.map((row) => row.media_uri);
}
