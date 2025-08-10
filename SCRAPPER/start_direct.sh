#!/bin/sh

# Wait for Crawl4AI service to be ready if it's running in a separate container
if [ -n "$CRAWL4AI_HOST" ]; then
    echo "Waiting for Crawl4AI service at http://$CRAWL4AI_HOST:11235 to be ready..."
    until curl -f http://$CRAWL4AI_HOST:11235/health >/dev/null 2>&1; do
        echo "Crawl4AI not ready yet, waiting..."
        sleep 5
    done
    echo "Crawl4AI service is ready!"
else
    echo "Running in direct mode with local Crawl4AI installation"
fi

# Check if URL is provided as an environment variable
if [ -n "$SCRAPER_URL" ]; then
    echo "Starting direct scraper with URL: $SCRAPER_URL"
    if [ -n "$SCRAPER_DEPTH" ] && [ -n "$SCRAPER_MAX_PAGES" ]; then
        echo "Using depth: $SCRAPER_DEPTH, max pages: $SCRAPER_MAX_PAGES"
        python scrape_direct.py "$SCRAPER_URL" "$SCRAPER_DEPTH" "$SCRAPER_MAX_PAGES"
    elif [ -n "$SCRAPER_DEPTH" ]; then
        echo "Using depth: $SCRAPER_DEPTH, default max pages: 50"
        python scrape_direct.py "$SCRAPER_URL" "$SCRAPER_DEPTH"
    else
        echo "Using default depth: 4, default max pages: 50"
        python scrape_direct.py "$SCRAPER_URL"
    fi
else
    echo "Starting direct scraper..."
    python scrape_direct.py
fi