import { useCallback } from "react";
import { useConfigContext } from "../../context/ConfigContext.jsx";
import { keysOn, withTags } from "./tags.js";

// Tags live in the API v2
const apiV2 = (apiUrl) => apiUrl.replace(/\/v\d+\/?$/, "/v2");

// The answer of the API, or null when the request fails
const request = async (url, options = {}) => {
    try {
        const response = await fetch(url, { credentials: 'include', ...options });
        if (response.status === 204) return {};
        return response.ok ? await response.json() : null;
    } catch {
        return null;
    }
};

const send = (method, url, body) => request(url, {
    method,
    body: body === undefined ? undefined : JSON.stringify(body),
    headers: {"Content-Type": "application/json"},
});

/**
 * A map as the API v1 answers it, with its keys and what its points have
 * when keys are shown. When they are not, or cannot be read, without keys:
 * `keys` goes empty on purpose, so the ones of a map read before do not stay.
 */
export const withMapTags = async (apiUrl, mapData) => {
    const withoutKeys = { ...mapData, keys: undefined };
    if (!keysOn()) return withoutKeys;
    const api = apiV2(apiUrl);
    const [keys, tags] = await Promise.all([
        request(`${api}/maps/${mapData.id}/keys`), request(`${api}/maps/${mapData.id}/tags`),
    ]);
    return keys && tags ? withTags(mapData, keys.keys, tags.tags) : withoutKeys;
};

export default function useTagsApi() {
    const { config } = useConfigContext();
    const api = apiV2(config.API_URL);

    // A new key of a map: { key, single, closed, colors_map, values }
    const createKey = useCallback((mapId, key) => send('POST', `${api}/maps/${mapId}/keys`, key), [api]);

    // What changes in a key: { key, archived, colors_map, values }; values is the whole list
    const updateKey = useCallback(
        (mapId, keyId, changes) => send('PUT', `${api}/maps/${mapId}/keys/${keyId}`, changes), [api]
    );

    // Only a key that was never given to a point can be removed
    const removeKey = useCallback(
        (mapId, keyId) => send('DELETE', `${api}/maps/${mapId}/keys/${keyId}`), [api]
    );

    // Give, confirm (the same again) or take out a value of a key: { action, value_id | value }
    const setPointTag = useCallback(
        (pointId, keyId, change) => send('PUT', `${api}/points/${pointId}/tags/${keyId}`, change), [api]
    );

    // Add a point to a map by hand: its id, where it is and its name
    const createPoint = useCallback(
        (mapId, point) => send('POST', `${api}/points`, { ...point, map_id: mapId }), [api]
    );

    return { createKey, updateKey, removeKey, setPointTag, createPoint };
}
