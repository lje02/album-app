FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-enhanced.txt .

RUN pip install --no-cache-dir -r requirements-enhanced.txt

COPY bot-enhanced.py bot.py
COPY .env .env

RUN mkdir -p downloads logs backups

VOLUME ["/app/downloads", "/app/logs"]

CMD ["python", "bot.py"]
