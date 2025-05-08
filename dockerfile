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

# Dynamically run different tasks based on RUN_TARGET
CMD ["sh", "-c", "\
  if [ \"$RUN_TARGET\" = 'post-to-facebook' ]; then python -m utils.scheduled.scheduled_job; \
  elif [ \"$RUN_TARGET\" = 'send-newsletter' ]; then python -m utils.email.newsletter_sender; \
  elif [ \"$RUN_TARGET\" = 'post-meme' ]; then python -m utils.scheduled.scheduled_meme_job; \
  elif [ \"$RUN_TARGET\" = 'post-reel' ]; then python -m utils.scheduled.scheduled_reel_job; \
  else gunicorn --bind 0.0.0.0:10000 app:app; \
  fi"]
