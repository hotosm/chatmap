import { useCallback, useMemo } from "react";

import { paintTags } from "./mapLayer.js";
import { colorKeyOf, keyFilterOf, shownValue, usesKeys, withKeyTags, withShownValues } from "./tags.js";
import useNow from "./useNow.js";
import useTagsApi from "./useTagsApi.js";

// A map read without its keys: shown and filtered as always
const WITHOUT_KEYS = {
    colorKey: null,
    shown: (mapData) => mapData,
    filter: () => null,
    paint: () => {},
};

/**
 * How a map shows the values of its points at a time: what each point shows
 * for the key that colors it, the filter by one of its values and its paint.
 *
 * @param {object} data Map data, with its keys when they are shown
 * @param {number} now The time to tell expired values by
 * @returns {object} { colorKey, shown(mapData), filter(filterTag), paint(map, layer, pointColor) }
 */
export const mapTags = (data, now) => {
    if (!usesKeys(data)) return WITHOUT_KEYS;
    const colorKey = colorKeyOf(data.keys, data.colorKey);
    return {
        colorKey,
        shown: (mapData) => withShownValues(mapData, colorKey, now),
        // Whether a point shows the value the filter asks for; null when it asks for a free tag
        filter: (filterTag) => {
            const asked = keyFilterOf(filterTag);
            if (!asked) return null;
            const key = data.keys.find((item) => item.id === asked.keyId);
            return (feature) => shownValue(feature.properties, key, now) === asked.valueId;
        },
        paint: (map, layer, pointColor) => paintTags(map, layer, colorKey, pointColor),
    };
};

/**
 * The tags of a map, for the map that shows it: mapTags, updated every minute
 * while it has keys, and what the popup of a point needs to show and give
 * them (null without keys). The popup is drawn on its own React root, so
 * values are saved from here.
 */
export default function useMapTags(data) {
    const on = usesKeys(data);
    const now = useNow(on);
    const { setPointTag } = useTagsApi();

    // The properties of the point with the value saved, or null when the API does not take it
    const setTag = useCallback(async (properties, keyId, change) => {
        const saved = await setPointTag(properties.id, keyId, change);
        return saved ? withKeyTags(properties, keyId, saved.tags) : null;
    }, [setPointTag]);

    return useMemo(() => {
        const tags = mapTags(data, now);
        return { ...tags, point: on ? { keys: data.keys, colorKey: tags.colorKey && tags.colorKey.id, setTag } : null };
    }, [data, now, on, setTag]);
}
