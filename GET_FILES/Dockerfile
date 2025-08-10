FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install-deps
RUN playwright install chromium

# Copy application code
COPY pdf_downloader.py .
COPY start.sh .

# Make the start script executable
RUN chmod +x /app/start.sh

# Command to run the application
CMD ["/app/start.sh"]