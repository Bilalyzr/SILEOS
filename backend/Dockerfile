# Development Dockerfile for Python Backend
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Install system dependencies including Chrome and ChromeDriver
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        libpq-dev \
        gcc \
        libc6-dev \
        libmagic1 \
        curl \
        wget \
        gnupg \
        unzip \
        ca-certificates \
        nodejs \
    && wget -q -O /tmp/google-chrome-key.gpg https://dl-ssl.google.com/linux/linux_signing_key.pub \
    && gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg /tmp/google-chrome-key.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/* /tmp/google-chrome-key.gpg

# ChromeDriver matching the Chrome installed above.
#
# This step used to be missing despite the comment claiming otherwise, which
# left Selenium Manager to fetch the driver at runtime — on the first
# certificate render, from inside the container. That is slow at best and
# fails outright anywhere egress is restricted, and because the renderer falls
# back to the legacy ReportLab design on any error, the symptom was
# "PDF export produces the wrong certificate" rather than a visible failure.
#
# Deliberately non-fatal: if the pinned driver can't be fetched at build time
# we still produce a working image and Selenium Manager remains the fallback.
# The build log says which happened, and /api/v1/admin/certificate-render-check
# reports it at runtime.
RUN set -eux; \
    CHROME_VERSION="$(google-chrome-stable --version | awk '{print $3}')"; \
    DRIVER_URL="https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip"; \
    if wget -q -O /tmp/chromedriver.zip "$DRIVER_URL"; then \
        unzip -q /tmp/chromedriver.zip -d /tmp; \
        mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver; \
        chmod +x /usr/local/bin/chromedriver; \
        rm -rf /tmp/chromedriver.zip /tmp/chromedriver-linux64; \
        echo "ChromeDriver pinned: $(chromedriver --version)"; \
    else \
        echo "WARNING: could not fetch ChromeDriver ${CHROME_VERSION}; falling back to Selenium Manager at runtime"; \
    fi

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire backend directory to /app
COPY . .

# Create directories for uploads and logs
RUN mkdir -p uploads certificates logs

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
