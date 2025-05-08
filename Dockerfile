ARG BASE_IMAGE="python:3.11-slim-bullseye@sha256:7af2c2c559edb3388e5e86fb7d2a9b9b25ebb3851bcc86a9669d11cbc870c823"

# Base stage with common dependencies
FROM ${BASE_IMAGE} AS base

WORKDIR /

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install necessary packages and clean up
RUN export DEBIAN_FRONTEND=noninteractive \
    && apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    gcc \
    binutils \
    pkg-config \
    libsoup2.4-dev \
    libjavascriptcoregtk-4.0-dev \
    libpango1.0-dev \
    libgtk-3-dev \
    libwebkit2gtk-4.0-dev \
    libssl-dev \
    openssh-server \
    net-tools \
    bash \
    ca-certificates \
    sudo \
    sqlite3 \
    vim

RUN mkdir /var/run/sshd

# Install rust
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y

# Cleanup
RUN apt-get clean
RUN rm -rf /var/lib/apt/lists/*

# Set the PATH to include cargo
ENV PATH="/root/.cargo/bin:${PATH}"

# Copy only requirements first for better caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY web/ web/
RUN pip install --no-cache-dir -r web/requirements.txt

RUN python web/readyai_conversation_data_importer.py

# Copy the rest of the application code
COPY . .

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create the miners bittensor directory
RUN mkdir -p ~/.bittensor/miners

# Use the entrypoint script to decide which target to run
ENTRYPOINT ["/entrypoint.sh"]