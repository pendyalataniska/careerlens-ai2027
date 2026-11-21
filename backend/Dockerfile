FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt /app/requirements.txt
COPY backend/requirements-app.txt /app/requirements-app.txt
RUN pip install --upgrade pip \
    && pip install --index-url https://download.pytorch.org/whl/cpu torch \
    && pip install -r /app/requirements.txt

COPY alembic.ini /app/alembic.ini
COPY backend/alembic /app/backend/alembic
COPY backend/app /app/backend/app
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/backend/var/private-resumes /data/private-resumes \
    && chown -R appuser:appuser /data/private-resumes \
    && chown -R appuser:appuser /app

ENV PYTHONPATH=/app/backend \
    RESUME_STORAGE_DIR=/data/private-resumes
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
