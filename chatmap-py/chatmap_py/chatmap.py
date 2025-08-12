'''
    This will be used for all parsers for extracting related messages
    ex: location + media from chats.
'''

class ChatMap:

    def __init__(self, messages, searchLocation):
        self.locationMessages = {}
        self.pairedMessagesIds = []
        self.messages = messages
        self.searchLocation = searchLocation
        self.msgObjects = list(messages.values())

    def getMessageFromSameUser (self, index, username, chat, msg_index):
        messages = self.messages
        # If message is from the same user
        if index > -1 and index < len(messages) and messages[index]['username'] == username \
            and messages[index]['chat'] == chat:
            # Calculate time passed between current and previous message.
            delta_diff = abs((messages[msg_index]['time'] - messages[index]['time']).total_seconds() * 1000) # Convert timedelta to milliseconds
            if (messages[index] 
                and delta_diff < 1800000 # 30 min tolerance
                and ('file' in messages[index] or (messages[index]['message'])
            )
            ):
                return {
                    'index': index, 
                    'delta': delta_diff
                }

    '''
    Get closest message (in terms time) from the same user.
    It will scan a dictionary of messages, starting in msgIndex position.
    From that position, it will look for messages of the same user in both
    directions (previous and next), calculate time dalta and return the
    closest one.
    '''
    def getClosestMessage(self, messages, msgIndex):
        # Previous message index
        prevIndex = msgIndex - 1
        # Next message index
        nextIndex = msgIndex + 1
        # Previous message
        prevMessage = None
        # Next message
        nextMessage = None
        # Closest message
        message = messages[msgIndex]

        # Flags for looking for next/prev messages when a location message
        # from same user is found
        stopNext = False
        stopPrev = False

        while (
            # There's a prev or next message, but no both
            (
                (prevIndex > -1 and messages[prevIndex]) or 
                (nextIndex < len(messages) and messages[nextIndex])
            ) and not (nextMessage and prevMessage)
        ):

            # Look for prev message from the same user
            if not prevMessage and not stopPrev:
                prevMessageFromSameUser = self.getMessageFromSameUser(
                    prevIndex,
                    message['username'],
                    message['chat'],
                    msgIndex
                )
                if prevMessageFromSameUser:
                    if self.locationMessages.get(prevMessageFromSameUser['index']):
                        stopPrev = True
                    else:
                        prevMessage = prevMessageFromSameUser

            # Look for next message from the same user
            if not nextMessage and not stopNext:
                nextMessageFromSameUser = self.getMessageFromSameUser(
                    nextIndex,
                    message['username'],
                    message['chat'],
                    msgIndex
                )
                if nextMessageFromSameUser:
                    if self.locationMessages.get(nextMessageFromSameUser['index']):
                        stopNext = True
                    else:
                        nextMessage = nextMessageFromSameUser

            if prevIndex > -1:
                prevIndex -= 1
            nextIndex += 1

        # If there are prev and next messages
        # check the time difference between the two
        # to decide which to return
        if prevMessage and nextMessage:
            if prevMessage.get('delta') == nextMessage.get('delta'):
                if prevMessage['index'] in self.pairedMessagesIds:
                    return messages[prevMessage['index']]
                else:
                    return messages[nextMessage['index']]

            elif prevMessage['delta'] < nextMessage['delta']:
                return messages[prevMessage['index']]
            elif prevMessage['delta'] > nextMessage['delta']:
                return messages[nextMessage['index']]

        elif prevMessage:
            return messages[prevMessage['index']]
        elif nextMessage:
            return messages[nextMessage['index']]

        return message

    # Get closest next/prev message from the same user
    def getClosestMessageByDirection(self, messages, msgIndex, direction):
        nextIndex = msgIndex + direction
        message = messages[msgIndex]
        nextMessage = None
        while (messages[nextIndex]) and not nextMessage:
            if messages[nextIndex] and \
                messages[nextIndex].username == message.username \
                and not nextMessage:
                    delta_next = abs(messages[msgIndex]['time'] - messages[nextIndex]['time'])
                    nextMessage = {
                        'index': nextIndex,
                        'delta': delta_next
                    }
            nextIndex += direction

        if nextMessage:
            return messages[nextMessage.index]
        return message

    def pairContentAndLocations(self):

        msgObjects = self.msgObjects
        messages = self.messages
        searchLocation = self.searchLocation

        # Initialize the GeoJSON response
        geoJSON = {
            'type': "FeatureCollection",
            'features': []
        }

        # A GeoJSON Feature for storing a message
        featureObject = {}

        # Index all messages with location
        for index, msgObject in enumerate(msgObjects):
            # Check if there's a location in the message
            location = searchLocation(msgObject)
            # If there's a location, create a Point.
            if location:
                coordinates = [
                    float(location[1]),
                    float(location[0])
                ]
                # Accept only coordinates with decimals
                if (
                    coordinates[0] % 1 != 0 and 
                    coordinates[1] % 1 != 0
                ):
                    self.locationMessages[index] = [coordinates[0], coordinates[1]]

        # When a location has been found, look for the closest
        # content from the same user and pair it to the message.
        for index, msgObject in enumerate(msgObjects):
            if index in self.locationMessages:
                featureObject = {
                    'type': "Feature",
                    'properties': {},
                    'geometry': {
                        'type': "Point",
                        'coordinates': self.locationMessages[index]
                    }
                }
                message = self.getClosestMessage(messages, index)

                if message:
                        self.pairedMessagesIds.append(message['id'])
                        # Add the GeoJSON feature
                        featureObject['properties'] = {
                            'id': message['id'],
                            'message': message['message'],
                            'username': message['username'],
                            'chat': message['chat'],
                            'time': str(message['time']),
                            'file': str(message['file']),
                            'location': message['location'],
                            'related': message['id']
                        }
                else:
                    # No related message
                    featureObject['properties'] = {
                        'id': msgObject['id'],
                        'username': msgObject['username'],
                        'time': str(msgObject['time']),
                        'message': msgObject['message'],
                        'chat': msgObject['chat'],
                        'time': str(msgObject['time']),
                        'file': str(msgObject['file']),
                        'location': msgObject['location'],
                        'related': msgObject['id']
                    }

                # featureObject['properties']['id'] = index
                if not isinstance(featureObject['properties'].get('time'), int):
                    geoJSON['features'].append(featureObject)

        return geoJSON
