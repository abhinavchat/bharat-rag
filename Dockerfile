# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

# Set a non-root user later if you want; for now root is okay for dev/demo
WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy project files (minimal set)
COPY pyproject.toml uv.lock README.md /app/
COPY src /app/src

# Install dependencies + project
RUN uv sync --frozen --no-dev

# Expose uv's virtualenv
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Default command: run the FastAPI app with uvicorn
CMD ["uvicorn", "bharatrag.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
