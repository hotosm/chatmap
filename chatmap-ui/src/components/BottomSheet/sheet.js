/**
 * The pure part of a bottom sheet: how tall it is at each of its snap
 * points, and at which one it rests when a drag ends. Heights are the
 * pixels of the sheet in sight, measured from the bottom up.
 */

// The snap points a sheet can rest at, from the lowest
export const SNAPS = ["peek", "half", "full"];
// Not a snap point: where a sheet dragged down rests when it can be closed
export const CLOSED = "closed";

// How long a drag keeps going after it is let go, to project where it ends (ms)
export const MOMENTUM = 150;
// A drag faster than this (px/ms) always moves at least one snap point
export const FLING = 0.5;

/**
 * The height of each snap point in a space of `room` pixels: peek shows a
 * strip of `peek` pixels, half half of it, full all of it.
 *
 * @param {number} room The pixels from the top the sheet can reach to its bottom
 * @param {string[]} snaps The snap points the sheet uses, some of SNAPS
 * @param {number} peek The pixels of the sheet in sight when it peeks
 * @returns {object} {peek, half, full} for the snaps given
 */
export const snapHeights = (room, snaps = SNAPS, peek = 120) => {
    const all = { peek: Math.min(peek, room), half: Math.round(room / 2), full: room };
    return Object.fromEntries(snaps.filter((snap) => snap in all).map((snap) => [snap, all[snap]]));
};

// The snap points from the lowest, with closed first when it can close
const stopsOf = (heights, closable) => [
    ...(closable ? [[CLOSED, 0]] : []),
    ...Object.entries(heights).sort((a, b) => a[1] - b[1]),
];

/**
 * Where a sheet rests when a drag ends: the snap point nearest to where the
 * drag would end with its speed. A quick flick moves at least one snap point
 * in its direction, even when it was short.
 *
 * @param {object} heights The heights of its snap points (see snapHeights)
 * @param {string} from The snap point the drag started at
 * @param {number} shown The pixels in sight when it was let go
 * @param {number} velocity The speed of the drag in px/ms, positive downwards
 * @param {boolean} closable Whether dragging it down closes it
 * @returns {string} A snap point, or CLOSED
 */
export const settle = ({ heights, from, shown, velocity = 0, closable = true }) => {
    const stops = stopsOf(heights, closable);
    const projected = shown - velocity * MOMENTUM;
    let nearest = 0;
    stops.forEach(([, height], i) => {
        if (Math.abs(height - projected) < Math.abs(stops[nearest][1] - projected)) nearest = i;
    });
    if (Math.abs(velocity) >= FLING && stops[nearest][0] === from) {
        const step = velocity > 0 ? -1 : 1;
        nearest = Math.min(Math.max(nearest + step, 0), stops.length - 1);
    }
    return stops[nearest][0];
};

/**
 * The snap point one step up (+1) or down (-1) from another, for the keyboard
 * and the handle. Down from the lowest closes it when it can close.
 *
 * @returns {string} A snap point, or CLOSED
 */
export const stepFrom = (snaps, from, step, closable = true) => {
    const order = SNAPS.filter((snap) => snaps.includes(snap));
    const next = order.indexOf(from) + step;
    if (next < 0) return closable ? CLOSED : order[0];
    return order[Math.min(next, order.length - 1)];
};

// The pixels a sheet shows while dragged: never below nothing nor above its room
export const dragged = (start, delta, room) => Math.min(Math.max(start - delta, 0), room);

// Whether a sheet at a snap point is modal: from `modalAt` up it covers what is behind it
export const isModal = (snaps, snap, modalAt = "full") => {
    const order = SNAPS.filter((item) => snaps.includes(item));
    return snap !== CLOSED && order.indexOf(snap) >= order.indexOf(modalAt) && order.includes(modalAt);
};
