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

// The links of a message that are not undone: what it gave to points now
export const liveLinks = (message) => (message.links || []).filter((link) => !link.undone);

// The messages with one of them as it is now
export const withMessage = (messages, message) => messages.map((item) => item.id === message.id ? message : item);

// The changes a point got from messages, linked by a person
export const FROM_MESSAGES = ["message"];

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
