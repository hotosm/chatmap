import {File} from 'expo-file-system';

import {apiFetch, apiUpload, withTimeout} from '../api/client';
import type {QueueItem} from '../queue/store';
import type {UploadableItem} from '../sync/engine';
import type {MediaOutcome, PointOutcome} from '../sync/outcomes';
import {getSecret} from './secret';

const POINT_TIMEOUT_MS = 20000;
const MEDIA_TIMEOUT_MS = 120000;

export async function createPoint(item: QueueItem): Promise<PointOutcome> {
    const authorization = `Contributor ${await getSecret()}`;

    const response = await withTimeout(POINT_TIMEOUT_MS, (signal) =>
        apiFetch('/v2/points', {
            method: 'POST',
            headers: {'Content-Type': 'application/json', Authorization: authorization},
            body: JSON.stringify({
                map_id: item.mapId,
                latitude: item.latitude,
                longitude: item.longitude,
                time: item.capturedAt,
                message: item.message,
            }),
            signal,
        }),
    );

    if (response.status === 201 || response.status === 200) {
        const body: {id: string} = await response.json();

        return {status: 'created', pointId: body.id};
    }

    if (response.status === 403 || response.status === 404 || response.status === 422) {
        return {status: 'rejected', reason: String(response.status)};
    }

    return {status: 'retry'};
}

export async function uploadMedia(item: UploadableItem): Promise<MediaOutcome> {
    const file = new File(item.mediaUri);

    if (!file.exists) {
        return {status: 'rejected', reason: 'missing-file'};
    }

    const authorization = `Contributor ${await getSecret()}`;
    const form = new FormData();
    form.append('file', file);
    form.append('captured_at', item.mediaCapturedAt);

    const response = await withTimeout(MEDIA_TIMEOUT_MS, (signal) =>
        apiUpload(`/v2/points/${encodeURIComponent(item.pointId)}/media`, {
            method: 'POST',
            headers: {Authorization: authorization},
            body: form,
            signal,
        }),
    );

    if (response.status === 201 || response.status === 409) {
        return {status: 'uploaded'};
    }

    if (response.status === 403 || response.status === 415 || response.status === 422) {
        return {status: 'rejected', reason: String(response.status)};
    }

    return {status: 'retry'};
}
