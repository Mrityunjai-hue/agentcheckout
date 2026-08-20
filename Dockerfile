# Production Dockerfile for AgentCheckout

FROM python:3.11-slim

# Prevent Python from writing pyc files to disc and buffering stdout/stderr
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt-get/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt psycopg2-binary

# Copy application source code
COPY . .

# Build dataset, train model, and seed initial database
RUN python ml/prepare_dataset.py && \
    python ml/train_model.py && \
    python ml/simulate_uplift.py && \
    python seed_data.py

EXPOSE 8000

# Run FastAPI / FastMCP server with Uvicorn
CMD ["uvicorn", "mcp_server.server:app", "--host", "0.0.0.0", "--port", "8000"]
