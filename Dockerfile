# agentrubric web dashboard + REST API
FROM python:3.12-slim

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir ".[web]"

# Evaluations persist in a SQLite file under /data (mount a volume to keep them).
ENV AGENTRUBRIC_DB=/data/agentrubric.db
VOLUME ["/data"]
EXPOSE 8000

# Bind to all interfaces inside the container.
CMD ["sh", "-c", "agentrubric serve --db \"$AGENTRUBRIC_DB\" --host 0.0.0.0 --port 8000"]
