FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-v4.txt .
RUN pip install --no-cache-dir -r requirements-v4.txt

RUN python -m playwright install chromium --with-deps || true

COPY . .

RUN mkdir -p /app/data/uploads /app/data/output /app/data/assets /app/app_data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
