# Experimental desktop installable app

This is an experimental app that can be installed on your computer and run as
a standalone desktop application.

## Requirements

To build the app, you need to have Node >20 and npm installed.

Install requirements by running:

`yarn install`

## Building backends

### IM API connector

The instant messaging API connector is a Go app that connects to WhatsApp using the whatsmeow
library. You can build it by going to th the `chatmap-wa-connector` directory and running:

`go build`

### IM API connector

The instant messaging API connector is a Go app that connects to WhatsApp using the whatsmeow
library. You can build it by going to the the `chatmap-wa-connector` directory and running:

`go build`

Then, rename and copy the binary file `chatmap-wa-connector` to `electron-app/backend/chatmap-go`

### ChatMap API

This API servers as a middleware between the front-end and the IM API. You can build it
by going to the `chatmap-api` directory and running:

`pyinstaller --onefile run.py`

Then, rename and copy the binary file to `electron-app/backend/chatmap-api`

### ChatMap front-end

For building the fron-end, go to the root folder and type:

`yarn build`

Then, copy all files from the `build` directory to `electron-app/public.

## Run Electron app

Finally, for running the Electron app, go to the `electron-app` directory and run:

`yarn start`

You can also package it by running:

`yarn build`

