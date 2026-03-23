FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr libxml2-dev libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY app ./app
COPY evals ./evals
COPY scripts ./scripts
COPY tests ./tests
COPY docs ./docs

RUN pip install --upgrade pip && pip install .

EXPOSE 8000
