#!/usr/bin/env bash
set -eo pipefail

# run migrations
uv run alembic upgrade head

# run app
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --log-level warning
