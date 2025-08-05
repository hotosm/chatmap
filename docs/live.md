# ChatMap Live + Linked Devices

In this advanced mode users will be able to link devices to ChatMap
for creating live-updated maps.

<img width="542" alt="Screenshot 2025-07-30 at 2 58 23 PM" src="https://github.com/user-attachments/assets/e867eae1-1788-4ab8-a2a4-968a33e1c275" />

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