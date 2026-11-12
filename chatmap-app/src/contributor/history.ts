import {apiFetch, withTimeout} from '../api/client';
import {getSecret} from './secret';

const HISTORY_TIMEOUT_MS = 15000;

export type HistoryMedia = {
    id: string;
    contentType: string;
    size: number;
    capturedAt: string | null;
};

export type HistoryPoint = {
    id: string;
    time: string;
    latitude: number;
    longitude: number;
    message: string | null;
    media: HistoryMedia | null;
};

export type HistoryPage = {
    points: HistoryPoint[];
    next: string | null;
};

export type HistoryResult =
    | {status: 'ok'; page: HistoryPage}
    | {status: 'forbidden'};

type HistoryResponse = {
    points: {
        id: string;
        time: string;
        latitude: number;
        longitude: number;
        message: string | null;
        media: {id: string; content_type: string; size: number; captured_at: string | null} | null;
    }[];
    next: string | null;
};

export async function fetchHistory(mapId: string, cursor: string | null): Promise<HistoryResult> {
    const query = cursor ? `?cursor=${encodeURIComponent(cursor)}` : '';
    const authorization = `Contributor ${await getSecret()}`;

    const response = await withTimeout(HISTORY_TIMEOUT_MS, (signal) =>
        apiFetch(`/v2/maps/${encodeURIComponent(mapId)}/points${query}`, {
            headers: {Authorization: authorization},
            signal,
        }),
    );

    if (response.status === 403) {
        return {status: 'forbidden'};
    }

    if (!response.ok) {
        throw new Error(`Unexpected response listing points (${response.status})`);
    }

    const body: HistoryResponse = await response.json();

    return {
        status: 'ok',
        page: {
            points: body.points.map((point) => ({
                id: point.id,
                time: point.time,
                latitude: point.latitude,
                longitude: point.longitude,
                message: point.message,
                media: point.media
                    ? {
                        id: point.media.id,
                        contentType: point.media.content_type,
                        size: point.media.size,
                        capturedAt: point.media.captured_at,
                    }
                    : null,
            })),
            next: body.next,
        },
    };
}
