import asyncio
import os
import sys
import re
from pathlib import Path
from playwright.async_api import async_playwright
import fitz  # PyMuPDF
from urllib.parse import urljoin, urlparse

def generate_output_dir_name(url: str) -> str:
    """
    Generate a unique directory name based on the URL.
    
    Args:
        url (str): The URL to base the directory name on
        
    Returns:
        str: A safe directory name
    """
    # Parse the URL
    parsed = urlparse(url)
    
    # Extract domain and path
    domain = parsed.netloc.replace("www.", "")
    path = parsed.path.strip("/")
    
    # Replace any non-alphanumeric characters with underscores
    safe_domain = re.sub(r'[^a-zA-Z0-9]', '_', domain)
    safe_path = re.sub(r'[^a-zA-Z0-9]', '_', path)
    
    # Combine them
    if safe_path:
        dir_name = f"{safe_domain}_{safe_path}"
    else:
        dir_name = safe_domain
        
    # Limit length and ensure it's not empty
    dir_name = dir_name[:50]  # Limit to 50 characters
    if not dir_name:
        dir_name = "output"
        
    return dir_name

async def download_and_parse_pdf(url: str, base_output_dir: str = "output") -> str:
    """
    Navigate to a webpage, find the 'Скачать учебный план' button,
    download the PDF, and parse it to Markdown.
    
    Args:
        url (str): The URL of the webpage to scrape
        base_output_dir (str): Base directory to save output files
        
    Returns:
        str: Path to the generated Markdown file
    """
    # Generate unique output directory name based on URL
    unique_dir_name = generate_output_dir_name(url)
    output_dir = os.path.join(base_output_dir, unique_dir_name)
    
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # Set up download handling
            async with page.expect_download() as download_info:
                # Navigate to the page
                print(f"Opening page: {url}")
                await page.goto(url, wait_until="networkidle")
                
                # Wait for the page to load
                await page.wait_for_timeout(3000)
                
                # Look for the "Скачать учебный план" button
                download_button = await page.query_selector("text=Скачать учебный план")
                
                if not download_button:
                    # Try alternative selectors
                    download_button = await page.query_selector("button:has-text('Скачать учебный план')")
                    
                if not download_button:
                    print("Could not find 'Скачать учебный план' button")
                    # Print all buttons for debugging
                    buttons = await page.query_selector_all("button")
                    for button in buttons:
                        text = await button.text_content()
                        if text:
                            print(f"Found button: {text.strip()}")
                    return None
                
                print("Found 'Скачать учебный план' button, clicking it...")
                await download_button.click()
                
                # Wait for download to complete
                download = await download_info.value
                print(f"Download started: {download.suggested_filename}")
                
                # Save the PDF file
                pdf_path = os.path.join(output_dir, "downloaded_file.pdf")
                await download.save_as(pdf_path)
                print(f"PDF saved to: {pdf_path}")
            
            # Parse PDF to Markdown
            markdown_content = parse_pdf_to_markdown(pdf_path)
            
            # Save Markdown file
            md_path = os.path.join(output_dir, "parsed_content.md")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            
            print(f"Markdown saved to: {md_path}")
            
            return md_path
            
        except Exception as e:
            print(f"Error during PDF download and parsing: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            await browser.close()

def parse_pdf_to_markdown(pdf_path: str) -> str:
    """
    Parse a PDF file and convert it to Markdown format.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        str: Markdown content
    """
    try:
        # Open the PDF
        doc = fitz.open(pdf_path)
        markdown_content = []
        
        # Process each page
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # Extract text
            text = page.get_text("text")
            
            # Add page separator and content
            if page_num > 0:
                markdown_content.append("\n\n---\n\n")
            
            markdown_content.append(f"# Page {page_num + 1}\n\n")
            markdown_content.append(text)
        
        doc.close()
        return "".join(markdown_content)
    
    except Exception as e:
        print(f"Error parsing PDF: {str(e)}")
        return f"Error parsing PDF: {str(e)}"

async def main():
    # Get URL from environment variable or command line argument
    url = os.getenv("SCRAPER_URL")
    
    if not url and len(sys.argv) > 1:
        url = sys.argv[1]
    
    if not url:
        print("Please provide a URL via SCRAPER_URL environment variable or as a command line argument")
        return
    
    print(f"Starting PDF download and parsing for: {url}")
    
    # Run the download and parse function
    result_path = await download_and_parse_pdf(url)
    
    if result_path:
        print(f"Successfully parsed PDF. Markdown saved to: {result_path}")
    else:
        print("Failed to download and parse PDF")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())