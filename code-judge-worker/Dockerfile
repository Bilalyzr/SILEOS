# Pinned to Debian 12: Playwright 1.48 installs Chromium's system libraries
# for bookworm, not for the newer Debian that the unpinned slim tag now uses.
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

RUN useradd --create-home --uid 10001 judgeworker
WORKDIR /app
COPY requirements.txt .
# Chromium (and its system libraries) renders HTML/CSS submissions. It is
# installed to a shared path so the unprivileged worker user can launch it.
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m playwright install --with-deps chromium \
    && chmod -R a+rX /ms-playwright \
    && rm -rf /var/lib/apt/lists/*
COPY worker.py web_check.py ./
USER 10001

CMD ["python", "worker.py"]
