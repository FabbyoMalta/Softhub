FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir celery redis
COPY celery_app.py .
CMD ["celery", "-A", "celery_app.celery", "worker", "--loglevel=info"]
