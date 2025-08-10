#!/usr/bin/env python3
"""
Script to generate embeddings for markdown files and store them in Qdrant.
"""

import logging
import os
import re
import time
import uuid
from pathlib import Path

import ollama
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

# Configuration
OLLAMA_MODEL = "dengcao/Qwen3-Embedding-0.6B:Q8_0"
QDRANT_COLLECTION_NAME = "markdown_pages"
PAGES_DIR = "pages"
CHUNK_SIZE = 1000  # Maximum size of content per vector
CHUNK_OVERLAP = 100  # Overlap between chunks in characters
VECTOR_SIZE = 1024  # Size of the embedding vector

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("embedding.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def get_qdrant_client():
    """Initialize and return Qdrant client."""
    return QdrantClient(
        host=os.environ.get("QDRANT_HOST", "localhost"),
        port=os.environ.get("QDRANT_PORT", 6333),
        prefer_grpc=False,  # Use HTTP instead of gRPC to avoid version issues
    )


def create_collection(client):
    """Create Qdrant collection if it doesn't exist."""
    try:
        client.get_collection(QDRANT_COLLECTION_NAME)
        logger.info(f"Collection '{QDRANT_COLLECTION_NAME}' already exists")
    except:
        # Create collection with vector size of 1024
        client.create_collection(
            collection_name=QDRANT_COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        logger.info(
            f"Created collection '{QDRANT_COLLECTION_NAME}' with vector size {VECTOR_SIZE}"
        )


def get_ollama_client():
    """Initialize and return Ollama client."""
    return ollama.Client(
        host=f"http://{os.environ.get('OLLAMA_HOST', 'localhost')}:{os.environ.get('OLLAMA_PORT', 11434)}"
    )


def generate_embedding(client, text):
    """Generate embedding for given text using Ollama."""
    response = client.embeddings(model=OLLAMA_MODEL, prompt=text)
    return response["embedding"]


def generate_embedding_with_retry(client, text, max_retries=3, delay=1):
    """Generate embedding with retry mechanism."""
    for attempt in range(max_retries):
        try:
            response = client.embeddings(model=OLLAMA_MODEL, prompt=text)
            return response["embedding"]
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(delay * (2**attempt))  # Exponential backoff
            else:
                raise e


def upload_point_with_retry(client, point, max_retries=3):
    """Upload a single point to Qdrant with retry mechanism."""
    for attempt in range(max_retries):
        try:
            client.upsert(collection_name=QDRANT_COLLECTION_NAME, points=[point])
            return True
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} to upload point failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2**attempt)  # Exponential backoff
            else:
                logger.error(
                    f"Failed to upload point after {max_retries} attempts: {e}"
                )
                return False


def chunk_content(content, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Split content into chunks of specified size with overlap."""
    if len(content) <= chunk_size:
        return [content]

    chunks = []
    start = 0

    while start < len(content):
        # Calculate end position
        end = start + chunk_size

        # If this is not the last chunk, try to find a good break point
        if end < len(content):
            # Look for sentence endings within the last 200 characters
            search_start = max(start + chunk_size - 200, start)
            search_text = content[search_start:end]

            # Find the last sentence ending
            sentence_endings = [m.end() for m in re.finditer(r"[.!?]\s+", search_text)]
            if sentence_endings:
                # Use the last sentence ending
                end = search_start + sentence_endings[-1]
            else:
                # Look for line breaks
                line_breaks = [m.end() for m in re.finditer(r"\n", search_text)]
                if line_breaks:
                    end = search_start + line_breaks[-1]

        # Extract chunk
        chunk = content[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move start position with overlap
        if end >= len(content):
            break
        start = max(start + chunk_size - overlap, end - overlap)

    return chunks


def extract_metadata_from_content(content):
    """Extract page number and URL from page content header."""
    page_info = None
    page_url = None

    # Look for the pattern: ## Page X: URL
    page_match = re.search(r"## Page (\d+): (http[^\s\n]+)", content)
    if page_match:
        page_info = f"Page {page_match.group(1)}"
        page_url = page_match.group(2)

    # Look for **URL**: pattern
    url_match = re.search(r"\*\*URL\*\*:\s*(http[^\s\n]+)", content)
    if url_match:
        if not page_url:  # Only use this if we didn't find a page URL
            page_url = url_match.group(1)

    return page_info, page_url


def process_markdown_files():
    """Process all markdown files and store embeddings in Qdrant."""
    # Initialize clients
    qdrant_client = get_qdrant_client()
    ollama_client = get_ollama_client()

    # Create collection
    create_collection(qdrant_client)

    # Process each markdown file
    pages_dir = Path(PAGES_DIR)
    if not pages_dir.exists():
        logger.error(f"Pages directory '{PAGES_DIR}' does not exist")
        return

    file_count = 0
    vector_count = 0

    # Get total number of files and chunks for global progress tracking
    all_files = list(pages_dir.glob("*.md"))
    total_files = len(all_files)

    # Calculate total chunks across all files
    total_chunks = 0
    processed_chunks = 0
    for file_path in all_files:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        chunks = chunk_content(content, CHUNK_SIZE, CHUNK_OVERLAP)
        total_chunks += len(chunks)

    logger.info(f"Total files to process: {total_files}, Total chunks: {total_chunks}")

    for idx, file_path in enumerate(all_files):
        file_count += 1
        logger.info(f"Processing {file_path.name}... ({idx + 1}/{total_files})")

        # Read file content
        with open(file_path, "r", encoding="utf-8") as f:
            full_content = f.read()

        # Extract page info and URL from content
        page_info, page_url = extract_metadata_from_content(full_content)

        # Create fallback metadata if not found
        if not page_info and not page_url:
            # Use filename as fallback page info
            page_info = f"File: {file_path.stem}"  # Remove .md extension
            logger.info(
                f"No metadata found in {file_path.name}, using fallback: {page_info}"
            )
        elif not page_info and page_url:
            # If we have URL but no page info, create page info from filename
            page_info = f"File: {file_path.stem}"
            logger.info(
                f"No page info found in {file_path.name}, using fallback: {page_info}"
            )

        # Split content into chunks with overlap
        chunks = chunk_content(full_content, CHUNK_SIZE, CHUNK_OVERLAP)
        logger.info(
            f"Split {file_path.name} into {len(chunks)} chunks with {CHUNK_OVERLAP} char overlap"
        )

        # Generate embedding for each chunk
        for i, chunk in enumerate(chunks):
            try:
                embedding = generate_embedding_with_retry(ollama_client, chunk)
                processed_chunks += 1
                # Calculate and log global progress percentage
                global_progress = (processed_chunks / total_chunks) * 100
                logger.info(
                    f"Generated embedding for {file_path.name} chunk {i+1}/{len(chunks)} (Global: {global_progress:.2f}%) (size: {len(embedding)})"
                )

                # Verify embedding size and pad/truncate if necessary
                if len(embedding) < VECTOR_SIZE:
                    # Pad with zeros if smaller
                    embedding.extend([0.0] * (VECTOR_SIZE - len(embedding)))
                elif len(embedding) > VECTOR_SIZE:
                    # Truncate if larger
                    embedding = embedding[:VECTOR_SIZE]

                # Create point for Qdrant with full metadata
                point = PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding,
                    payload={
                        "filename": file_path.name,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "content": chunk,  # Store full chunk content
                        "full_content": full_content,  # Store complete file content
                        "page_info": page_info,  # Store extracted page info (e.g., "Page 142")
                        "url": page_url,  # Store extracted URL
                        "content_preview": chunk[:500],  # Store preview for logging
                        "chunk_size": len(chunk),
                        "overlap_used": CHUNK_OVERLAP,
                    },
                )
                # Upload point immediately
                if upload_point_with_retry(qdrant_client, point):
                    vector_count += 1
                    logger.info(
                        f"Uploaded point for {file_path.name} chunk {i+1}/{len(chunks)} to Qdrant (Page: {page_info}, URL: {page_url})"
                    )
                else:
                    logger.error(
                        f"Failed to upload point for {file_path.name} chunk {i+1}/{len(chunks)} to Qdrant"
                    )

            except Exception as e:
                processed_chunks += 1
                # Calculate and log global progress percentage even for failed chunks
                global_progress = (processed_chunks / total_chunks) * 100
                logger.error(
                    f"Error generating embedding for {file_path.name} chunk {i+1}: {e} (Global: {global_progress:.2f}%)"
                )
                continue

    logger.info(
        f"Processed {file_count} files and generated {vector_count} vectors with {CHUNK_OVERLAP} character overlap"
    )


if __name__ == "__main__":
    process_markdown_files()
    logger.info("Embedding process completed!")
