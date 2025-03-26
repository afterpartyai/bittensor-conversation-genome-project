ARG BASE_IMAGE="python:3.11-slim-bullseye"

# Base stage with common dependencies
FROM ${BASE_IMAGE} AS base

# Create a non-root user
RUN useradd -ms /bin/bash appuser

WORKDIR .

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy only requirements first for better caching
COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Switch to non-root user
USER appuser

# Create the miners bittensor directory
RUN mkdir -p ~/.bittensor/miners

# Use the entrypoint script to decide which target to run
ENTRYPOINT ["/entrypoint.sh"]