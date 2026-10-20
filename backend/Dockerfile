FROM python:3.11-slim

# Mencegah pembuatan file .pyc dan memastikan output langsung dicetak ke log
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instal dependensi sistem yang dibutuhkan untuk kompilasi dan PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Salin requirements dan instal paket Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Salin seluruh kode backend ke container
COPY . .

# Port default FastAPI
EXPOSE 8000

# Jalankan uvicorn dengan reload aktif untuk mode development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

