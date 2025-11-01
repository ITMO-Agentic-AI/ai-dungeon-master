FROM python:3.11-slim as builder

WORKDIR /app

RUN pip install poetry==1.8.0

COPY pyproject.toml poetry.lock* ./

RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root --only main

FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY . .

RUN mkdir -p src/data/storage/players \
    && mkdir -p src/data/storage/world \
    && mkdir -p src/data/storage/rules \
    && mkdir -p src/data/storage/logs

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["python", "main.py"]
