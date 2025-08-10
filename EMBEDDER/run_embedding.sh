#!/bin/bash

# Script to run the complete embedding process:
# 1. Split the markdown file into pages
# 2. Generate embeddings for each page and store in Qdrant

echo "Starting embedding process..."

# Step 1: Split the markdown file into pages
echo "Step 1: Splitting markdown file into pages..."
python split_md.py

# Step 2: Generate embeddings and store in Qdrant
echo "Step 2: Generating embeddings and storing in Qdrant..."
python embedder.py

echo "Embedding process completed!"