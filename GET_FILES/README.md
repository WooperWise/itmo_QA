# PDF Downloader and Parser

This script runs in a Docker container and performs the following tasks:
1. Accepts a website URL via environment variable
2. Navigates to the page
3. Finds the "Скачать учебный план" button
4. Downloads the PDF file
5. Parses the PDF to Markdown format

## Usage

### Using Docker Compose (Recommended)

1. Update the `SCRAPER_URL` environment variable in `docker-compose.yml` to the desired URL
2. Run the container:
   ```bash
   docker-compose up --build
   ```

### Using Docker Directly

1. Build the image:
   ```bash
   docker build -t pdf-downloader .
   ```

2. Run the container with environment variable:
   ```bash
   docker run --rm -e SCRAPER_URL="https://abit.itmo.ru/program/master/ai_product" -v $(pwd)/output:/app/output pdf-downloader
   ```

## Output

The script will generate a unique folder in the `output` directory based on the URL, containing:
- `downloaded_file.pdf`: The downloaded PDF file
- `parsed_content.md`: The PDF content converted to Markdown format

For example, for the URL `https://abit.itmo.ru/program/master/ai_product`, the output will be in:
`output/abit.itmo.ru/program/master/ai_product/`

## Environment Variables

- `SCRAPER_URL`: The URL of the webpage to scrape (required)

## Dependencies

- Python 3.11
- Playwright (for web scraping)
- PyMuPDF (for PDF parsing)