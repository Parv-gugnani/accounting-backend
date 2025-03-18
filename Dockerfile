FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p /app/app/static/css /app/app/static/js /app/app/static/img /app/app/templates

# Copy application code
COPY . .

# Make sure the static and template directories exist and have content
RUN ls -la /app/app/static
RUN ls -la /app/app/templates
RUN ls -la /app/app/static/img || echo "No img directory"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8090

# Expose port - Railway will set PORT env var
EXPOSE ${PORT}

# Command to run the application with increased workers and timeout
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 4 --proxy-headers --timeout-keep-alive 75
