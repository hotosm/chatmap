"""
Module for mapping chat messages to geographic locations and pairing them with related content.

This module is designed to extract location data from chat messages and associate
them with nearby messages (e.g., media or text) from the same user, based on time proximity.
"""


class ChatMap:
    """
    A class for mapping chat messages to geographic locations and pairing them with related content.

    This class processes a list of messages, identifies those with location data,
    and pairs them with nearby messages from the same user to form GeoJSON features.
    """

    def __init__(self, messages, searchLocation):
        """
        Initialize the ChatMap instance.

        Args:
            messages (dict): A dictionary of message objects indexed by their IDs.
            searchLocation (callable): A function that extracts location data from a message.
        """        
        self.locationMessages = {}  # Stores indices of messages with valid locations
        self.pairedMessagesIds = []  # Tracks IDs of messages already paired
        self.messages = messages  # Original message data
        self.searchLocation = searchLocation  # Function to extract location from message
        self.msgObjects = list(messages.values())  # List of message objects
        
    def getMessageFromSameUser (self, index, username, chat, msg_index):
        """
        Check if a message at a given index is from the same user and within time tolerance.

        Args:
            index (int): Index of the message to check.
            username (str): Username of the current message.
            chat (str): Chat name of the current message.
            msg_index (int): Index of the reference message.

        Returns:
            dict or None: Dictionary containing index and time delta if conditions are met,
                          otherwise None.
        """
        messages = self.messages
        # Ensure index is valid and message matches user and chat
        if index > -1 and index < len(messages) and messages[index]['username'] == username \
            and messages[index]['chat'] == chat:
            # Compute time difference in milliseconds
            delta_diff = abs((messages[msg_index]['time'] - messages[index]['time']).total_seconds() * 1000) # Convert timedelta to milliseconds
            # Check if message has file or text content and is within time tolerance (30 minutes)
            if (messages[index] 
                and delta_diff < 1800000 # 30 min tolerance
                and ('file' in messages[index] or (messages[index]['message'])
            )
            ):
                return {
                    'index': index, 
                    'delta': delta_diff
                }

    def getClosestMessage(self, messages, msgIndex):
        """
        Find the closest message (in time) from the same user in either direction.

        Scans both forward and backward from the given index to find messages from the same user.
        Returns the one with the smallest time difference, respecting already paired messages.

        Args:
            messages (list): List of message objects.
            msgIndex (int): Index of the reference message.

        Returns:
            dict: The closest message object, or the reference message if none found.
        """
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

            # Look for previous message from the same user
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

            # Update indices
            if prevIndex > -1:
                prevIndex -= 1
            nextIndex += 1
            
        # Determine which message to return based on time delta and pairing status
        prevPaired = prevMessage and prevMessage['index'] in self.pairedMessagesIds
        nextPaired = nextMessage and nextMessage['index'] in self.pairedMessagesIds

        if prevMessage and nextMessage:

            # Prev and next message are in the same distance
            if prevMessage.get('delta') == nextMessage.get('delta'):

                if not prevPaired:
                    return messages[prevMessage['index']]
                elif not nextPaired:
                    return messages[nextMessage['index']]

            elif prevMessage['delta'] < nextMessage['delta']:
                if not prevPaired:
                    return messages[prevMessage['index']]
                elif not nextPaired:
                    return messages[nextMessage['index']]
            elif prevMessage['delta'] > nextMessage['delta']:
                if not nextPaired:
                    return messages[nextMessage['index']]
                elif not prevPaired:
                    return messages[prevMessage['index']]

        elif prevMessage:
             if not prevPaired:
                return messages[prevMessage['index']]
        elif nextMessage:
            if not nextPaired:
                return messages[nextMessage['index']]

        return message

    def getClosestMessageByDirection(self, messages, msgIndex, direction):
        """
        Find the next or previous message from the same user within time tolerance.

        Args:
            messages (list): List of message objects.
            msgIndex (int): Index of the reference message.
            direction (int): Direction to scan (1 for next, -1 for previous).

        Returns:
            dict: The closest matching message or the reference message if none found.
        """
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
        """
        Pair messages with location data to nearby content from the same user.

        Creates a GeoJSON FeatureCollection where each location is paired with the
        nearest message from the same user (based on time), if available.

        Returns:
            dict: A GeoJSON FeatureCollection with location and related message data.
        """
        msgObjects = self.msgObjects
        messages = self.messages
        searchLocation = self.searchLocation

        # Initialize GeoJSON structure
        geoJSON = {
            'type': "FeatureCollection",
            'features': []
        }

        # A GeoJSON Feature for storing a message
        featureObject = {}

        # Index all messages with valid location data
        for index, msgObject in enumerate(msgObjects):
            # Check if there's a location in the message
            location = searchLocation(msgObject)
            # If there's a location, create a Point.
            if location:
                coordinates = [
                    float(location[1]),
                    float(location[0])
                ]
                # Accept only decimal coordinates
                if (
                    coordinates[0] % 1 != 0 and 
                    coordinates[1] % 1 != 0
                ):
                    self.locationMessages[index] = [coordinates[0], coordinates[1]]

        # Pair each location with the closest related message
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
                    if message['id'] not in self.pairedMessagesIds:
                        # Add the GeoJSON feature
                        featureObject['properties'] = {
                            'id': msgObject['id'],
                            'message': message['message'],
                            'username': message['username'],
                            'chat': message['chat'],
                            'time': str(message['time']),
                            'file': message['file'],
                            'related': message['id']
                        }
                        self.pairedMessagesIds.append(message['id'])
                else:
                    # No related message found
                    featureObject['properties'] = {
                        'id': msgObject['id'],
                        'message': msgObject['message'],
                        'username': msgObject['username'],
                        'chat': msgObject['chat'],
                        'time': str(msgObject['time']),
                        'file': msgObject['file'],
                        'related': msgObject['id']
                    }

                 # Ensure time is not an integer (to avoid invalid types)
                if not isinstance(featureObject['properties'].get('time'), int):
                    geoJSON['features'].append(featureObject)
        return geoJSON
