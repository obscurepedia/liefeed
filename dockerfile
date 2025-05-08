# Use an official Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies (including WeasyPrint and PostgreSQL headers)
RUN apt-get update && \
    apt-get install -y \
        build-essential \
        libpq-dev \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libgdk-pixbuf2.0-0 \
        libcairo2 \
        libffi-dev \
        libxml2 \
        libxslt1.1 \
        libjpeg-dev \
        libz-dev \
        curl \
        fonts-liberation \
        fonts-freefont-ttf && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . .

# Install Python dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Expose port (Render uses port 10000 internally)
EXPOSE 10000

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]
