/**
 *
 * @param {string} text
 * @returns {object} GeoJSON
 */
export default function geoJSONParser({ text }) {
    if (!text) return;
    const geoJSON = JSON.parse(text);
    geoJSON.features = geoJSON.features.map(feature => {
        feature.properties.tags = feature.properties.tags ? feature.properties.tags.split(",") : [];
        return feature;
    })
    return { geoJSON };
}
