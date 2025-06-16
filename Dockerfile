# Use a stable, actively maintained image
FROM python:3.9-slim

# Prevent Python from writing .pyc files and enable unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies for WeasyPrint, FFmpeg, Playwright, etc.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
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
        fonts-freefont-ttf \
        ffmpeg \
        libglib2.0-0 \
        libnss3 \
        libatk-bridge2.0-0 \
        libx11-xcb1 \
        libxcomposite1 \
        libxdamage1 \
        libxrandr2 \
        libgbm1 \
        libasound2 \
        libxshmfence1 \
        libgtk-3-0 \
        libxss1 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . .
COPY static/ static/

# Install Python dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Install Playwright dependencies
RUN python -m playwright install --with-deps

# Expose port (Render uses port 10000 internally)
EXPOSE 10000

# Set entrypoint with dynamic task selection
CMD ["sh", "-c", "echo '🔥 Cron job container started'; \
  if [ \"$RUN_TARGET\" = 'post-to-facebook' ]; then python cron/scheduled_job.py; \
  elif [ \"$RUN_TARGET\" = 'send-newsletter' ]; then python cron/newsletter_sender.py; \
  elif [ \"$RUN_TARGET\" = 'post-meme' ]; then python cron/scheduled_meme_job.py; \
  elif [ \"$RUN_TARGET\" = 'post-reel-to-facebook' ]; then python cron/scheduled_reel_job.py; \
  elif [ \"$RUN_TARGET\" = 'validate-new-signups' ]; then python cron/validate_new_signups.py; \
  elif [ \"$RUN_TARGET\" = 'trigger-daily-reel' ]; then python cron/trigger_reel.py; \
  elif [ \"$RUN_TARGET\" = 'subscriber-summary' ]; then python cron/send_subscriber_summary_runner.py; \
  elif [ \"$RUN_TARGET\" = 'send-weekly-newsletter' ]; then python cron/send_weekly_newsletter.py; \
  elif [ \"$RUN_TARGET\" = 'send-3x-newsletter' ]; then python cron/send_newsletter_3x.py; \
  elif [ \"$RUN_TARGET\" = 'worker-reel' ]; then python worker/worker_runner.py; \
  elif [ \"$RUN_TARGET\" = 'send-daily-newsletter' ]; then python cron/send_newsletter_daily.py; \
  else gunicorn --bind 0.0.0.0:10000 web.app:app; \
  fi"]
