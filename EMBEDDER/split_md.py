#!/usr/bin/env python3
"""
Script to split a large markdown file into smaller chunks by pages.
Each page is identified by a header like "## Page X: URL".
"""

import os
import re
from pathlib import Path


def split_md_file(input_file, output_dir):
    """
    Split a markdown file into separate files based on page headers.

    Args:
        input_file (str): Path to the input markdown file
        output_dir (str): Directory to save the split files
    """
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Read the entire file
    with open(input_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Find all page headers
    page_pattern = r"## Page \d+: .+?(?=\n## Page \d+: |\Z)"
    pages = re.findall(page_pattern, content, re.DOTALL)

    print(f"Found {len(pages)} pages in the document")

    # Save each page to a separate file
    total_pages = len(pages)
    for i, page in enumerate(pages, 1):
        # Calculate and display progress percentage
        progress = (i / total_pages) * 100
        print(f"Processing: {progress:.2f}% ({i}/{total_pages})")
        # Extract page title from the header
        title_match = re.search(r"## Page \d+: (.+)", page)
        if title_match:
            title = title_match.group(1).strip()
            # Create a safe filename
            filename = re.sub(r"[^\w\s-]", "", title).strip().lower()
            filename = re.sub(r"[-\s]+", "_", filename) + ".md"
        else:
            filename = f"page_{i}.md"

        # Full path for the output file
        output_path = os.path.join(output_dir, filename)

        # Write the page content to file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(page.strip())

        print(f"Saved page {i} to {output_path}")


if __name__ == "__main__":
    # Check if file exists in current directory first, then in data directory
    input_file = "data.md"
    if not os.path.exists(input_file):
        input_file = "data/data.md"

    output_dir = "pages"

    split_md_file(input_file, output_dir)
    print("Splitting complete!")
