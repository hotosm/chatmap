/**
 * Media of the points of a map uploaded from the app, kept in the API v2.
 * It shows in the popup of a point, before the media of the API v1 (`file`)
 * if a point has both; a map without it is as it always was. Everything
 * about it lives in this folder, and the rest of the app only uses what is
 * exported here.
 */

// Reading a map (useApi)
export { withMapMedia } from "./media.js";
// The popup of a point (Map/popup)
export { mediaType } from "./media.js";
