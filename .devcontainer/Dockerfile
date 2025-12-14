# Simple Python devcontainer with uv
FROM mcr.microsoft.com/devcontainers/python:3.12

# Install system dependencies required for Weekend 5 features
# - ffmpeg: Required for moviepy to extract audio from videos
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install uv (project's Python package manager)
RUN pip install --no-cache-dir uv

# Set working dir for the dev container
WORKDIR /workspaces/bharat-rag

# Optional: pre-create venv so uv uses it
RUN uv sync --dev || true
