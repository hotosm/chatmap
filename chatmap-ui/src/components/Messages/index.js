/**
 * Messages of the chat groups of a map, in a page of their own: its owner
 * chooses there the groups of the phone the map listens to, and reads their
 * messages to link them to its places. An optional module: it shows with
 * the keys of the map (see messagesOn in messages.js). Everything about it
 * lives in this folder, and the rest of the app only uses what is exported here.
 */
import "./messages.css";

// The way to them from the map, for its owner (the header of mapView)
export { default as MessagesLink } from "./MessagesLink.jsx";
// The messages linked to the point chosen on the map (mapView)
export { default as PointMessages } from "./PointMessages.jsx";
// Reading them (the page of the messages of a map)
export { default as MessagesInbox } from "./MessagesInbox.jsx";
export { groupMessagesOn, messagesOn, pageOf, pointPanelCover } from "./messages.js";
