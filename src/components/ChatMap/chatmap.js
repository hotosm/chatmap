/*
 * This will be used for all parsers for extracting related messages
 * ex: location + media from chats.
*/

export default class ChatMap {

  constructor (messages, searchLocation) {
    this.messages = messages;
    this.searchLocation = searchLocation;
    this.msgObjects = Object.values(messages);
  }

  // An dictionary to keep track of location messages
  locationMessages = {};

  // An array to keep track of the paired messages
  pairedMessagesIds = [];

  getMessageFromSameUser = (index, username, msgIndex) => {
      const messages = this.messages;
        // If message is from the same user
      if (messages[index]?.username === username) {
        // Calculate time passed between current and previous message.
        const delta_diff = Math.abs(messages[msgIndex].time - messages[index].time);
        if (
          messages[index] &&
          delta_diff < 1800000 && // 30 min tolerance
          (
            messages[index].file || (
              messages[index]?.message
            )
          )
        ) {
          return {
            index: index, 
            delta: delta_diff
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
          if (this.locationMessages[prevMessageFromSameUser.index]) {
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
          if (this.locationMessages[nextMessageFromSameUser.index]) {
            stopNext = true;
          } else {
            nextMessage = nextMessageFromSameUser;
          }
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

        if (this.pairedMessagesIds.indexOf(prevMessage.index) === -1) {
          return messages[prevMessage.index];
        } else {
          return messages[nextMessage.index];
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
      return messages[nextMessage.index];
    }
    return message;
  }


  pairContentAndLocations = () => {

    const msgObjects = this.msgObjects;
    const messages = this.messages;
    const searchLocation = this.searchLocation;

    // Initialize the GeoJSON response
    const geoJSON = {
        type: "FeatureCollection",
        features: []
    };

    // A GeoJSON Feature for storing a message
    let featureObject = {}

    // Index all messages with location
    msgObjects.forEach((msgObject, index) => {
      // Check if there's a location in the message
      const location = searchLocation(msgObject);
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
              this.locationMessages[index] = [coordinates[0], coordinates[1]];
          }
      }
    });

    // When a location has been found, look for the closest
    // content from the same user and pair it to the message.
    msgObjects.forEach((msgObject, index) => {
      if (this.locationMessages[index]) {
        featureObject = {
            type: "Feature",
            properties: {},
            geometry: {
                type: "Point",
                coordinates: this.locationMessages[index]
            }
        }
        const message = this.getClosestMessage(messages, index);
        if (message) {
            if (
              this.pairedMessagesIds.indexOf(message.id) === -1
            ) {
              // Add the GeoJSON feature
              featureObject.properties = {
                ...message,
                related: message.id
              };
              this.pairedMessagesIds.push(message.id);
            }
        } else {
            // No related message
            featureObject.properties = {
                username: msgObject.username,
                time: msgObject.time
            }
        }

        featureObject.properties.id = index;
        if (!isNaN(featureObject.properties.time)) {
          geoJSON.features.push(featureObject);
        }
      }
    });
    return geoJSON;
  }

}

