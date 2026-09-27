# Stage 1: Build dependencies
FROM python:3.12-slim as builder

WORKDIR /build

# Install system dependencies if required (e.g. gcc, pg_config)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install dependencies into a wheels directory
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Final lightweight image
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed dependencies from builder
COPY --from=builder /root/.local /root/.local
COPY . /app

# Ensure local user binaries are on PATH
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app/app:$PYTHONPATH

EXPOSE 8000

# Run uvicorn server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
