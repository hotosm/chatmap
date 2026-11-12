// Media uploaded from the app lives in the API v2
const apiV2 = (apiUrl) => apiUrl.replace(/\/v\d+\/?$/, "/v2");

// image, video or audio: the content types the API v2 serves media with
export const mediaType = (contentType) => contentType.split("/")[0];

/**
 * Adds the media of the points of a map (as read from the API v2) to its
 * data. Each point with media gets `media`: { url, content_type }. The URL
 * is built with the server this web talks to, not with the `url` the API
 * answers, which depends on the public address the server has configured.
 *
 * @param {object} mapData Map data (GeoJSON FeatureCollection)
 * @param {array} media Media of the map: [{ point_id, id, content_type, ... }]
 * @param {string} apiUrl The API this web talks to
 * @returns {object} The map data with the media of its points
 */
export const withMedia = (mapData, media, apiUrl) => {
    const byPoint = {};
    for (const item of media || []) byPoint[item.point_id] = item;
    return {
        ...mapData,
        features: (mapData.features || []).map((feature) => {
            const item = byPoint[feature.properties.id];
            if (!item) return feature;
            const pointMedia = { url: `${apiV2(apiUrl)}/media/${item.id}`, content_type: item.content_type };
            return { ...feature, properties: { ...feature.properties, media: pointMedia } };
        }),
    };
};

/**
 * A map as the API v1 answers it, with the media of its points in the API
 * v2. When that media cannot be read, the map as it came.
 */
export const withMapMedia = async (apiUrl, mapData) => {
    try {
        const response = await fetch(`${apiV2(apiUrl)}/maps/${mapData.id}/media`, { credentials: 'include' });
        if (!response.ok) return mapData;
        const { media } = await response.json();
        return withMedia(mapData, media, apiUrl);
    } catch {
        return mapData;
    }
};
