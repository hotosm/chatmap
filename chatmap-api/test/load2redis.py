'''
 ChatMap utility for testing
 Load messages from JSON file to Redis
'''

import argparse
import json
import redis
from datetime import datetime

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

class StreamIdGenerator:
    def __init__(self):
        self.last_ms = None
        self.counter = 0

    def generate_stream_id(self, item):
        dt = datetime.fromisoformat(item.get("date"))
        ms = int(dt.timestamp() * 1000)
        if ms == self.last_ms:
            self.counter += 1
        else:
            self.counter = 0
            self.last_ms = ms

        return f"{ms}-{self.counter}"

def main():
    args = argparse.ArgumentParser()
    args.add_argument("--file", "-f", help="File", type=str, default=None)
    args = args.parse_args()
    if args.file:
        with open(args.file) as file:
            data = json.loads("\n".join(file.readlines()))
            sorted_data = sorted(
                data,
                key=lambda item: datetime.fromisoformat(item["date"])
            )
            streamIdGenerator = StreamIdGenerator()
            for _, item in enumerate(sorted_data):
                streamID = streamIdGenerator.generate_stream_id(item)
                msg = {
                    'id': streamID,
                    'stream': "messages:123456",
                    'message': {
                        "id":      streamID,
                        "user":    item.get('user') or "",
                        "from":    item.get('from') or "",
                        "chat":    item.get('chat') or "",
                        "text":    item.get('text') or "",
                        "date":    item.get('date') or "",
                        "location": item.get('location') or "",
                        "file": item.get('file') or ""
                    }
                }
                r.xadd(msg['stream'], msg['message'], id=streamID)

    else:
        print("ChatMap testing utility load2redis")
        print("")
        print("This script can read locations shared on a chat JSON log file")
        print("and save them into Redis")
        print("")
        print("Usage: python load2redis.py -f messages.json")

if __name__ == "__main__":
    main()