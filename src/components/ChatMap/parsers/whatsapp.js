
/**
 * Contains a main parser function and supporting fuctions
 * for creating a map from a WhatsApp conversation log.
 *
 * The Map is stored in memory as a GeoJSON and a list
 * of media files
 */

import { getClosestMessage } from "../chatmap";
import ignore from "./ignore";

// Regex to search for coordinates in the format <lat>,<lon> (ex: -31.006037,-64.262794)
const LOCATION_PATTERN = /[-+]?([1-8]?\d(\.\d+)?|90(\.0+)?),\s*[-+]?(180(\.0+)?|((1[0-7]\d)|([1-9]?\d))(\.\d+)?).*$/;

// Regex to search for messages in the format [<date>, <time>] <username>: <message>
const MSG_PATTERN = {
    IOS: /\[(.*)\] ([^:]*): (.*)/,
    ANDROID: /(.*) - ([^:]*): (.*)/
}

// Detect system (Android or iOS)
export const detectSystem = (line) => {
    const match_ios = line.match(MSG_PATTERN.IOS);
    const match_android = line.match(MSG_PATTERN.ANDROID);
    if (match_ios) {
        return "IOS";
    } else if (match_android) {
        return "ANDROID"
    }
    return "UNKNOWN";
}

// Look for jpg or mp4 media files
export const lookForMediaFile = (msgObject) => {
    const msg = msgObject.message.toLowerCase();
    let mediaFileIndex = msg.indexOf(".jpg");
    if (mediaFileIndex < 0) {
        mediaFileIndex = msg.indexOf(".mp4");
    }
    if (mediaFileIndex > 0) {
        let path = msgObject.message.substring(msg.lastIndexOf(":") + 1, mediaFileIndex + 4);
        if (path.substring(0, 1) == " ") {
            return path.substring(1, path.length)
        }
        return path;
    }
    return ""
}

// Search for a location
export const searchLocation = (line) => {
    const match = line.match(LOCATION_PATTERN);
    if (match) {
        return match[0].split(",").map(x => parseFloat(x))
    }
    return null;
}

// Parse time, username and message
export const parseMessage = (line, system) => {
    const match = line.match(MSG_PATTERN[system]);
    if (match && ignore.indexOf(match[3]) === -1) {
        let username = match[2];

        // Check if the username has a ':' character and remove the text after it
        const usernameIndexOf = username.indexOf(":");
        if (usernameIndexOf > -1) {
            username = username.substring(0, usernameIndexOf);
        }

        let msgObject = {
            time: parseTimeString(match[1]),
            username:  username,
            message: match[3],
        }

        // Look for media
        msgObject.file = lookForMediaFile(msgObject);
        if (msgObject.file) {
            msgObject.message = "";
        }
        
        return msgObject;
    }
}

// Parse time strings
export const parseTimeString = (dateStr) => {
    let dateTimeStr = dateStr.replace("a. m.", "AM").replace("p. m.", "PM")
    dateTimeStr = dateTimeStr.replace("a.m.", "AM").replace("p.m.", "PM")
    let dateTime = dateTimeStr.split(" ");
    const now = new Date();
    let fmtDate = [[now.getFullYear(), now.getMonth() + 1, now.getDate()].join("/"), dateTime[1]].join(" ")
    return new Date(fmtDate);
}

// Parse messages from lines and create an index
export const parseAndIndex = (lines, system) => {
    let index = 0;
    const result = {};
    lines.forEach((line) => {

        // Clean unicode from line
        line = line.replaceAll(/[\u200E\u200F\u202A-\u202E\u200B]/g, '');

        const msg = parseMessage(line, system);

        if (msg) {
            result[index] = msg;
            result[index].id = index;
            index++;
        } else {
            // If message is just text without datestring,
            // append it to the previous message. Code should be
            // improved but it will work for now.
            if (result[index - 1] && 

                (system == "ANDROID" && line.substring(2,1) !== "/" &&
                line.indexOf("a. m.") == -1 &&
                line.indexOf("p. m.") == -1) ||

                (system == "IOS" &&
                line.indexOf("[") == -1))
            {
                result[index - 1].message += " " + line;
            }
        }
    })
    return result;
}

/**
 *
 * @param {string} text
 * @returns {object} GeoJSON
 */
export default function whatsAppParser({ text }) {
    if (!text) return;

    // Split the full text in lines
    const lines = text.split("\n");

    // Initialize the GeoJSON response
    const geoJSON = {
        type: "FeatureCollection",
        features: []
    };

    // A GeoJSON Feature for storing a message
    let featureObject = {}

    // Detect system (Android, iOS, ...)
    let system;
    for (let i = 0; i < lines.length; i++) {
        system = detectSystem(lines[i]);
        if (system !== "UNKNOWN") {
            break;
        }
    };

    // Get message objects from text lines
    const messages = parseAndIndex(lines, system);
    const msgObjects = Object.values(messages);

    // Read each message.
    // When a location has been found, look for the closest
    // content from the same user, and attach it to the message.
    msgObjects.forEach((msgObject, index) => {
        if (msgObject.message) {

            // Check if there's a location in the message
            const location = searchLocation(msgObject.message);

            // If there's a location, create a Point.
            if (location) {
                const coordinates = [
                    parseFloat(location[1]),
                    parseFloat(location[0])
                ];
                // Accept only coordinates with decimals
                if (
                    coordinates[0] / Math.round(coordinates[0]) !== 1 &&
                    coordinates[1] / Math.round(coordinates[1]) !== 0
                ) {
                    featureObject = {
                        type: "Feature",
                        properties: {},
                        geometry: {
                            type: "Point",
                            coordinates: coordinates
                        }
                    }
                    const message = getClosestMessage(messages, index, searchLocation);
                    // Add the GeoJSON feature
                    if (message) {
                        featureObject.properties = {...message};
                        featureObject.properties.related = message.id;
                        messages[message.id].mapped = true;
                    } else {
                        // No related message
                        featureObject.properties = {
                            username: msgObject.username,
                            time: msgObject.time
                        }
                    }
                    featureObject.properties.id = index;
                    geoJSON.features.push(featureObject);
                    messages[index].mapped = true;
                }
            }
        }
    });

    return {geoJSON, messages};
}
