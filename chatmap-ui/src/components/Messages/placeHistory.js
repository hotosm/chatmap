/**
 * The history of a place: every change of its tags, of all its keys, from
 * messages or by hand, undone ones too, and which of them put what the
 * map shows today. Pure helpers for PlaceHistory.
 */
// From tags.js itself, not the index of the module, to stay a pure module that tests can read
import { expiresAt } from "../Tags/tags.js";
import { FROM_MESSAGES } from "./messages.js";

// What a change is for the place today
export const ON_MAP = "onMap";
// It put what the place has, but nobody confirmed it for longer than it lasts
export const EXPIRED = "expired";
// A newer change of its key rules
export const OLDER = "older";
export const UNDONE = "undone";
// It took a value out of the place
export const TAKEN_OUT = "takenOut";

// Whether a change and a tag are about the same value: an option of the list, or a text
const sameValue = (change, tag) =>
    change.value_id || tag.value_id ? change.value_id === tag.value_id : (change.value || "") === (tag.value || "");

// Newest first, as the API gives them: by when they happened, then by when they were written down
const newestFirst = (a, b) =>
    new Date(b.happened_at) - new Date(a.happened_at) || b.id - a.id;

// The option of a key a tag or a change has, or a written value as { value }
export const valueOf = (key, item) =>
    (key && item.value_id && (key.values || []).find((value) => value.id === item.value_id)) || { value: item.value };

/**
 * What the map shows today for a place, one row per key, in the order of
 * the keys: the values it has, since when, and when each stops being known
 * (null when it does not expire).
 *
 * @param {array} pointTags What the point has: [{ key_id, value_id, value, since, confirmed_at }]
 * @param {array} keys The keys of the map, with their values
 * @returns {array} [{ key, values: [{ tag, value, since, expiresAt, expired }] }]
 */
export const valuesInForce = (pointTags, keys, now = Date.now()) => (keys || [])
    .map((key) => ({
        key,
        values: (pointTags || [])
            .filter((tag) => tag.key_id === key.id)
            .map((tag) => {
                const value = valueOf(key, tag);
                const expires = expiresAt(value, tag.confirmed_at);
                return { tag, value, since: tag.since, expiresAt: expires, expired: expires !== null && expires.getTime() <= now };
            }),
    }))
    .filter(({ values }) => values.length > 0);

/**
 * Every change of a place, newest first, with what it is today: the one
 * that put each value the place has is on the map (or expired), the others
 * that set a value are older, and undone ones stay, marked.
 *
 * @param {array} changes The changes the history of the point gives
 * @param {array} pointTags What the point has now
 * @param {array} keys The keys of the map, with their values
 * @returns {array} [{ change, key, value, state, gone }], gone when its message is no longer kept
 */
export const placeHistory = (changes, pointTags, keys, now = Date.now()) => {
    const sorted = [...(changes || [])].sort(newestFirst);
    const keyOf = (keyId) => (keys || []).find((key) => key.id === keyId);

    // The newest change not undone that sets each value the place has put it there
    const ruling = new Map();
    for (const { values } of valuesInForce(pointTags, keys, now)) {
        for (const { tag, expired } of values) {
            const change = sorted.find((item) =>
                item.key_id === tag.key_id && item.action === "set" && !item.undone_at && sameValue(item, tag));
            if (change) ruling.set(change.id, expired ? EXPIRED : ON_MAP);
        }
    }

    return sorted.map((change) => {
        const key = keyOf(change.key_id);
        const state = change.undone_at ? UNDONE :
            ruling.get(change.id) || (change.action === "remove" ? TAKEN_OUT : OLDER);
        return {
            change,
            key,
            value: valueOf(key, change),
            state,
            gone: FROM_MESSAGES.includes(change.source) && !change.message_id,
        };
    });
};

/**
 * What the note under a change says, the first that applies: undone, its
 * message gone, made without a message, older or taken out, or where the
 * value on the map came from.
 */
export const noteOf = ({ change, state, gone }) => {
    if (state === UNDONE) return "undone";
    if (gone) return "gone";
    if (!FROM_MESSAGES.includes(change.source)) return change.source === "manual" ? "manual" : "other";
    if (state === OLDER) return "older";
    if (state === TAKEN_OUT) return "takenOut";
    return "linked";
};
