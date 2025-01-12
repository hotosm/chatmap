// Get closest message from the same user
export const getClosestMessage = (messages, msgIndex) => {
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
export const getClosestNextMessage = (messages, msgIndex) => {
    return getClosestMessageByDirection(messages, msgIndex, 1);
}

// Get closest previous message from the same user
export  const getClosestPrevMessage = (messages, msgIndex) => {
    return getClosestMessageByDirection(messages, msgIndex, -1);
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