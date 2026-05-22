FROM python:3.11-slim AS base

RUN groupadd -r app && useradd -r -g app -d /app -s /sbin/nologin app

WORKDIR /app

COPY requirements-v4.txt .
RUN pip install --no-cache-dir -r requirements-v4.txt && \
    playwright install chromium --with-deps || true

COPY app/ app/

RUN mkdir -p /app/data/uploads /app/data/output /app/app_data && \
    chown -R app:app /app

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]