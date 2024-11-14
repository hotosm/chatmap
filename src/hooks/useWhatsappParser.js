import { useState, useEffect } from 'react';

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

// Search for a location
const searchLocation = (line) => {
    const match = line.match(LOCATION_PATTERN);
    if (match) {
        return match[0].split(",").map(x => parseFloat(x))
    }
    return null;
}

// Parse datetime, username and message
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
            datetime: system === "ANDROID" ? parseDateStringAndroid(match[1]) : parseDateStringiOS(match[1]),
            username:  username,
            message: match[3],
        }

        // Look for JPG images
        const jpgIndex = msgObject.message.toLowerCase().indexOf(".jpg");
        if (jpgIndex > 0) {
            msgObject.file = msgObject.message.substring(0,jpgIndex + 4);
        }

        return msgObject;
    }
}

// Parse date strings in the format [DD/MM/YYYY, hh:mm:ss AM/PM]
const parseDateStringiOS = (dateStr) => {
    const dateTime = dateStr.split(",");
    const date = dateTime[0].split("/");
    const fmtDate = [[date[2], date[1], date[0]].join("/"), dateTime[1]].join(" ")
    return new Date(fmtDate);
}

// Parse date strings in the format DD/MM/YY hh:mm a. m./p. m.
const parseDateStringAndroid = (dateStr) => {
    let dateTime = dateStr.replace("a. m.", "AM").replace("p. m.", "PM").split(" ");
    const date = dateTime[0].split("/");
    const fmtDate = [[date[1], date[0], date[2]].join("/"), dateTime[1]].join(" ")
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
        const delta_prev = Math.abs(messages[msgIndex].datetime - messages[prevIndex].datetime);
        prevMessage = {
            index: prevIndex, 
            delta: delta_prev
        }
      }

      // If next message is from the same user
      if (messages[nextIndex] && 
          messages[nextIndex].username === message.username &&
          !nextMessage) {
        const delta_next = Math.abs(messages[msgIndex].datetime - messages[nextIndex].datetime);
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
        const delta_next = Math.abs(messages[msgIndex].datetime - messages[nextIndex].datetime);
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

// Hook for parsing messages from a text
function useWhatsappParser({ text, msgPosition}) {

    const [geoJSON, setGeoJSON] = useState(null);

    useEffect(() => {
        if (!text) return;
        const lines = text.split("\n");
        const geoJSON = {
            type: "FeatureCollection",
            features: []
        };
        let featureObject = {}
        let last_line_is_location = false;

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
                    if (!last_line_is_location) {
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
                        last_line_is_location = true;
                    }
                }

                const isLastMessage = (location && index === msgObjects.length - 1);
                if ((!location && last_line_is_location) || isLastMessage) {
                    const searchIndex = isLastMessage ? index : index - 1
                    switch (msgPosition) {
                        case "before":
                            featureObject.properties = {
                                ...getClosestPrevMessage(messages, searchIndex)
                            };
                            break;
                        case "after":
                            featureObject.properties = {
                                ...getClosestNextMessage(messages, searchIndex)
                            };
                            break;
                        default:
                            featureObject.properties = {
                                ...getClosestMessage(messages, searchIndex)
                            };
                            break;
                        }
                        geoJSON.features.push(featureObject);
                    featureObject = {};
                    last_line_is_location = false;
                }
            }
        });

        if (last_line_is_location) {
            geoJSON.features.push(featureObject);
        }
        setGeoJSON(geoJSON);
    }, [text, msgPosition]);

    return [geoJSON];

}

export default useWhatsappParser;
