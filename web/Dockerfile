ARG BASE_IMAGE="python:3.11-slim-bullseye@sha256:7af2c2c559edb3388e5e86fb7d2a9b9b25ebb3851bcc86a9669d11cbc870c823"

# Base stage with common dependencies
FROM ${BASE_IMAGE} AS base

WORKDIR /

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY web/ ./

RUN pip install --no-cache-dir -r requirements.txt

RUN python conversation_data_importer.py

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]