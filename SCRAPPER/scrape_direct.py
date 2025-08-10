import asyncio
import json
import sys
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

# Import Crawl4AI components
from crawl4ai import (
    AsyncWebCrawler,
    CrawlerRunConfig,
    BFSDeepCrawlStrategy,
    CrawlResult,
    FilterChain,
    ContentTypeFilter,
    DefaultMarkdownGenerator,
    PruningContentFilter
)
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy

# Rich for beautiful console output
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

console = Console()

def print_result_summary(results: List[CrawlResult], title: str = "Crawl Results Summary", max_items: int = 10):
    """Prints a concise summary of crawl results."""
    if not results:
        console.print(f"[yellow]{title}: No results received.[/]")
        return

    console.print(Panel(f"[bold]{title}[/]", border_style="green", expand=False))
    count = 0
    for result in results:
        if count >= max_items:
            console.print(f"... (showing first {max_items} of {len(results)} results)")
            break
        count += 1
        success_icon = "[green]✔[/]" if result.success else "[red]✘[/]"
        url = result.url
        status = getattr(result, 'status_code', 'N/A')
        content_info = ""
        
        # Check if markdown is present
        if result.markdown:
            if hasattr(result.markdown, 'raw_markdown'):
                content_info = f" | Markdown: [cyan]Present ({len(result.markdown.raw_markdown)} chars)[/]"
            else:
                content_info = f" | Markdown: [cyan]Present ({len(str(result.markdown))} chars)[/]"
        elif result.html:
            content_info = f" | HTML Size: [cyan]{len(result.html)}[/]"
        
        console.print(f"{success_icon} URL: [link={url}]{url}[/link] (Status: {status}){content_info}")
        
        # Print depth if available
        if hasattr(result, 'metadata') and result.metadata and 'depth' in result.metadata:
            console.print(f"  Depth: {result.metadata['depth']}")
        
        # Print error if not successful
        if not result.success and hasattr(result, 'error_message') and result.error_message:
            console.print(f"  [red]Error: {result.error_message}[/]")

def save_results_to_markdown(results: List[CrawlResult], filename: str = "crawl_results.md"):
    """Save crawl results to a Markdown file."""
    if not results:
        console.print("[yellow]No results to save.[/]")
        return

    with open(filename, "w", encoding="utf-8") as f:
        f.write("# Crawl Results\n\n")
        f.write(f"Total pages crawled: {len(results)}\n\n")
        f.write("---\n\n")
        
        for i, result in enumerate(results, 1):
            url = result.url
            success = result.success
            depth = result.metadata.get('depth', 'N/A') if result.metadata else 'N/A'
            
            f.write(f"## Page {i}: {url}\n\n")
            f.write(f"- **URL**: {url}\n")
            f.write(f"- **Success**: {success}\n")
            f.write(f"- **Depth**: {depth}\n")
            
            # Handle markdown data
            if result.markdown:
                f.write(f"\n### Content\n\n")
                if hasattr(result.markdown, 'raw_markdown'):
                    f.write(result.markdown.raw_markdown)
                else:
                    f.write(str(result.markdown))
            elif result.html:
                f.write(f"\n### HTML Content (Size: {len(result.html)} characters)\n\n")
                f.write("```html\n")
                # Truncate HTML to avoid extremely large files
                html_content = result.html[:2000] + "..." if len(result.html) > 2000 else result.html
                f.write(html_content)
                f.write("\n```")
            
            f.write("\n\n---\n\n")
    
    console.print(f"[green]Results saved to {filename}[/]")

async def deep_crawl_with_error_resistance(url: str, max_depth: int = 4, max_pages: int = 50) -> List[CrawlResult]:
    """Perform a deep crawl with error resistance - continues even if individual pages fail."""
    console.print(f"[bold cyan]Starting deep crawl of {url} with max depth {max_depth} and max pages {max_pages}[/]")
    
    # Configure the crawler
    config = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_depth=max_depth,
            max_pages=max_pages,
            filter_chain=FilterChain(
                filters=[
                    ContentTypeFilter(allowed_types=["text/html"])
                ]
            )
        ),
        markdown_generator=DefaultMarkdownGenerator(
            content_filter=PruningContentFilter(
                threshold=0.6,
                threshold_type="relative"
            )
        ),
        verbose=True
    )
    
    # Progress tracking
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    )
    
    results = []
    failed_pages = []
    visited_urls = set()  # Set to track visited URLs and avoid duplicates
    
    try:
        async with AsyncWebCrawler() as crawler:
            console.print("[bold]Crawling...[/]")
            
            # Run the crawl
            crawl_results = await crawler.arun(
                url=url,
                config=config
            )
            
            # Process results, filtering out any that cause serialization issues
            if isinstance(crawl_results, list):
                for i, result in enumerate(crawl_results):
                    try:
                        # Try to access key attributes to ensure the result is valid
                        _ = result.url
                        _ = result.success
                        
                        # Check if URL has already been processed
                        if result.url in visited_urls:
                            console.print(f"[yellow]![/] Skipping duplicate URL: {result.url}")
                            continue
                        
                        # Add URL to visited set
                        visited_urls.add(result.url)
                        
                        if result.success:
                            results.append(result)
                            console.print(f"[green]✓[/] Successfully crawled: {result.url}")
                        else:
                            failed_pages.append(result)
                            console.print(f"[red]✗[/] Failed to crawl: {result.url}")
                    except Exception as e:
                        console.print(f"[yellow]![/] Skipping problematic result #{i} due to error: {str(e)}")
                        failed_pages.append(result)
            else:
                # Single result
                try:
                    # Check if URL has already been processed
                    if crawl_results.url in visited_urls:
                        console.print(f"[yellow]![/] Skipping duplicate URL: {crawl_results.url}")
                    else:
                        # Add URL to visited set
                        visited_urls.add(crawl_results.url)
                        
                        if crawl_results.success:
                            results.append(crawl_results)
                            console.print(f"[green]✓[/] Successfully crawled: {crawl_results.url}")
                        else:
                            failed_pages.append(crawl_results)
                            console.print(f"[red]✗[/] Failed to crawl: {crawl_results.url}")
                except Exception as e:
                    console.print(f"[yellow]![/] Skipping problematic result due to error: {str(e)}")
                    failed_pages.append(crawl_results)
                    
    except Exception as e:
        console.print(f"[bold red]Error during crawling:[/]")
        console.print(f"[red]{str(e)}[/]")
        # Even if we have an overall error, we might have partial results
        pass
    
    # Summary
    console.print(f"\n[bold cyan]Crawling Summary:[/]")
    console.print(f"[green]Successful pages: {len(results)}[/]")
    console.print(f"[red]Failed pages: {len(failed_pages)}[/]")
    console.print(f"[blue]Duplicate pages skipped: {len(visited_urls) - len(results) - len(failed_pages)}[/]")
    
    # Print failed pages
    if failed_pages:
        console.print("\n[bold yellow]Failed Pages:[/]")
        for page in failed_pages[:10]:  # Show first 10
            console.print(f"  [red]✗[/] {page.url}")
            if hasattr(page, 'error_message') and page.error_message:
                console.print(f"    Error: {page.error_message}")
        if len(failed_pages) > 10:
            console.print(f"  ... and {len(failed_pages) - 10} more")
    
    return results

async def main():
    # Get URL from command line arguments or stdin
    if len(sys.argv) > 1:
        url = sys.argv[1]
        # Check if depth parameter is provided
        max_depth = 4  # default value
        if len(sys.argv) > 2:
            try:
                max_depth = int(sys.argv[2])
            except ValueError:
                console.print("[yellow]Invalid depth parameter. Using default value of 4.[/]")
                max_depth = 4
        
        # Check if max_pages parameter is provided
        max_pages = 50  # default value
        if len(sys.argv) > 3:
            try:
                max_pages = int(sys.argv[3])
            except ValueError:
                console.print("[yellow]Invalid max_pages parameter. Using default value of 50.[/]")
                max_pages = 50
    else:
        console.print("[bold cyan]Enter the URL to scrape:[/]")
        url = sys.stdin.readline().strip()
        console.print("[bold cyan]Enter the maximum depth (default is 4):[/]")
        depth_input = sys.stdin.readline().strip()
        max_depth = 4  # default value
        if depth_input:
            try:
                max_depth = int(depth_input)
            except ValueError:
                console.print("[yellow]Invalid depth parameter. Using default value of 4.[/]")
        
        console.print("[bold cyan]Enter the maximum number of pages (default is 50):[/]")
        pages_input = sys.stdin.readline().strip()
        max_pages = 50  # default value
        if pages_input:
            try:
                max_pages = int(pages_input)
            except ValueError:
                console.print("[yellow]Invalid max_pages parameter. Using default value of 50.[/]")
    
    if not url:
        console.print("[red]No URL provided. Exiting.[/]")
        return
    
    # Perform deep crawl with error resistance
    results = await deep_crawl_with_error_resistance(url, max_depth=max_depth, max_pages=max_pages)
    
    # Save results to markdown file
    if results:
        # Create filename based on URL
        safe_url = url.replace('http://', '').replace('https://', '').replace('/', '_').replace(':', '_')
        filename = f"{safe_url}_direct_crawl_results.md"
        save_results_to_markdown(results, filename)
    else:
        console.print("[yellow]No successful results to save.[/]")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Execution interrupted by user.[/]")
    except Exception as e:
        console.print(f"\n[bold red]An error occurred during execution:[/]")
        console.print_exception(show_locals=False)