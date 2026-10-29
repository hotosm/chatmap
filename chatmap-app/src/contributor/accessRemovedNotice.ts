import type {MapRemoval} from '../storage/maps';

function describe({map, discarded}: MapRemoval): string {
    const base = `You no longer have access to "${map.mapName ?? 'Untitled map'}".`;

    if (discarded === 0) {
        return base;
    }

    return `${base} ${discarded} pending ${discarded === 1 ? 'point was' : 'points were'} not sent.`;
}

export function accessRemovedTitle(removed: MapRemoval[]): string {
    return removed.length === 1 ? 'Map unavailable' : 'Maps unavailable';
}

export function accessRemovedMessage(removed: MapRemoval[]): string {
    return removed.map(describe).join('\n\n');
}
