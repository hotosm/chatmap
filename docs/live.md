# ChatMap Live + Linked Devices

In this advanced mode users will be able to link devices to ChatMap
for creating live-updated maps.

<img width="542" alt="Screenshot 2025-07-30 at 2 58 23 PM" src="https://github.com/user-attachments/assets/e867eae1-1788-4ab8-a2a4-968a33e1c275" />

# Setup

## Install dependencies

You'll need a Redis server for temporarily storing incoming messages.

## Run IM API connector

Inside `chatmap-wa-connector` you'll find a Go app for connecting to
the WhatsApp API using the whatsmeow library for linking devices and 
receiving messages. All messags will be stored in the Redis queue.

```bash
cd chatmap-wa-connector
go run main.gp
```

## Run ChatMap API

Inside `chatmap-api` you'll find a Python API that serves as a middleware between
the front-end and the IM API connector. It also manages the Redis queue for parsing
locations using the `chatmap-py` package and saves them in the database.

```bash
cd chatmap-api
uvicorn main:app --reload
```

## Run ChatMap Frontend

Run the ChatMap front end with the corresponding flag for enabling live mode:

```bash
VITE_ENABLE_LIVE=1 yarn start
```

Once you have eveything up and running, you'll find a link to the `/linked` page
where users can scan a QR code for link a device. 

Once a device is linked, ChatMap will parse locations + related content from
all incoming messages and update the map in real-time.
