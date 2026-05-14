FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Collect static files (for admin)
RUN python manage.py collectstatic --noinput

EXPOSE 8001

CMD ["gunicorn", "analyticsproject.wsgi:application", "--bind", "0.0.0.0:8001", "--workers", "3"]
