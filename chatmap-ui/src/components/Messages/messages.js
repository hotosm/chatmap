// How many messages a page of the API holds at most
export const PAGE_SIZE = 100;

/**
 * Whether the server keeps the messages of chat groups: ENABLE_GROUP_MESSAGES
 * of config.json, set from the same CHATMAP_ENABLE_GROUP_MESSAGES as the API.
 * The template writes it as text, so a server without it still gets valid JSON.
 */
export const groupMessagesOn = (config) => [true, "true"].includes(config?.ENABLE_GROUP_MESSAGES);

/**
 * Whether the messages of a map are shown: to its owner, when the map shows
 * its keys (withKeys, see usesKeys in Tags): there is nothing to link them to without them.
 */
export const messagesOn = (mapData, withKeys) => Boolean(withKeys && mapData && mapData.owner && mapData.id);

/**
 * The order of the messages is the one the API gives: newest first and, for
 * messages sent in the same second, by id as the database orders them. It is
 * never worked out here, so the next page always starts where the API says.
 */
const unseen = (messages, shown) => {
    const ids = new Set(shown.map((message) => message.id));
    return messages.filter((message) => !ids.has(message.id));
};

// The messages shown after reading the newest ones again: those first, as the API gives them
export const withNewer = (shown, page) => [...page, ...unseen(shown, page)];

// The messages shown after reading the next page: it goes below, without the ones already shown
export const withOlder = (shown, page) => [...shown, ...unseen(page, shown)];

/**
 * Whether the list starts over with the newest page read again: when that
 * page is full and all of it is newer than what is shown, there may be
 * messages in between that were never read, and none should be skipped.
 */
export const startsOver = (shown, page) => {
    const newestShown = shown[0];
    const oldestRead = page[page.length - 1];
    // All of it newer: the newest shown is not in it, and its oldest was sent after that one
    return Boolean(
        page.length >= PAGE_SIZE && newestShown && oldestRead &&
        !page.some((message) => message.id === newestShown.id) &&
        Date.parse(oldestRead.sent_at) >= Date.parse(newestShown.sent_at)
    );
};

// Where the next page starts: after the last message shown, by its time and id
export const nextPage = (shown) => {
    const last = shown[shown.length - 1];
    return last ? { before: last.sent_at, before_id: last.id } : {};
};

// The address of a page of the app, keeping the parameters of the current one (like ?dashboard)
export const pageOf = (path, hash = window.location.hash) => {
    const query = hash.split("?")[1];
    return `#${path}${query ? `?${query}` : ""}`;
};

// The coordinates a location says, rounded to about a meter: [lat, lon], or null when it says none
export const coordsOf = (location) => {
    const match = /^\s*([-+]?\d+(?:\.\d+)?)\s*,\s*([-+]?\d+(?:\.\d+)?)/.exec(location || "");
    if (!match) return null;
    const [lat, lon] = [Number(match[1]), Number(match[2])];
    if (Math.abs(lat) > 90 || Math.abs(lon) > 180) return null;
    return [lat, lon].map((value) => Math.round(value * 1e5) / 1e5);
};

// The name of each group by its id, to show it on its messages
export const groupNames = (groups) => Object.fromEntries((groups || []).map((group) => [group.id, group.name]));

// Meters between two [lat, lon], near enough for places of a map
export const metersBetween = ([lat1, lon1], [lat2, lon2]) => {
    const rad = Math.PI / 180;
    const x = (lon2 - lon1) * rad * Math.cos(((lat1 + lat2) / 2) * rad);
    const y = (lat2 - lat1) * rad;
    return Math.round(Math.sqrt(x * x + y * y) * 6371000);
};

/**
 * The places of a map a message can be linked to: the points its owner made
 * on the dashboard (not the reports from locations shared in chats), not
 * removed, with their name. Nearest first when the message says where it was sent
 * from (coords), by name when it does not.
 *
 * @returns {array} [{ id, name, meters }]; meters is null without coords
 */
export const placesOf = (features, coords) => {
    const places = (features || [])
        .filter((feature) => feature.properties && feature.properties.place && !feature.properties.removed && feature.geometry)
        .map((feature) => {
            const [lon, lat] = feature.geometry.coordinates;
            return {
                id: feature.properties.id,
                name: feature.properties.message || "",
                meters: coords ? metersBetween(coords, [lat, lon]) : null,
            };
        });
    return places.sort((a, b) => coords ? a.meters - b.meters : a.name.localeCompare(b.name));
};

// The places whose name has the text, without minding case nor accents
export const placesNamed = (places, text) => {
    const plain = (value) => value.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
    const asked = plain(text.trim());
    return asked ? places.filter((place) => plain(place.name).includes(asked)) : places;
};

// How many places a chat group can be about, as the API takes them
export const MAX_GROUP_PLACES = 2;

// The places a chat group is always about, of the ones of the map, in the order of its point ids
export const groupPlaces = (group, places) =>
    (group.point_ids || []).map((id) => places.find((place) => place.id === id)).filter(Boolean);

// The places that can still be added to a group, found by name: none once it has as many as it can
export const placesToAdd = (places, chosen, text, shown = 5) => {
    if (chosen.length >= MAX_GROUP_PLACES) return [];
    const taken = new Set(chosen);
    return placesNamed(places, text).filter((place) => !taken.has(place.id)).slice(0, shown);
};

// The ids of the places the group of each message always speaks of, by the id of the group
export const groupPointsOf = (groups) =>
    Object.fromEntries((groups || []).map((group) => [group.id, group.point_ids || []]));

// The links of a message that are not undone: what it gave to points now
export const liveLinks = (message) => (message.links || []).filter((link) => !link.undone);

// The messages with one of them as it is now
export const withMessage = (messages, message) => messages.map((item) => item.id === message.id ? message : item);

// The changes a point got from messages, linked by a person or as a rule suggested
export const FROM_MESSAGES = ["message", "rule"];

// The changes a point got from messages that are not undone, newest first, as its history gives them
export const linksOfPoint = (history) =>
    ((history && history.changes) || []).filter((change) => FROM_MESSAGES.includes(change.source) && !change.undone_at);

/**
 * What the panel of the messages of a point covers over the map, { right }
 * or { bottom } on a phone, as messages.css draws it; null when it is not shown.
 */
export const pointPanelCover = (shown, width = window.innerWidth, height = window.innerHeight) => {
    if (!shown) return null;
    return width <= 720 ? { bottom: Math.round(height * 0.45) + 16 } : { right: Math.min(384, width - 32) + 16 };
};

// What is written in more than one way, folded to one way, as the rules of the API compare texts
const FOLDED = {
    "ٱ": "ا", "ى": "ي", "ة": "ه", "ی": "ي", "ک": "ك",
    "׳": "'", "״": '"', "ך": "כ", "ם": "מ", "ן": "נ", "ף": "פ", "ץ": "צ",
    "ـ": "", "‌": "", "‍": "", "‎": "", "‏": "",
};
const DIGITS = /[٠-٩۰-۹]/;
const LETTER = /\p{L}/u;

/**
 * A text as the rules compare it (see plain in the API), with where each of
 * its characters comes from in the text: without case nor accents nor the
 * marks of Arabic and Hebrew, folded, and a letter repeated in a row once.
 *
 * @returns {object} { plain, from }: from[i] is the index in text of plain[i]
 */
export const plainWithIndex = (text) => {
    let plain = "";
    const from = [];
    [...text].reduce((index, char) => {
        const decomposed = char.toLowerCase().normalize("NFKD").replace(/\p{M}/gu, "");
        for (const piece of decomposed) {
            const code = piece.charCodeAt(0);
            const folded = piece in FOLDED ? FOLDED[piece] :
                DIGITS.test(piece) ? String((code >= 0x06F0 ? code - 0x06F0 : code - 0x0660)) : piece;
            if (!folded) continue;
            // A letter repeated in a row counts once, as "cerrrrado" and "cerrado" are the same word
            if (LETTER.test(folded) && plain.endsWith(folded)) {
                continue;
            }
            plain += folded;
            // One for each unit of it: an emoji like 🔴 is two, and plain is read by units
            for (let unit = 0; unit < folded.length; unit++) from.push(index);
        }
        return index + char.length;
    }, 0);
    return { plain, from };
};

/**
 * A text cut in pieces, marking the ones where it says one of the values a
 * rule looked for, found as the rules compare texts.
 *
 * @returns {array} [{ text, match }]
 */
export const highlighted = (text, values = []) => {
    if (!text || values.length === 0) return [{ text: text || "", match: false }];
    const { plain, from } = plainWithIndex(text);
    const marked = new Array(text.length).fill(false);
    for (const value of values) {
        const looked = plainWithIndex(value).plain;
        if (!looked) continue;
        for (let at = plain.indexOf(looked); at !== -1; at = plain.indexOf(looked, at + 1)) {
            const start = from[at];
            const end = at + looked.length < from.length ? from[at + looked.length] : text.length;
            marked.fill(true, start, end);
        }
    }
    const pieces = [];
    [...text].reduce((index, char) => {
        const match = marked[index];
        const last = pieces[pieces.length - 1];
        if (last && last.match === match) last.text += char;
        else pieces.push({ text: char, match });
        return index + char.length;
    }, 0);
    return pieces;
};

/**
 * Who sent a message, told apart without saying who: the start of its
 * pseudonym, as "Person 3fa1", and a color of its own, the same in every message.
 *
 * @returns {object} { code, hue }
 */
export const senderOf = (sender) => {
    const pseudonym = sender || "";
    const hash = [...pseudonym].reduce((sum, char) => (sum * 31 + char.charCodeAt(0)) % 100003, 7);
    // Steps of the golden angle around the circle of colors, so close pseudonyms get far colors
    return { code: pseudonym.slice(0, 4), hue: Math.round((hash * 137.508) % 360) };
};

// The day a message was sent, where the page is read: "2026-10-27"
export const dayOf = (sentAt) => {
    const date = new Date(sentAt);
    const two = (number) => String(number).padStart(2, "0");
    return `${date.getFullYear()}-${two(date.getMonth() + 1)}-${two(date.getDate())}`;
};

// The place of the map nearest to where a message was sent from, up to a distance; null without one
export const nearestPlace = (features, coords, within = 2000) => {
    if (!coords) return null;
    const [nearest] = placesOf(features, coords);
    return nearest && nearest.meters <= within ? nearest : null;
};

// The suggestions of a message with the answer of the API to one of them, or to a link
export const withSuggestions = (message, suggestions) => suggestions ? { ...message, suggestions } : message;

/**
 * The rows of a message in its card: first what rules suggest for the whole
 * message (line null), then each line with text, with what it suggests, in
 * the order of the message. A line keeps its number as the API counts them.
 */
export const messageRows = (text, suggestions = []) => {
    const whole = suggestions.filter((item) => item.line === null || item.line === undefined);
    const lines = (text || "").split("\n")
        .map((line, index) => ({ line: index, text: line.trim(), suggestions: suggestions.filter((item) => item.line === index) }))
        .filter((row) => row.text);
    return [...(whole.length ? [{ line: null, text: null, suggestions: whole }] : []), ...lines];
};

// What a person renews with one click: pending, plain, with a place and a value, which the place already shows
export const renewable = (suggestions = []) => suggestions.filter((item) =>
    item.state === "pending" && item.unchanged && !item.doubt && item.point_id && item.value_id
);

// The live link of a message that gives what a suggestion said: the one its confirmation made
export const linkOf = (message, suggestion) => liveLinks(message).find((link) =>
    link.point_id === suggestion.point_id && (!suggestion.key_id ||
        (link.key_id === suggestion.key_id && link.value_id === suggestion.value_id))
) || null;
