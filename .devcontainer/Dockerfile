# Simple Python devcontainer with uv
FROM mcr.microsoft.com/devcontainers/python:3.12

# Install uv (project’s Python package manager)
RUN pip install --no-cache-dir uv

# Set working dir for the dev container
WORKDIR /workspaces/bharat-rag

# Optional: pre-create venv so uv uses it
RUN uv sync --dev || true
