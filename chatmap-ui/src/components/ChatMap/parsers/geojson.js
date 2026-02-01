export function searchLocation(msg) {
  return [msg.geometry.coordinates[1], msg.geometry.coordinates[0]];
};

/**
 *
 * @param {string} text
 * @returns {object} GeoJSON
 */
function geoJSONParser({ text }) {
    if (!text) return;
    const geoJSON = JSON.parse(text);
    const messages = geoJSON.features.map((feature) => {
      return {
        ...feature.properties,
        geometry: feature.geometry,
      }
    });

    return messages;
}

geoJSONParser._name = 'GeoJSON';

export default geoJSONParser;
