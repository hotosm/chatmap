from datetime import datetime
from chatmap import ChatMap

'''
 Contains a main parser function and supporting fuctions
 for creating a map from a custom conversation log.
'''

def strip_path(filename):
    return filename.split('/')[-1]

def searchLocation(msg):
    if 'location' in msg and msg['location'] != "":
        return msg['location'].split(',')
    return None

# Parse time, username and message
def parseMessage(line):
    msgObject = {
        'time': parseTimeString(line['date']),
        'username': line['from'],
    }
    msgObject['message'] = line['text']
    msgObject['chat'] = line['chat']
    msgObject['location'] = line['location']
    return msgObject


# Parse time strings
def parseTimeString (date_string):
    return datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S%z")

# Parse messages from lines and create an index
def parseAndIndex(lines):
    index = 0
    result = {}
    for line in lines:
        msg = parseMessage(line)
        if msg:
            result[index] = msg
            result[index]['id'] = index
            index += 1
    return result

# Main entry function (receives JSON with messages, returns GeoJSON)
def streamParser(jsonData):
    messages = parseAndIndex(jsonData)
    chatmap = ChatMap(messages, searchLocation)
    geoJSON = chatmap.pairContentAndLocations()
    return geoJSON

