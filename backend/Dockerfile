FROM python:3.10-slim

# Non-root user for least-privilege execution
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# System dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies before copying source so the layer is cached
COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/production.txt

# Copy application source
COPY . .

# Create runtime directories and set permissions
RUN mkdir -p media/uploads staticfiles logs data && \
    chown -R appuser:appuser /app

USER appuser

# Collect static files at build time
RUN python manage.py collectstatic --noinput \
    --settings core.settings.production \
    || true   # tolerate DB-less builds

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

CMD ["./start.sh"]
