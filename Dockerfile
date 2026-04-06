FROM python:3.11-alpine

WORKDIR /app

RUN apk add --no-cache shadow libffi-dev openssl-dev && \
    useradd -m -u 1000 -s /bin/sh appuser

COPY requirements.txt .

RUN pip install --no-cache-dir --root-user-action=ignore -r requirements.txt && \
    apk del --no-cache libffi-dev openssl-dev && \
    find /usr/local/bin -type f \( -name "2to3*" -o -name "idle*" -o -name "pydoc*" -o -name "wheel*" \) -delete 2>/dev/null || true && \
    find /usr/local/lib/python3.11/site-packages -type d \( -name "pip*" -o -name "setuptools*" -o -name "test*" \) -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local/lib/python3.11/site-packages -type d -name "*tests*" -exec rm -rf {} + 2>/dev/null || true

COPY . .

RUN find /app -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    find /app -name "*.pyc" -delete 2>/dev/null || true && \
    mkdir -p logs instance && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 5212

ENV PYTHONUNBUFFERED=1

CMD ["gunicorn", "-k", "eventlet", "-b", "0.0.0.0:5212", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
