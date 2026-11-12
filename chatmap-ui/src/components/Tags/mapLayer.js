import { UNKNOWN } from "./tags.js";

// A point whose value expired: white, outlined in gray
const UNKNOWN_COLOR = '#FFFFFF';
const UNKNOWN_OUTLINE = '#9A969B';
// A value without a color of its own
const NO_COLOR = '#9A969B';

/**
 * Paint properties for a layer of points, filling each point with the color
 * of the value it shows now for a key (see withShownValues). Points without
 * a value, and removed ones, keep their color.
 *
 * @param {object} key Key the map is colored by, or null
 * @param {array|string} pointColor Color (or expression) of a point without value
 * @returns {object} Paint properties
 */
export const tagsPaint = (key, pointColor) => {
    const values = (key && key.values) || [];
    if (values.length === 0) {
        return { 'circle-color': pointColor, 'circle-stroke-width': 0 };
    }
    const shown = ["coalesce", ["get", "color_value"], ""];
    const hasValue = [
        "all",
        ["!", ["boolean", ["get", "removed"], false]],
        ["in", shown, ["literal", [...values.map((value) => value.id), UNKNOWN]]],
    ];
    return {
        'circle-color': [
            "case",
            hasValue,
            ["match", shown, ...values.flatMap((value) => [value.id, value.color || NO_COLOR]), UNKNOWN_COLOR],
            pointColor,
        ],
        'circle-stroke-color': ["match", shown, UNKNOWN, UNKNOWN_OUTLINE, '#FFFFFF'],
        'circle-stroke-width': ["case", hasValue, 3, 0],
    };
};

// Show the values of a key on one of the layers of the map
export const paintTags = (map, layer, key, pointColor) => {
    const paint = tagsPaint(key, pointColor);
    for (const property in paint) {
        map.setPaintProperty(layer, property, paint[property]);
    }
};
