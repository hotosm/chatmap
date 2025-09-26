FROM python:3.11-slim-buster AS builder

WORKDIR /app

COPY db.py ./db.py
COPY run.py ./run.py
COPY main.py ./main.py
COPY data.py ./data.py
COPY stream.py ./stream.py
COPY db.py ./db.py
COPY settings.py ./settings.py
COPY uv.lock ./uv.lock

FROM python:3.11-slim-buster

WORKDIR /app

COPY --from=builder /app .
COPY --from=builder /app/uv.lock .
RUN uv sync --locked
RUN groupadd -r admin && useradd -r -g admin admin

RUN chown -R admin:admin /app

USER admin

ENV UVICORN_HOST="0.0.0.0"

CMD uv run uvicorn main:app --host "$UVICORN_HOST" --port 8000 --log-level info
