/*
 * This will be used for all parsers for extracting related messages
 * ex: location + media from chats.
*/

export default class ChatMap {

  constructor (messages, searchLocation, options) {
    this.messages = messages;
    this.searchLocation = searchLocation;
    this.options = options;
    this.notMediaFileMessages = {};
  }

  // An dictionary to keep track of location messages
  locationMessages = {};

  // An array to keep track of the paired messages
  pairedMessagesIds = {};

  getMessageFromSameUser = (nextOrPrevMsgIndex, username, currentMsgIndex) => {
      const messages = this.messages;
      const message = messages[currentMsgIndex];
      const nextOrPrevMsg = messages[nextOrPrevMsgIndex];
      // If message is from the same user
      if (nextOrPrevMsg?.username === username) {
        // Message is not paired yet
        if (
          !this.pairedMessagesIds[nextOrPrevMsg.id]
        ) {
          // Calculate time passed between current and previous message.
          const delta_diff = Math.abs(message.time - nextOrPrevMsg.time);
          if (
            nextOrPrevMsg &&
            delta_diff < 1800000 && // 30 min tolerance
            (
              nextOrPrevMsg.file || (
                nextOrPrevMsg?.message
              )
            )
          ) {
            return {
              index: nextOrPrevMsgIndex,
              delta: delta_diff
            }
          }
        }
      }
  }

  /**
   * Get closest message (in terms time) from the same user.
   * It will scan a dictionary of messages, starting in msgIndex position.
   * From that position, it will look for messages of the same user in both
   * directions (previous and next), calculate time dalta and return the
   * closest one.
   * @param {object} messages Dictionary of messages ex: messages[msgIndex]
   * @param {int} msgIndex A message index
   * @returns {object} message
   */
  getClosestMessage = (messages, msgIndex) => {
    // Previous message index
    let prevIndex = msgIndex - 1;
    // Next message index
    let nextIndex = msgIndex + 1;
    // Previous message
    let prevMessage;
    // Next message
    let nextMessage;
    // Closest message
    let message = messages[msgIndex];

    // Flags for looking for next/prev messages when a location message
    // from same user is found
    let stopNext = false;
    let stopPrev = false;

    const messagesCount = messages.length + 1;

    while (
      // There's a prev or next message, but no both
      (messages[prevIndex] || messages[nextIndex]) && 
      !(nextMessage && prevMessage) ) {

      // Look for prev message from the same user
      if (!prevMessage && !stopPrev) {
        const prevMessageFromSameUser = this.getMessageFromSameUser(
          prevIndex,
          message.username,
          msgIndex
        );

        if (prevMessageFromSameUser) {
          if (prevMessageFromSameUser.location) {
            stopPrev = true;
          } else {
            prevMessage = prevMessageFromSameUser;
          }
        }
      }

      // Look for next message from the same user
      if (!nextMessage && !stopNext) {
        const nextMessageFromSameUser = this.getMessageFromSameUser(
          nextIndex,
          message.username,
          msgIndex
        );

        if (nextMessageFromSameUser) {
          if (nextMessageFromSameUser.location) {
            stopNext = true;
          } else {
            nextMessage = nextMessageFromSameUser;
          }
        }
      }

      if (prevIndex > -1 && !stopPrev) {
        prevIndex--;
      }
      if (nextIndex < messagesCount && !stopNext) {
        nextIndex++;
      }
    }

    // Remove location messages
    if (messages[prevMessage?.index]?.location) {
      prevMessage = null;
    }
    if (messages[nextMessage?.index]?.location) {
      nextMessage = null;
    }

    // If there are prev and next messages
    if (prevMessage && nextMessage) {

      // Return prev or next depending on which one is closer
      if (prevMessage.delta <= nextMessage.delta) {
        return messages[prevMessage.index];
      } else if (prevMessage.delta >= nextMessage.delta) {
        return messages[nextMessage.index];
      }

    // If only prev or next
    } else if (prevMessage) {
      return messages[prevMessage.index];
    } else if (nextMessage) {
        return messages[nextMessage.index];
    }

    // No message to pair has been found, return same message
    return message;
  }

  // Get closest next/prev message from the same user
  getClosestMessageByDirection = (messages, msgIndex, direction) => {
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
      return messages[nextMessage.id];
    }
    return message;
  }


  pairContentAndLocations = () => {

    // Initialize the GeoJSON response
    const geoJSON = {
        type: "FeatureCollection",
        features: []
    };

    // Index messages, add location
    this.messages.forEach((msg, index) => {
      // Save index
      msg.id = index;
      // Check if there's a location in the message
      const location = this.searchLocation(msg);
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
              msg.location = [coordinates[0], coordinates[1]];
          }
      }
    });

    if (this.options.mediaOnly) {
      // Filter messages, keep only the ones with a file or location
      this.messages = this.messages.filter(msg => (
        msg.file || msg.location
      ))
      // Re-index messages
      this.messages = this.messages.map((msg, index) => ({
        ...msg,
        id: index
      }))
    }

    // When a location has been found, look for the closest
    // content from the same user and pair it to the message.
    this.messages.forEach((msg) => {

      if (msg.location) {
        const featureObject = {
            type: "Feature",
            properties: {},
            geometry: {
                type: "Point",
                coordinates: msg.location
            }
        }

        // Get closest message to the location
        const message = this.getClosestMessage(this.messages, msg.id);
        this.pairedMessagesIds[message.id] = true;

        // Check if mediaOnly is enabled before adding the feature
        if (!(this.options.mediaOnly && !message.file)) {

          // Add the GeoJSON feature
          featureObject.properties = {
            ...message,
            message: message.location ? "(Location only)" : message.message
          };
          if (!isNaN(featureObject.properties.time)) {
            geoJSON.features.push(featureObject);
          }
        }

      }
    });
    return geoJSON;
  }

}

export const createChatMapId = () => {
  return (Math.floor(10000 + Math.random() * 90000)).toString();
}

