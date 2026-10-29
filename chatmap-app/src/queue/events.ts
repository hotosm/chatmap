const listeners = new Set<() => void>();

export function onQueueChanged(listener: () => void): () => void {
    listeners.add(listener);

    return () => {
        listeners.delete(listener);
    };
}

export function emitQueueChanged(): void {
    for (const listener of listeners) {
        listener();
    }
}
