#!/usr/bin/env bash
set -eo pipefail

# run app
if [[ -z "$@" ]]; then
    exec uv run uvicorn main:app --host 0.0.0.0 --port 8000 --log-level warning
else
    exec $@
fi
