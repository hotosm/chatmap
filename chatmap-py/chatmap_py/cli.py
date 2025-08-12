'''
 ChatMap cli
'''

import argparse
import json
from chatmap_py import parser

def main():
    args = argparse.ArgumentParser()
    args.add_argument("--file", "-f", help="File", type=str, default=None)
    args = args.parse_args()
    if args.file:
        with open(args.file) as file:
            # try:
                data = json.loads("\n".join(file.readlines()))
                for idx, item in enumerate(data):
                    item['id'] = idx
                geoJSON = parser.streamParser(data)
                print(json.dumps(geoJSON))
            # except Exception as e:
                # print("Error:", e)

    else:
        print("ChatMap location parser")
        print("")
        print("This script can read locations shared on a chat JSON log file")
        print("and print them as a GeoJSON.")
        print("")
        print("Usage: python chatmap-cli.py -f messages.json")

if __name__ == "__main__":
    main()