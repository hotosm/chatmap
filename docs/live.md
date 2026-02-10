# ChatMap Live

In this advanced mode users will be able to link devices to ChatMap
for creating live-updated maps.

<img width="906" height="426" alt="Screenshot 2025-11-29 at 12 45 41 PM" src="https://github.com/user-attachments/assets/18677508-035c-407b-aa22-58fba537de0f" />

## Intended cases

It's recommended to use ChatMap Live in one of these ways:

- With a dedicated device/account for receiving all messages, so no personal messages are available. This is usually the case for institutions, organizations and governments. This will enable live map updates but also receiving information (location point, media, text) by direct message, without the need to use a group.

- Using the dedicated/device account as a bot, so other people can invite it to their groups for processing data. This is more useful when you can't have a dedicated device/account but you're worried about your privacy, which make sense because even if ChatMap is storing data encrypted there's always a risk.

- Running ChatMap on your on premises. Another option that we're exploring is to have a desktop or mobile app.

# Setup (with Docker)

Just make sure to set encryption keys if you're setting up ChatMap for production:

* `CHATMAP_ENC_KEY` (32 byte long string)
* `CHATMAP_SECRET_KEY`

And the flags for enabling both auth + live features:

* `ENABLE_LIVE=true`
* `ENABLE_AUTH=true`

Then just run Docker compose:

`docker compose -f compose.dev.yml up`

You'll be able to access ChatMap in port 5173

`http://localhost:5173`

## Supported IM apps

It only works with WhatsApp for now, but other connectors will be developed, starting
with Signal and Telegram.

## How it works?

ChatMap Live uses a bridge to WhatsApp based on [whatsmeow](https://github.com/tulir/whatsmeow) for receiving messages and store them in a Redis stream. Media files are not downloaded, but a reference to them is stored, while text messages are encrypted. A Python API periodically get messages from the stream and parse them using [chatmap-py](https://pypi.org/project/chatmap-py/), saving the resulting points in a Postgres/PostGIS database. Only text and media messages for map points are decrypted and stored, all other messages are not stored and deleted from the Redis stream. Finally, the UI make requests to the API for getting a QR code, request a session and display the points into the map.

We plan to add more bridges in the future, to support Telegram and Signal, but maybe also other apps. 

<img width="1510" height="907" alt="Screenshot 2025-11-29 at 12 47 46 PM" src="https://github.com/user-attachments/assets/33cca86a-e63d-4369-aa79-aff117470654" />

