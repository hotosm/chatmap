import * as Crypto from 'expo-crypto';
import {Directory, File, Paths} from 'expo-file-system';

export type MediaKind = 'photo' | 'video' | 'audio';

const directory = new Directory(Paths.document, 'queued-media');

const VIDEO_EXTENSIONS = new Set(['mp4', 'mov']);
const AUDIO_EXTENSIONS = new Set(['m4a', 'mp3', 'ogg', 'opus', 'wav']);

let chain: Promise<unknown> = Promise.resolve();

export function exclusiveMedia<T>(task: () => Promise<T>): Promise<T> {
    const result = chain.then(task, task);
    chain = result.catch(() => undefined);

    return result;
}

function extensionOf(uri: string): string {
    const match = /\.([A-Za-z0-9]{1,5})(?:\?.*)?$/.exec(uri);

    return match ? match[1].toLowerCase() : 'jpg';
}

export function kindOfUri(uri: string): MediaKind {
    const extension = extensionOf(uri);

    if (VIDEO_EXTENSIONS.has(extension)) {
        return 'video';
    }

    return AUDIO_EXTENSIONS.has(extension) ? 'audio' : 'photo';
}

export function kindOfContentType(contentType: string): MediaKind {
    if (contentType.startsWith('video/')) {
        return 'video';
    }

    return contentType.startsWith('audio/') ? 'audio' : 'photo';
}

export async function persistMedia(temporaryUri: string): Promise<string> {
    directory.create({idempotent: true, intermediates: true});

    const target = new File(directory, `${Crypto.randomUUID()}.${extensionOf(temporaryUri)}`);
    await new File(temporaryUri).copy(target);

    return target.uri;
}

export function deleteMedia(uri: string): void {
    try {
        const file = new File(uri);

        if (file.exists) {
            file.delete();
        }
    } catch (error) {
        console.warn('Deleting a media file failed', error);
    }
}

export function sweepMedia(referenced: Set<string>): void {
    if (!directory.exists) {
        return;
    }

    for (const entry of directory.list()) {
        if (entry instanceof File && !referenced.has(entry.uri)) {
            deleteMedia(entry.uri);
        }
    }
}
