# chatmap-api

This is a Python API that serves as a middleware between the front-end and
the IM API connector. It also manages the Redis queue for parsing
locations using the `chatmap-py` package and saves them in the database.

## Setup

You'll need a Redis server with messages (created by `chatmap-im-connector`).

## Install dependencies

```bash
pip install -r requirements.txt
```

## Run

```bash
uvicorn main:app --reload
```

## Licensing

This project is part of ChatMap

Copyright 2025 Emilio Mariscal

This is free software! you may use this project under the terms of the GNU General Public License (GPL) Version 3.
