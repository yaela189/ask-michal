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

# Install dependencies in small batches to keep peak memory under 512MB
# Batch 1: Core web framework
RUN pip install --no-cache-dir fastapi uvicorn[standard] pydantic pydantic-settings python-multipart

# Batch 2: Database + auth
RUN pip install --no-cache-dir sqlalchemy python-jose[cryptography] google-auth google-auth-oauthlib

# Batch 3: HTTP + AI client
RUN pip install --no-cache-dir httpx anthropic

# Batch 4: PDF processing
RUN pip install --no-cache-dir PyMuPDF

# Batch 5: Vector search (largest packages - install separately)
RUN pip install --no-cache-dir numpy
RUN pip install --no-cache-dir faiss-cpu
RUN pip install --no-cache-dir onnxruntime
RUN pip install --no-cache-dir fastembed

# Install the project itself (deps already satisfied, just registers the package)
RUN pip install --no-cache-dir --no-deps -e .

# Create data directory
RUN mkdir -p /app/data /app/knowledge_base

# Expose port
EXPOSE 8000

# Run the server
CMD ["python", "-m", "uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
