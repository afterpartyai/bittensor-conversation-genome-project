ARG BASE_IMAGE="python:3.11-slim-bullseye"

# Base stage with common dependencies
FROM ${BASE_IMAGE} AS base

# Create a non-root user
RUN useradd -ms /bin/bash appuser

ARG NETWORK=test
ENV NETWORK=${NETWORK}

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install necessary packages and clean up
RUN apt-get update && apt-get install -y --no-install-recommends \
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
    && apt-get purge --auto-remove -y curl build-essential pkg-config \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.cargo/bin:${PATH}"

# Check rust and cargo versions
RUN rustc --version && cargo --version

# Copy only requirements first for better caching
COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . ./

# Switch to non-root user
USER appuser

# Define different targets for different networks
# Mainnet target
FROM base AS miner_mainnet
CMD ["python3", "-m", "neurons.miner_mainnet"]

# Testnet target
FROM base AS miner_testnet
CMD ["python3", "-m", "neurons.miner_testnet"]

# Local target
FROM base AS miner_local
CMD ["python3", "-m", "neurons.miner_local"]

# Mainnet target
FROM base AS validator_mainnet
CMD ["python3", "-m", "neurons.validator_mainnet"]

# Testnet target
FROM base AS validator_testnet
CMD ["python3", "-m", "neurons.validator_testnet"]

# Local target
FROM base AS validator_local
CMD ["python3", "-m", "neurons.validator_local"]