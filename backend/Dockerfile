FROM python:3.11-slim AS builder

WORKDIR /build

# Install build tools needed to compile C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt \
    && find /install -type d -name "tests" -exec rm -rf {} + 2>/dev/null; \
       find /install -type d -name "test" -exec rm -rf {} + 2>/dev/null; \
       find /install -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null; \
       find /install -name "*.pyc" -delete 2>/dev/null; \
       find /install -name "*.pyo" -delete 2>/dev/null; \
       true

# ---- Production stage ----
FROM python:3.11-slim

WORKDIR /project

# Copy only the installed Python packages from the builder
COPY --from=builder /install /usr/local

# Copy backend source (exclude examples via .dockerignore)
COPY backend/ ./backend/

EXPOSE 6173

CMD ["python", "backend/main.py"]
