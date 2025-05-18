
/**
 * Contains a main parser function and supporting fuctions
 * for creating a map from a Telegram conversation log.
 *
 * The Map is stored in memory as a GeoJSON and a list
 * of media files
 */

import ChatMap from "../chatmap";

const stripPath = filename => {
    return filename.substring(filename.lastIndexOf("/") + 1, filename.length);
}

const searchLocation = msg => {
    return msg.location;
}


// Parse time, username and message
const parseMessage = (line) => {
    let text = "";
    let msgObject = {
        time: parseTimeString(line.date),
        username: line.from,
    };
    if (Array.isArray(line.text)) {
        line.text.forEach(item => {
            if (item.type === "link") {
                text = item.text;
            }
        });
    } else if (line.text !== "") {
        text = line.text;
    }
    msgObject.message = text;

    if (line.location_information) {
        msgObject.location = [line.location_information.latitude, line.location_information.longitude]; 
    }
    if (line.photo) {
        msgObject.file = stripPath(line.photo);
    }
    if (line.file && line.mime_type === "video/mp4") {
        msgObject.file = stripPath(line.file);
    }
    return msgObject;
}

// Parse time strings
const parseTimeString = (dateStr) => {
    return new Date(dateStr);
}

// Parse messages from lines and create an index
const parseAndIndex = (lines) => {
    let index = 0;
    const result = {};
    lines.forEach((line) => {
        const msg = parseMessage(line);
        if (msg) {
            result[index] = msg;
            result[index].id = index;
            index++;
        }
    })
    return result;
}

export default function telegramParser({ text }) {
    if (!text) return;
    const json = JSON.parse(text);

    // Get message objects
    const messages = parseAndIndex(json.messages);
    const chatmap = new ChatMap(messages, searchLocation);
    const geoJSON = chatmap.pairContentAndLocations();

    return {geoJSON, messages};
}
