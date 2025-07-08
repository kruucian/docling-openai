# Docling Serve with OpenAI Vision OCR
# Minimal CPU-only image

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System deps – poppler for pdf2image
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends poppler-utils && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy source
COPY . /app

# Install runtime deps
RUN pip install --upgrade pip && \
    pip install "uvicorn[standard]" pdf2image pillow && \
    pip install -e ./src/docling-serve

EXPOSE 5001

# Disable UI by default; enable by setting DOCLING_SERVE_ENABLE_UI=1
ENV DOCLING_SERVE_ENABLE_UI=0

CMD ["python", "-m", "docling_serve", "run", "--host", "0.0.0.0", "--port", "5001"]
