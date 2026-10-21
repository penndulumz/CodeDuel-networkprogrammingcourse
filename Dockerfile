FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/data \
    COOKIE_SECURE=auto \
    FORWARDED_ALLOW_IPS=*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /data

# Render and Railway inject PORT; main.py falls back to 8000 locally.
EXPOSE 8000
CMD ["python", "main.py", "--host", "0.0.0.0"]
