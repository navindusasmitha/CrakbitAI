FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml /app/pyproject.toml
COPY crakbit_chain /app/crakbit_chain
COPY scripts /app/scripts

RUN python -m pip install --upgrade pip && \
    python -m pip install /app

ENTRYPOINT []
CMD ["crakchain", "--help"]
