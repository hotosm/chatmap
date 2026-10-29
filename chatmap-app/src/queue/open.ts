const openPoints = new Map<string, number>();

export function openPoint(mapId: string, itemId: number): void {
    openPoints.set(mapId, itemId);
}

export function closeItem(itemId: number): void {
    for (const [mapId, id] of openPoints) {
        if (id === itemId) {
            openPoints.delete(mapId);
        }
    }
}

export function closeMap(mapId: string): void {
    openPoints.delete(mapId);
}

export function openItemIds(): number[] {
    return [...openPoints.values()];
}
