FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN adduser --disabled-password --gecos "" appuser
#adding log folder
RUN mkdir -p /app/logs && chown -R appuser:appuser /app
USER appuser

CMD ["python", "app.py"]
