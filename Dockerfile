ARG BASE_IMAGE="python:3.11-slim-bullseye"

FROM ${BASE_IMAGE} AS base

ARG NETWORK=test

ENV NETWORK=${NETWORK}

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    pkg-config \
    libssl-dev \
    libglib2.0-dev \
    libgirepository1.0-dev \
    libgtk-3-dev \
    libgdk-pixbuf2.0-dev \
    libcairo2-dev \
    libpango1.0-dev \
    libsoup2.4-dev \
    libwebkit2gtk-4.0-dev \
    libjavascriptcoregtk-4.0-dev \
    && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y \
    && apt-get clean

ENV PATH="/root/.cargo/bin:${PATH}"

RUN rustc --version && cargo --version

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . ./

RUN echo "Running on NETWORK=${NETWORK}" && cat /dev/null

CMD ["python3", "-m", "neurons.miner"]