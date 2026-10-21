/**
 * Tags of a map: the keys it defines (a status, a category...) and the
 * values its points have, coloring the map by one of them. An optional
 * module: it shows when the map is read with its keys (see keysOn in
 * tags.js); without them, the map is as it always was. Everything about it
 * lives in this folder, and the rest of the app only uses what is exported
 * here.
 */
import "./tags.css";

// Reading a map (useApi)
export { withMapTags } from "./useTagsApi.js";
// Showing it (Map)
export { default as useMapTags } from "./useMapTags.js";
export { default as MapTools } from "./MapTools.jsx";
// The popup of a point (Map/popup)
export { default as PointTags } from "./PointTags.jsx";
// Filtering it by tag (TagsOptions)
export { TagFilterItems, tagFilterName } from "./TagFilter.jsx";
// Setting up its tags, for its owner (mapView)
export { default as MapTagsOptions } from "./MapTagsOptions.jsx";
