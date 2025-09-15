
/**
 * Contains a main parser function and supporting fuctions
 * for creating a map from a WhatsApp conversation log.
 *
 * The Map is stored in memory as a GeoJSON and a list
 * of media files
 */

import ignore from "./ignore";
import ChatMap from "../chatmap";

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

// Look for jpg, mp4, or audio media files
export const lookForMediaFile = (msgObject) => {
    const msg = msgObject.message.toLowerCase();
    // Supported media extensions
    const extensions = [".jpg", ".mp4", ".ogg", ".opus", ".mp3", ".m4a", ".wav"];
    let mediaFileIndex = -1;
    let foundExt = "";
    for (let ext of extensions) {
        let idx = msg.indexOf(ext);
        if (idx > 0) {
            mediaFileIndex = idx;
            foundExt = ext;
            break;
        }
    }
    if (mediaFileIndex > 0) {
        let path = msgObject.message.substring(msg.lastIndexOf(":") + 1, mediaFileIndex + foundExt.length);
        if (path.substring(0, 1) == " ") {
            return path.substring(1, path.length)
        }
        return path;
    }
    return ""
}

// Search for a location
export const searchLocation = msgObject => {
    if (msgObject.message) {
        const match = msgObject.message.match(LOCATION_PATTERN);
        if (match) {
            return match[0].split(",").map(x => parseFloat(x))
        }
    }
    return null;
}

// Check if message is in list of ignored strings
const isInTheIgnoreList = msg => {
    for (let i = 0; i < ignore.length; i++) {
        if (msg.indexOf(ignore[i]) > -1) {
            return true;
        }
    };
    return false;
}

// Parse time, username and message
export const parseMessage = (line, system) => {
    const match = line.match(MSG_PATTERN[system]);
    if (match && !isInTheIgnoreList(match[3])) {
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
    let fmtDate = [[now.getFullYear(), now.getMonth() + 1, now.getDate()].join("/"), dateTime[1]].join(" ").replace(".", ":")
    return new Date(fmtDate);
}

// Parse messages from lines and create an index
export const parseAndIndex = (lines, system) => {
    let index = 0;
    const result = [];
    lines.forEach((line) => {

        // Clean unicode from line
        line = line.replaceAll(/[\u200E\u200F\u202A-\u202E\u200B]/g, '');

        const msg = parseMessage(line, system);

        if (msg && !isInTheIgnoreList(msg.message)) {
            result.push(msg);
        } else {
            // If message is just text without datestring,
            // append it to the previous message.
            if (result[index - 1] &&
                // FIXME: check asian date formate
                (system == "ANDROID" && line.substring(2,1) !== "/" &&
                    line.indexOf("a. m.") == -1 &&
                    line.indexOf("p. m.") == -1) ||

                (system == "IOS" &&
                line.indexOf("[") == -1))
            {
                result[result.length - 1].message += " " + line;
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
export default function whatsAppParser({ text, options }) {
    if (!text) return;

    // Split the full text in lines
    const lines = text.split("\n");

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
    const chatmap = new ChatMap(messages, searchLocation, options);
    const geoJSON = chatmap.pairContentAndLocations();

    return { geoJSON };
}
