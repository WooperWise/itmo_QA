#!/bin/bash

# Wait for any dependent services if needed
if [ -n "$DEPENDENCY_HOST" ]; then
    echo "Waiting for dependency service at $DEPENDENCY_HOST to be ready..."
    until curl -f http://$DEPENDENCY_HOST >/dev/null 2>&1; do
        echo "Dependency not ready yet, waiting..."
        sleep 5
    done
    echo "Dependency service is ready!"
fi

# Check if URL is provided as an environment variable
if [ -n "$SCRAPER_URL" ]; then
    echo "Starting PDF downloader with URL: $SCRAPER_URL"
    python pdf_downloader.py "$SCRAPER_URL"
else
    echo "Starting PDF downloader..."
    python pdf_downloader.py
fi