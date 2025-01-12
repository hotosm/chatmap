import { getClosestMessage, getClosestNextMessage, getClosestPrevMessage } from "./chatmap";

function stripPath(filename) {
    return filename.substring(filename.lastIndexOf("/") + 1, filename.length);
}

// Look for jpg or mp4 media files
const lookForMediaFile = (msgObject) => {
    const msg = msgObject.message.toLowerCase();
    let mediaFileIndex = msg.indexOf(".jpg");
    if (mediaFileIndex < 0) {
        mediaFileIndex = msg.indexOf(".mp4");
    }
    if (mediaFileIndex > 0) {
        return msgObject.message.substring(0,mediaFileIndex + 4);
    }
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
            index++;
        }
    })
    return result;
}

export default function telegramParser({ text, msgPosition }) {
    if (!text) return;
    const json = JSON.parse(text);
    const geoJSON = {
        type: "FeatureCollection",
        features: []
    };
    // Creates an indexed dictionary for messages

    const messages = parseAndIndex(json.messages);
    const msgObjects = Object.values(messages);

    msgObjects.forEach((msgObject, index) => {
        if (msgObject.location) {
            let featureObject = {
                type: "Feature",
                properties: {},
                geometry: {
                    type: "Point",
                    coordinates: [
                        msgObject.location[1],
                        msgObject.location[0]
                    ]
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
