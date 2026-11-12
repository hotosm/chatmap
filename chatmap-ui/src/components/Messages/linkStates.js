import { timeAgo } from "../TimeAgo";
import { colorKeyOf, colorKeys, expiresAt, isExpired, newPoint, shownValue, tagsOf } from "../Tags/tags.js";

// What a link did, when it did not change what the place shows or was not made
export const OLDER = "older";
export const EXPIRED = "expired";
export const TWICE = "twice";
export const FAILED = "failed";

// The hours a value lasts, to say them: "24 hours" up to two days, then "3 days"
export const hoursAs = (hours) =>
    hours >= 48 && hours % 24 === 0 ? { value: hours / 24, unit: "day" } : { value: hours, unit: "hour" };

// How old something is, { value, unit } as timeAgo counts it but forward: "2 days"
export const ageOf = (datetime, now = Date.now()) => {
    const ago = timeAgo(datetime, now);
    return ago && { value: Math.abs(ago.value), unit: ago.unit };
};

// The value of a key a tag has: an option of its list, or the text it was given
const valueOf = (key, tag) => tag.value_id ?
    (key.values || []).find((item) => item.id === tag.value_id) || null :
    { value: tag.value };

/**
 * What a link the API took did, to say it in the card. Null when the place
 * shows now the value of the message, as most links do. Otherwise:
 * - older: it went to the history of the place, which has something newer
 *   (shown, given shownAt); shown is null when that is not known or expired too
 * - expired: the message is older than its value lasts, so the place shows it as unknown
 *
 * @param {object} answer What the API answered: { link, tags, applied } (see useMessageActions)
 * @param {object} key The key linked, with its values
 * @param {object|null} value The value given, when it is an option of the key
 * @param {string} sentAt When the message was sent
 */
export const linkOutcome = ({ answer, key, value, sentAt, now = Date.now() }) => {
    if (!answer.applied) {
        // What the point has for the key now: the one confirmed last
        const [tag] = (answer.tags || [])
            .filter((item) => item.key_id === key.id)
            .sort((a, b) => Date.parse(b.confirmed_at) - Date.parse(a.confirmed_at));
        const shown = tag ? valueOf(key, tag) : null;
        const known = shown && !isExpired(shown, tag, now);
        return { kind: OLDER, link: answer.link, shown: known ? shown : null, shownAt: known ? tag.confirmed_at : null };
    }
    if (value && isExpired(value, { confirmed_at: sentAt }, now)) {
        return { kind: EXPIRED, link: answer.link, value, lasts: hoursAs(value.expires_after), age: ageOf(sentAt, now) };
    }
    return null;
};

// A message that says nothing in words: only where it was sent from
export const onlyLocation = (message) => Boolean(message.location) && !(message.text || "").trim();

/**
 * The key whose value a place shows in the list to choose it: the one the
 * map is colored by, or else the first that could color it; null without one.
 */
export const statusKeyOf = (keys) => colorKeyOf(keys) || colorKeys(keys)[0] || null;

/**
 * What a point shows now for a key, to show it next to its name: its value,
 * or null when it has none. When the value expired, { unknown: true } with
 * the value it had (`last`) and when it expired (`expiredAt`), so the list
 * can say what it was rather than only that it is not known.
 */
export const statusOf = (feature, key, now = Date.now()) => {
    if (!feature || !key) return null;
    const shown = shownValue(feature.properties, key, now);
    if (!shown) return null;
    const value = (key.values || []).find((item) => item.id === shown);
    if (value) return value;
    const [tag] = tagsOf(feature.properties, key.id);
    const last = tag && (key.values || []).find((item) => item.id === tag.value_id);
    return { unknown: true, last: last || null, expiredAt: last ? expiresAt(last, tag.confirmed_at) : null };
};

// The name a new place takes from what was looked for: trimmed, or null when there is none
export const newPlaceName = (text) => (text || "").trim() || null;

/**
 * A new place where a message was sent from, as the API takes it and as the
 * map shows it (see newPoint).
 *
 * @param {array} coords [lat, lon] of the message (see coordsOf)
 */
export const placeAt = (name, coords, time = new Date().toISOString()) =>
    newPoint({ name, coordinates: [coords[1], coords[0]], time });

/**
 * The [[west, south], [east, north]] that hold some [lat, lon], to fit a map
 * to them; null when there are none.
 */
export const boundsOf = (points) => {
    const shown = (points || []).filter(Boolean);
    if (shown.length === 0) return null;
    const lats = shown.map(([lat]) => lat);
    const lons = shown.map(([, lon]) => lon);
    return [[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]];
};

// Where the places of a map are, as [lat, lon], leaving out the removed ones
export const placesCoords = (features) => (features || [])
    .filter((feature) => feature.geometry && !(feature.properties && feature.properties.removed))
    .map((feature) => [feature.geometry.coordinates[1], feature.geometry.coordinates[0]]);
