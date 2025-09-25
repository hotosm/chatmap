FROM python:3.11-slim-buster AS builder

WORKDIR /app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt
RUN pip freeze > requirements.lock

COPY db.py ./db.py
COPY run.py ./run.py
COPY main.py ./main.py
COPY data.py ./data.py
COPY stream.py ./stream.py
COPY db.py ./db.py
COPY settings.py ./settings.py

FROM python:3.11-slim-buster

WORKDIR /app

COPY --from=builder /app .
COPY --from=builder /app/requirements.lock .

RUN pip install --no-cache-dir -r requirements.lock

RUN groupadd -r admin && useradd -r -g admin admin

RUN chown -R admin:admin /app

USER admin

ENV UVICORN_HOST="0.0.0.0"

CMD uvicorn main:app --host "$UVICORN_HOST" --port 8000 --log-level info
