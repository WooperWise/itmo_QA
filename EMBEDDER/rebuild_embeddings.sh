#!/bin/bash

echo "🔄 Rebuilding embeddings with full content..."

# Stop any running containers
echo "Stopping existing containers..."
docker-compose down

# Remove the existing Qdrant data to force a clean rebuild
echo "Removing existing Qdrant data..."
sudo rm -rf qdrant_data/collections/markdown_pages

# Start Qdrant and Ollama services
echo "Starting Qdrant and Ollama services..."
docker-compose up -d qdrant ollama

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 10

# Run the embedder to rebuild with full content
echo "Running embedder with full content..."
docker-compose up --build embedder

echo "✅ Embeddings rebuilt successfully!"
echo "You can now start the bot with: cd ../botik && docker-compose up --build"