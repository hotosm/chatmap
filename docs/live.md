# ChatMap Live + Linked Devices

In this advanced mode users will be able to link devices to ChatMap
for creating live-updated maps.

<img width="906" height="426" alt="Screenshot 2025-11-29 at 12 45 41 PM" src="https://github.com/user-attachments/assets/18677508-035c-407b-aa22-58fba537de0f" />

## Intended cases

It's recommended to use ChatMap Live in one of these ways:

- With a dedicated device/account for receiving all messages, so no personal messages are available. This is usually the case for institutions, organizations and governments. This will enable live map updates but also receiving information (location point, media, text) by direct message, without the need to use a group.
- Using the dedicated/device account as a bot, so other people can invite it to their groups for processing data. This is more useful when you can't have a dedicated device/account but you're worried about your privaci, which make sense because even if ChatMap is storing data encrypted there's always a risk.

An third option that we want to explore in the future is to have a desktop or mobile app.

Of course that you can always run ChatMap Live **in your own device**, is not that hard! check the docs below.

# Setup (with Docker)

Just make sure to set encryption keys if you're setting up ChatMap for production:

* `CHATMAP_ENC_KEY` (32 byte long string)
* `CHATMAP_SECRET_KEY`

Then just run Docker compose:

`docker compose up -d`

You'll be able to access ChatMap in port 3000

`http://localhost:3000`

# Setup (without Docker)

## Install dependencies

You'll need a Redis server for temporarily storing incoming messages.

### Environmenmt variables

* `CHATMAP_ENC_KEY` - It will be used by `chatmap-im-connector` for encrypting all
incoming text messages and by `chatmap-api` for decrypting text messages
linked to a location.

## Run IM API connector

Inside `chatmap-im-connector` you'll find a Go app for connecting to
the WhatsApp API using the whatsmeow library for linking devices and 
receiving messages. All messages will be stored encrypted in the Redis queue.

```bash
cd chatmap-im-connector
go run main.go
```

## Run ChatMap API

Inside `chatmap-api` you'll find a Python API that serves as a middleware between
the front-end and the IM API connector. It also manages the Redis queue for parsing
locations using the `chatmap-py` package and saves them in the database.

* Install Python requirements using `pip install -r requirements.txt` (a virtual environment is recommended).
* Set a `CHATMAP_SECRET_KEY` environment variable for session encryption

```bash
cd chatmap-api
uvicorn main:app --reload
```

## Run ChatMap Frontend

Install requirements using `yarn install`.

Run the ChatMap front end with the corresponding flag for enabling live mode:

```bash
VITE_ENABLE_LIVE=1 yarn start
```

Once you have everything up and running, you'll find a link to the `/linked` page
where users can scan a QR code for link a device. 

Once a device is linked, ChatMap will parse locations + related content from
all incoming messages and update the map in real-time.

## Supported IM apps

It only works with WhatsApp for now, but other connectors will be developed, starting
with Signal and Telegram.

## How it works?

ChatMap Live uses a bridge to WhatsApp based on [whatsmeow](https://github.com/tulir/whatsmeow) for receiving messages and store them in a Redis stream. Media files are not downloaded, but a reference to them is stored, while text messages are encrypted. A Python API periodically get messages from the stream and parse them using [chatmap-py](https://pypi.org/project/chatmap-py/), saving the resulting points in a Postgres/PostGIS database. Only text and media messages for map points are decrypted and stored, all other messages are not stored and deleted from the Redis stream. Finally, the UI make requests to the API for getting a QR code, request a session and display the points into the map.

We plan to add more bridges in the future, to support Telegram and Signal, but maybe also other apps. 

<img width="1510" height="907" alt="Screenshot 2025-11-29 at 12 47 46 PM" src="https://github.com/user-attachments/assets/33cca86a-e63d-4369-aa79-aff117470654" />

