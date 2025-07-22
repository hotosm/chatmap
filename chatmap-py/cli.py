#!/usr/bin/python3

###
# ChatMap
# Takes a chat in JSON format and returns a GeoJSON
# with locations and paired messages.
###

from argparse import ArgumentParser
from parser import streamParser
import json

def main():

    parser = ArgumentParser()
    parser.add_argument("file",nargs="*")
    args = parser.parse_args()
    if args.file:
        with open(args.file[0], 'r') as data:
            json_data = json.load(data)
            geoJSON = streamParser(json_data)
            print(json.dumps(geoJSON))
    else:
        "Usage: python cli.py <filename.json>"

if __name__ == "__main__":
    main()