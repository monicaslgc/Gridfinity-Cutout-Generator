# Backend Dockerfile for FastAPI
FROM python:3.11-slim

# Set work directory inside container
WORKDIR /app

# Prevent Python from writing pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY backend/ .

# Expose FastAPI port
EXPOSE 8000

# Run FastAPI with Uvicorn.
# NOTE: this runs the flat main.py, not app/main.py. app/ is a more
# ambitious backend that predates this file but currently fails to import
# (see backend/tests/test_app_package_status.py). Point this at
# "app.main:app" again once that's fixed.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
