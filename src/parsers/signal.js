import { getClosestMessage, getClosestNextMessage, getClosestPrevMessage } from "./chatmap";
import moment from 'moment';

// Regex to search for coordinates in the format <lat>%2C<lon> (ex: -31.006037,-64.262794)
const LOCATION_PATTERN = /[-+]?([1-8]?\d(\.\d+)?|90(\.0+)?)%2C\s*[-+]?(180(\.0+)?|((1[0-7]\d)|([1-9]?\d))(\.\d+)?)$/;

// Search for a location
const searchLocation = (line) => {
    const match = line.match(LOCATION_PATTERN);
    if (match) {
        return match[0].split("%2C").map(x => parseFloat(x))
    }
    return null;
}

// Parse time, username and message
const parseMessage = (line, msg) => {
    const location = searchLocation(line);
    if (location) {
        msg._location = [parseFloat(location[1]), parseFloat(location[0])]
        msg.file = null;
    } else if (line.indexOf("From: ") === 0) {
        msg.username = line.replace("From: ", "");
    } else if (line.indexOf("Sent: ") === 0) {
        msg.timeString = line.replace("Sent: ", "");
        msg.time = parseTimeString(msg.timeString);
    } else if (line.indexOf("Attachment: ") === 0 && line.indexOf(".jpeg") > -1) {
        msg.file = line.substring(12, line.indexOf(".jpeg") + 5);
    } else if (line.indexOf("Attachment: ") === 0 && line.indexOf(".jpg") > -1) {
        msg.file = line.substring(12, line.indexOf(".jpg") + 4);
    } else if (line.indexOf("Attachment: ") === 0 && line.indexOf("jpeg") > -1 && line.indexOf("no filename") > -1 ) {
        const formattedTime = moment.parseZone(msg.timeString).format('YYYY-MM-DD-HH-mm-ss');
        msg.file = `attachment-${formattedTime}.jpg`;
    } else if (!msg.file && !msg.message && line.indexOf("Type: ") === -1 &&
        line.indexOf("Received: ") === -1 && line.indexOf("Conversation: ") === -1) {
        msg.message = line;
    }
}

// Parse time strings
const parseTimeString = (dateStr) => {
    return new Date(dateStr);
}

// Parse messages from lines and create an index
const parseAndIndex = (lines) => {
    const result = {};
    let msg = {};
    let started = false;
    let lastUsername;
    let msgIndex = 0;
    for (const [index, line] of lines.entries()) {
        parseMessage(line, msg);
        let isFrom = line.indexOf("From: ") === 0;
        if (started) {
            if (isFrom) {
                result[msgIndex] = msg;
                lastUsername = msg.username;
                msg = {};
                msgIndex++;
            // Last line
            } else if (index === lines.length - 1 && msg) {
                msg.username = lastUsername;
                result[msgIndex] = msg;
            }
        }
        if (isFrom && !started) {
            started = true;
        }
    }
    return result;
}


export default function signalParser({ text, msgPosition }) {
    if (!text) return;
    const lines = text.split("\n");
    const geoJSON = {
        type: "FeatureCollection",
        features: []
    };
    let featureObject = {}

    const messages = parseAndIndex(lines);
    const msgObjects = Object.values(messages);

    msgObjects.forEach((msgObject, index) => {
        if (msgObject._location) {
            featureObject = {
                type: "Feature",
                properties: {},
                geometry: {
                    type: "Point",
                    coordinates: msgObject._location
                }
            }
            let message;
            switch (msgPosition) {
                case "before":
                    message = getClosestPrevMessage(messages, index);
                    break;
                case "after":
                    message = getClosestNextMessage(messages, index);
                    break;
                default:
                    message = getClosestMessage(messages, index);
                break;
            }
            featureObject.properties = {...message};
            geoJSON.features.push(featureObject);
        }
    });

    return geoJSON;
}
