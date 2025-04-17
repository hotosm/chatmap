/*
 * This will be used for all parsers for extracting related messages
 * ex: location + media from chats.
*/

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
export const getClosestMessage = (messages, msgIndex, searchLocation) => {
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

  while (

    // There's a prev or next message
    // but no next or prev messages has been initialited
    (messages[prevIndex] || messages[nextIndex]) && 
    !(nextMessage && prevMessage) ) {

    // If PREV message is from the same user
    if (messages[prevIndex] &&
        // Message from the same user than previous one
        messages[prevIndex].username === message.username &&
       !prevMessage) {
      // Calculate time passed between current and previous message.
      const delta_prev = Math.abs(messages[msgIndex].time - messages[prevIndex].time);
      if (
        messages[prevIndex] &&
        delta_prev < 1800000 &&
        messages[prevIndex].file || (
        messages[prevIndex]?.message &&
        !searchLocation(messages[prevIndex].message))
      ) {
        prevMessage = {
          index: prevIndex, 
          delta: delta_prev
        }
      }
    }

    // If NEXT message is from the same user
    if (messages[nextIndex] && 
        // Message from the same user than next one
        messages[nextIndex].username === message.username &&
        !nextMessage) {
      // Calculate time passed between current and next message.
      const delta_next = Math.abs(messages[msgIndex].time - messages[nextIndex].time);

      if (
        messages[nextIndex] &&
        delta_next < 1800000 &&
        messages[nextIndex].file || (
        messages[nextIndex]?.message &&
        !searchLocation(messages[nextIndex].message))
      ) {
        nextMessage = {
            index: nextIndex, 
            delta: delta_next
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
  // return message;
}


// Get closest next/prev message from the same user
export  const getClosestMessageByDirection = (messages, msgIndex, direction) => {
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
