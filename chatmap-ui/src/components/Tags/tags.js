// What a point shows for a key when nobody confirmed its value for too long
export const UNKNOWN = "unknown";

/**
 * Whether the keys of the maps are shown: today, with "?dashboard" in the
 * address (#/map/<id>?dashboard). The only place that knows how they turn
 * on; free tags are there either way.
 */
export const keysOn = (hash = window.location.hash) =>
    new URLSearchParams(hash.split("?")[1] || "").has("dashboard");

// Whether a map was read with its keys: everything of this module shows only then
export const usesKeys = (mapData) => Array.isArray(mapData && mapData.keys);

const DARK_TEXT = "#1F2329";

/**
 * Adds the keys of a map and the tags of its points (as read from the API
 * v2) to its data. Each point gets `point_tags`, the values it has.
 *
 * @param {object} mapData Map data (GeoJSON FeatureCollection)
 * @param {array} keys Keys of the map, with their values
 * @param {array} tags What the points have: [{ point_id, key_id, value_id, value, since, confirmed_at }]
 * @returns {object} The map data with its keys
 */
export const withTags = (mapData, keys, tags) => {
    const byPoint = {};
    for (const tag of tags || []) {
        (byPoint[tag.point_id] = byPoint[tag.point_id] || []).push(tag);
    }
    return {
        ...mapData,
        keys: keys || [],
        features: (mapData.features || []).map((feature) => ({
            ...feature,
            properties: { ...feature.properties, point_tags: byPoint[feature.properties.id] || [] },
        })),
    };
};

// The keys a point can be given now: the ones not archived
export const activeKeys = (keys) => (keys || []).filter((key) => !key.archived);

// The values of a key that can be picked: the ones not archived
export const selectable = (key) => ((key && key.values) || []).filter((value) => !value.archived);

// Keys that can color the map: one value per point, picked from a list
export const colorKeys = (keys) => activeKeys(keys).filter((key) => key.single && key.closed);

/**
 * The key the map is colored by: the one whoever looks at it chose (colorKey,
 * null for none) or, until they choose, the one its owner chose.
 */
export const colorKeyOf = (keys, colorKey) => {
    const options = colorKeys(keys);
    if (colorKey !== undefined) return options.find((key) => key.id === colorKey) || null;
    return options.find((key) => key.colors_map) || null;
};

// What a point has for a key
export const tagsOf = (properties, keyId) => (properties.point_tags || []).filter((tag) => tag.key_id === keyId);

// The properties of a point with what it has now for a key, as the API answers it
export const withKeyTags = (properties, keyId, tags) => ({
    ...properties,
    point_tags: [...(properties.point_tags || []).filter((tag) => tag.key_id !== keyId), ...tags],
});

// The map moves to another point with the arrows; inside this module they move the cursor or the options
export const keepArrows = (event) => {
    if (event.key === "ArrowLeft" || event.key === "ArrowRight") event.stopPropagation();
};

/**
 * When the value of a key stops being known: the last confirmation plus the
 * hours the value lasts. Null when it does not expire.
 */
export const expiresAt = (value, confirmedAt) => {
    if (!value || !value.expires_after || !confirmedAt) return null;
    const confirmed = new Date(confirmedAt).getTime();
    if (isNaN(confirmed)) return null;
    return new Date(confirmed + value.expires_after * 60 * 60 * 1000);
};

// Whether nobody confirmed this value of a point for longer than it lasts
export const isExpired = (value, tag, now = Date.now()) => {
    const expires = expiresAt(value, tag.confirmed_at);
    return expires !== null && expires.getTime() <= now;
};

/**
 * What a point shows now for a key with one value: the id of its value,
 * UNKNOWN when it expired, or null when it has none. Nothing is saved when
 * a value expires.
 */
export const shownValue = (properties, key, now = Date.now()) => {
    const [tag] = key ? tagsOf(properties, key.id) : [];
    const value = tag && (key.values || []).find((item) => item.id === tag.value_id);
    if (!value) return null;
    return isExpired(value, tag, now) ? UNKNOWN : value.id;
};

// The map data with what each point shows now for a key, as `color_value`
export const withShownValues = (mapData, key, now = Date.now()) => ({
    ...mapData,
    features: (mapData.features || []).map((feature) => ({
        ...feature,
        properties: { ...feature.properties, color_value: shownValue(feature.properties, key, now) },
    })),
});

/**
 * The color of a text written over a value color: dark over light colors,
 * white over dark ones, the one that stands out more (WCAG).
 */
const luminance = (color) => {
    const hex = /^#?([0-9a-f]{6})$/i.exec(color || "");
    if (!hex) return null;
    const [r, g, b] = [0, 2, 4].map((i) => {
        const channel = parseInt(hex[1].slice(i, i + 2), 16) / 255;
        return channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
    });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};

const contrast = (a, b) => (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);

export const textOn = (color) => {
    const background = luminance(color);
    if (background === null) return "#FFFFFF";
    return contrast(background, 1) >= contrast(background, luminance(DARK_TEXT)) ? "#FFFFFF" : DARK_TEXT;
};

// The free tags of a point, from the text with commas the API answers
export const freeTags = (tags) => (tags || "").split(",").filter((tag) => tag);

// The free tags the points of a map use, the most used first: [{ tag, count }]
export const freeTagsInUse = (features) => {
    const counts = {};
    for (const feature of features || []) {
        if (feature.properties.removed) continue;
        for (const tag of freeTags(feature.properties.tags)) {
            counts[tag] = (counts[tag] || 0) + 1;
        }
    }
    return Object.entries(counts)
        .map(([tag, count]) => ({ tag, count }))
        .sort((a, b) => b.count - a.count || a.tag.localeCompare(b.tag));
};

// The ids of the values some point of the map has
export const valuesInUse = (features) => new Set(
    (features || []).flatMap((feature) => (feature.properties.point_tags || []).map((tag) => tag.value_id))
        .filter((id) => id)
);

// The filter of the map by tag also takes a value of a key: "key:<key id>:<value id or unknown>"
const KEY_FILTER = "key:";

export const keyFilter = (keyId, valueId) => `${KEY_FILTER}${keyId}:${valueId}`;

// The key and value a filter of the map asks for, or null when it asks for a free tag
export const keyFilterOf = (filter) => {
    if (typeof filter !== "string" || !filter.startsWith(KEY_FILTER)) return null;
    const [keyId, valueId] = filter.slice(KEY_FILTER.length).split(":");
    return { keyId, valueId };
};

/**
 * How many points show each value of a key with one value now, to filter by
 * them: its values not archived, and unknown when some point expired.
 *
 * @returns {array} [{ id, value, color, count }]
 */
export const shownValueCounts = (features, key, now = Date.now()) => {
    const counts = {};
    for (const feature of features || []) {
        if (feature.properties.removed) continue;
        const shown = shownValue(feature.properties, key, now);
        if (shown) counts[shown] = (counts[shown] || 0) + 1;
    }
    const values = (key.values || [])
        .filter((value) => !value.archived || counts[value.id])
        .map((value) => ({ id: value.id, value: value.value, color: value.color, count: counts[value.id] || 0 }));
    return counts[UNKNOWN] ? [...values, { id: UNKNOWN, value: null, color: null, count: counts[UNKNOWN] }] : values;
};

/**
 * A point added by hand, as the API takes it and as the map shows it.
 *
 * @param {object} point Its id, name, coordinates ([longitude, latitude]) and time
 * @returns {object} { request, feature }
 */
export const newPoint = ({ id, name, coordinates, time }) => ({
    request: {
        id,
        longitude: coordinates[0],
        latitude: coordinates[1],
        time,
        message: name,
    },
    feature: {
        type: "Feature",
        properties: {
            id,
            message: name,
            time,
            file: null,
            tags: "",
            removed: false,
            survey: [],
            point_tags: [],
        },
        geometry: { type: "Point", coordinates },
    },
});
