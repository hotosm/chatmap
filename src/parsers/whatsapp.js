// Regex to search for coordinates in the format <lat>,<lon> (ex: -31.006037,-64.262794)
const LOCATION_PATTERN = /[-+]?([1-8]?\d(\.\d+)?|90(\.0+)?),\s*[-+]?(180(\.0+)?|((1[0-7]\d)|([1-9]?\d))(\.\d+)?)$/;

// Regex to search for messages in the format [<date>, <time>] <username>: <message>
const MSG_PATTERN = {
    IOS: /\[(.*)\] (.*): (.*)/,
    ANDROID: /(.*) - (.*): (.*)/
}

// Detect system (Android or iOS)
const detectSystem = (line) => {
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

// Search for a location
const searchLocation = (line) => {
    const match = line.match(LOCATION_PATTERN);
    if (match) {
        return match[0].split(",").map(x => parseFloat(x))
    }
    return null;
}

// Parse time, username and message
const parseMessage = (line, system) => {
    const match = line.match(MSG_PATTERN[system]);
    if (match) {
        let username = match[2];

        // Check if the username has a ':' character and remove the text after it
        const usernameIndexOf = username.indexOf(":");
        if (usernameIndexOf > -1) {
            username = username.substring(0, usernameIndexOf);
        }

        let msgObject = {
            time: system === "ANDROID" ?
                parseTimeStringAndroid(match[1]) :
                parseTimeStringiOS(match[1]),
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

// Parse time strings in the format [hh:mm:ss AM/PM]
const parseTimeStringiOS = (dateStr) => {
    const dateTime = dateStr.split(",");
    let fmtDate;
    const now = new Date();
    fmtDate = [[now.getFullYear(), now.getMonth(), now.getDay()].join("/"), dateTime[1]].join(" ")
    return new Date(fmtDate);
}


// Parse time strings in the format hh:mm a. m./p. m.
const parseTimeStringAndroid = (dateStr) => {
    let dateTime = dateStr.replace("a. m.", "AM").replace("p. m.", "PM").split(" ");
    const date = dateTime[0].split("/");
    let fmtDate;
    const now = new Date();
    fmtDate = [[now.getFullYear(), now.getMonth(), now.getDay()].join("/"), dateTime[1]].join(" ")
    return new Date(fmtDate);
}

// Get closest message from the same user
const getClosestMessage = (messages, msgIndex) => {
    let prevIndex = msgIndex - 1;
    let nextIndex = msgIndex + 1;
    let prevMessage;
    let nextMessage;
    let message = messages[msgIndex];

    while (

      // There's a prev or next message
      // and the next message is different from the prev one
      (messages[prevIndex] || messages[nextIndex]) && 
      !(nextMessage && prevMessage) ) {

      // If prev message is from the same user
      if (messages[prevIndex] &&
          messages[prevIndex].username === message.username &&
         !prevMessage) {
        const delta_prev = Math.abs(messages[msgIndex].time - messages[prevIndex].time);
        prevMessage = {
            index: prevIndex, 
            delta: delta_prev
        }
      }

      // If next message is from the same user
      if (messages[nextIndex] && 
          messages[nextIndex].username === message.username &&
          !nextMessage) {
        const delta_next = Math.abs(messages[msgIndex].time - messages[nextIndex].time);
        nextMessage = {
            index: nextIndex, 
            delta: delta_next
        }
      }

      prevIndex--;
      nextIndex++;
    }

    // If there are prev and next messages
    // check the time difference between the two
    // to decide which to return

    if (prevMessage && nextMessage) {

      if (prevMessage.delta === nextMessage.delta) {
        return {
            ...messages[prevMessage.index],
            message: messages[prevMessage.index].message + ". " + messages[nextMessage.index].message
        }
      } else if (prevMessage.delta < nextMessage.delta) {
        return messages[prevMessage.index];
      } else if (prevMessage.delta > nextMessage.delta) {
        return messages[nextMessage.index];
      }

    } else if (prevMessage) {
      return messages[prevMessage.index];
    } else if (nextMessage) {
      return messages[nextMessage.index];
    }
    return message;
}

// Get closest next message from the same user
const getClosestNextMessage = (messages, msgIndex) => {
    return getClosestMessageByDirection(messages, msgIndex, 1);
}

// Get closest previous message from the same user
const getClosestPrevMessage = (messages, msgIndex) => {
    return getClosestMessageByDirection(messages, msgIndex, -1);
}

// Get closest next/prev message from the same user
const getClosestMessageByDirection = (messages, msgIndex, direction) => {
    let nextIndex = msgIndex + direction;
    let nextMessage;
    let message = messages[msgIndex];
    while (
      (messages[nextIndex]) && !(nextMessage) ) {
    
      if (messages[nextIndex] && 
          messages[nextIndex].username === message.username &&
          !nextMessage) {
        const delta_next = Math.abs(messages[msgIndex].time - messages[nextIndex].time);
        nextMessage = {
            index: nextIndex, 
            delta: delta_next
        }
      }
      nextIndex += direction;
    }
    if (nextMessage) {
      return messages[nextMessage.index];
    }
    return message;
}

// Parse messages from lines and create an index
const parseAndIndex = (lines, system) => {
    let index = 0;
    const result = {};
    lines.forEach((line) => {

        // Clean unicode from line
        line = line.replaceAll(/[\u200E\u200F\u202A-\u202E\u200B]/g, '');

        const msg = parseMessage(line, system);
        if (msg) {
            result[index] = msg;
            index++;
        }
    })
    return result;
}


export default function whatsAppParser({ text, msgPosition }) {
    if (!text) return;
    const lines = text.split("\n");
    const geoJSON = {
        type: "FeatureCollection",
        features: []
    };
    let featureObject = {}

    // Creates an indexed dictionary for messages
    let system;
    for (let i = 0; i < lines.length; i++) {
        system = detectSystem(lines[i]);
        if (system !== "UNKNOWN") {
            break;
        }
    };

    const messages = parseAndIndex(lines, system);
    const msgObjects = Object.values(messages);

    msgObjects.forEach((msgObject, index) => {
        if (msgObject.message) {
            const location = searchLocation(msgObject.message);
            if (location) {
                featureObject = {
                    type: "Feature",
                    properties: {},
                    geometry: {
                        type: "Point",
                        coordinates: [
                            parseFloat(location[1]),
                            parseFloat(location[0])
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
        }
    });

    return geoJSON;
}
