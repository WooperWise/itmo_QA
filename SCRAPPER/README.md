# Web Scraper with Crawl4AI

This project is a web scraping tool built with Crawl4AI that can perform deep crawling of websites and save the results in Markdown format. It's containerized with Docker for easy deployment and execution.

## Project Structure

```
SCRAPPER/
├── Dockerfile.scraper_direct     # Docker image definition
├── docker-compose.yml           # Docker Compose configuration
├── requirements_direct.txt      # Python dependencies
├── scrape_direct.py             # Main scraping script
├── start_direct.sh              # Container startup script
├── README.md                    # This file
└── *.md                         # Output files with scraped content
```

## Features

- Deep web crawling with configurable depth and page limits
- Error-resistant crawling that continues even if individual pages fail
- Duplicate URL detection to avoid redundant scraping
- Markdown output format for easy reading and processing
- Docker containerization for consistent execution environments
- Rich console output with progress indicators and status information
- Support for both command-line arguments and interactive input

## Prerequisites

- Docker and Docker Compose
- At least 4GB of free disk space for browser dependencies

## Quick Start

1. Clone or download this repository
2. Navigate to the SCRAPPER directory
3. Run the scraper with default settings:
   ```bash
   docker-compose up
   ```

## Configuration

The scraper can be configured through environment variables in the `docker-compose.yml` file:

- `SCRAPER_URL`: The starting URL for crawling (default: https://abit.itmo.ru/program/master/ai)
- `SCRAPER_DEPTH`: Maximum depth for deep crawling (default: 2)
- `SCRAPER_MAX_PAGES`: Maximum number of pages to crawl (default: 500)

Example configuration in docker-compose.yml:
```yaml
environment:
  - SCRAPER_URL=https://example.com
  - SCRAPER_DEPTH=3
  - SCRAPER_MAX_PAGES=100
```

## How to Use

### Method 1: Using Docker Compose (Recommended)

1. Modify the environment variables in `docker-compose.yml` as needed
2. Run the scraper:
   ```bash
   docker-compose up
   ```

The results will be saved as Markdown files in the current directory.

### Method 2: Running the Python Script Directly

1. Install the required dependencies:
   ```bash
   pip install -r requirements_direct.txt
   playwright install-deps
   playwright install chromium
   ```

2. Run the scraper:
   ```bash
   python scrape_direct.py [URL] [DEPTH] [MAX_PAGES]
   ```

If no arguments are provided, the script will prompt for input interactively.

## Output Format

The scraper saves results in Markdown format with the following structure:

```markdown
# Crawl Results

Total pages crawled: X

---

## Page 1: [URL]

- **URL**: [URL]
- **Success**: True/False
- **Depth**: [Crawling depth]

### Content

[Scraped content in Markdown format]
```

## Technical Details

### Main Components

1. **scrape_direct.py**: The core scraping script that uses Crawl4AI to perform web crawling
2. **Dockerfile.scraper_direct**: Builds a container with all necessary dependencies
3. **docker-compose.yml**: Orchestrates the scraper service
4. **start_direct.sh**: Container entry point that handles startup logic

### Scraping Process

1. The scraper starts with a given URL
2. It performs a breadth-first search (BFS) crawl up to the specified depth
3. For each page, it extracts content and converts it to Markdown
4. Results are saved to a Markdown file with a name based on the starting URL
5. The process tracks successful pages, failed pages, and duplicates

### Error Handling

- The scraper continues crawling even if individual pages fail
- Duplicate URLs are detected and skipped
- Errors are logged to the console with detailed information
- Failed pages are reported in the summary but don't stop the process

## Dependencies

- [Crawl4AI](https://github.com/unclecode/crawl4ai): Web crawling framework
- Playwright: Browser automation library
- Rich: Beautiful terminal formatting
- HTTPX: HTTP client library

## Troubleshooting

### Common Issues

1. **Docker container fails to start**:
   - Ensure Docker is running
   - Check that ports are not already in use
   - Verify sufficient disk space for browser dependencies

2. **Pages failing to crawl**:
   - Check internet connectivity
   - Some sites may have anti-bot measures
   - Try reducing the crawling depth or page limit

3. **Large output files**:
   - Reduce the maximum number of pages to crawl
   - Increase content filtering thresholds in the script

### Logs and Debugging

The scraper provides detailed console output including:
- Progress indicators
- Success/failure status for each page
- Error messages for failed pages
- Summary statistics at the end of crawling

## Customization

### Modifying Crawling Behavior

You can adjust the crawling behavior by modifying parameters in `scrape_direct.py`:

- `max_depth`: Controls how deep the crawler will follow links
- `max_pages`: Limits the total number of pages crawled
- Content filtering thresholds in the `PruningContentFilter`

### Adding New Features

To extend the scraper functionality:

1. Modify `scrape_direct.py` to add new features
2. Update dependencies in `requirements_direct.txt` if needed
3. Rebuild the Docker image:
   ```bash
   docker-compose build
   ```

## License

This project is provided as-is for educational and research purposes. Please respect the terms of service of websites you crawl and ensure compliance with applicable laws and regulations.