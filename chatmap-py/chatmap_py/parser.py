import re
from datetime import datetime
from .chatmap import ChatMap


'''
 Contains a main parser function and supporting fuctions
 for creating a map from a custom conversation log.
'''

LOCATION_PATTERN = re.compile(
    r"""[-+]? (?: [1-8]?\d(?:\.\d+)? | 90(?:\.0+)? ),\s* [-+]? (?: 180(?:\.0+)? | (?:1[0-7]\d|[1-9]?\d)(?:\.\d+)? )""",
    re.VERBOSE,
)

def strip_path(filename):
    return filename.split('/')[-1]

def searchLocation(msg):
    if 'location' in msg and msg['location'] != "" and msg['location'] != None:
        return msg['location'].split(',')
    match = LOCATION_PATTERN.search(msg['message'])
    if not match:
        return None
    lat_lon_str = match.group(0).strip()
    try:
        lat_str, lon_str = lat_lon_str.split(",")
        return [float(lat_str), float(lon_str)]
    except ValueError:
        return None

# Parse time, username and message
def parseMessage(line):
    msgObject = {
        'time': parseTimeString(line.get('date')),
        'username': line.get('from'),
    }
    msgObject['message'] = line.get('text')
    msgObject['id'] = line.get('id')
    msgObject['chat'] = line.get('chat')
    msgObject['file'] = line.get('file')
    msgObject['location'] = line.get('location')
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
            index += 1
    return result

# Main entry function (receives JSON with messages, returns GeoJSON)
def streamParser(jsonData):
    messages = parseAndIndex(jsonData)
    chatmap = ChatMap(messages, searchLocation)
    geoJSON = chatmap.pairContentAndLocations()
    return geoJSON

