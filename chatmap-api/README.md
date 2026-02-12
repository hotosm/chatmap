# chatmap-api

This is a Python API that serves as a middleware between the front-end and
the IM API connector. It also manages the Redis stream for parsing
locations using the `chatmap-py` package and saves them in the database.

## Setup

You'll need a Redis server with messages (created by `chatmap-im-connector`).

## Install dependencies

```bash
uv sync
```

## Run

```bash
uv uvicorn main:app --reload
```

## Licensing

This project is part of ChatMap

This is free software! you may use this project under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
