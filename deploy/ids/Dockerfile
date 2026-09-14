# sasha-ids — lightweight IDS watcher container
# Build context is the repo root (see docker-compose.ids.yml).
FROM python:3.12-alpine

# docker-cli lets the watcher run `docker exec sasha-edge nginx -s reload`
RUN apk add --no-cache docker-cli

WORKDIR /app
COPY scripts/ids_watch.py /app/ids_watch.py

# stdlib only — nothing to install
ENTRYPOINT ["python3", "/app/ids_watch.py"]
