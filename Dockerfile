# Autonomous Coding Ensemble System
# Multi-stage Docker build for production deployment

# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim as production

WORKDIR /app

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

# Copy installed packages from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application files
COPY autonomous_ensemble.py .
COPY coding_guide.txt .
COPY post_coding_guide.txt .

# Set ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Add local bin to PATH
ENV PATH=/home/appuser/.local/bin:$PATH

# Default output directory
ENV OUTPUT_DIR=/app/output
RUN mkdir -p ${OUTPUT_DIR}

# Health check - validate guides on startup
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python autonomous_ensemble.py --dry-run --guide coding_guide.txt || exit 1

# Default command shows help
ENTRYPOINT ["python", "autonomous_ensemble.py"]
CMD ["--help"]

# Labels for container metadata
LABEL org.opencontainers.image.title="Code Cobra" \
      org.opencontainers.image.description="Autonomous Coding Ensemble System - Multi-agent AI for code generation" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.source="https://github.com/kase1111-hash/Code_Cobra" \
      org.opencontainers.image.licenses="MIT"
