FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY server/ server/
COPY client/ client/
COPY scripts/ scripts/

# Install Python dependencies (fastembed uses ONNX, no PyTorch needed)
RUN pip install --no-cache-dir ".[server]"

# Create data directory
RUN mkdir -p /app/data /app/knowledge_base

# Expose port
EXPOSE 8000

# Run the server
CMD ["python", "-m", "uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
