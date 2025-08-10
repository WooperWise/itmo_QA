# Markdown Embedder for RAG

This project processes markdown files, generates embeddings using Ollama, and stores them in Qdrant for use in Retrieval-Augmented Generation (RAG) systems.

## Features

- Splits large markdown files into pages
- Generates embeddings using Ollama with the dengcao/Qwen3-Embedding-0.6B:Q8_0 model
- Creates multiple vectors for large files (chunks over 1000 characters)
- Stores embeddings in Qdrant vector database
- Provides detailed logging to both stdout and log files

## Project Structure

- `data.md` - The input markdown file to process
- `split_md.py` - Script to split the large markdown file into smaller pages
- `embedder.py` - Script to generate embeddings and store them in Qdrant
- `docker-compose.yml` - Docker Compose configuration for all services
- `Dockerfile` - Docker configuration for the services
- `requirements.txt` - Python dependencies
- `embedding.log` - Log file with detailed processing information

## Prerequisites

- Docker and Docker Compose
- NVIDIA GPU (recommended for Ollama)

## Setup and Usage

1. **Start the services:**
   ```bash
   docker-compose up -d
   ```

2. **Wait for services to initialize:**
   - Qdrant will be available on port 6333 (default Qdrant port)
   - Ollama will automatically pull the `dengcao/Qwen3-Embedding-0.6B:Q8_0` model (this may take some time)
   - The markdown file will be automatically split into pages
   - Embeddings will be automatically generated and stored in Qdrant

3. **Monitor the process:**
   ```bash
   docker-compose logs -f
   ```
   
   Or view the log file directly:
   ```bash
   docker-compose exec embedder cat embedding.log
   ```

## Manual Usage

If you prefer to run the steps manually:

1. **Split the markdown file:**
   ```bash
   docker-compose run split-md
   ```

2. **Generate embeddings:**
   ```bash
   docker-compose run embedder
   ```

## Services

- **Qdrant**: Vector database running on port 6333 (default Qdrant port) in host network mode
- **Ollama**: Embedding model service on port 11434 in host network mode
- **split-md**: Service that splits the markdown file into pages
- **Embedder**: Service that generates embeddings and stores them in Qdrant

## Customization

- To use a different markdown file, replace `data.md`
- To use a different embedding model, update the `OLLAMA_MODEL` variable in `embedder.py` and the model name in the ollama service command in `docker-compose.yml`
- To change the chunk size, modify the `CHUNK_SIZE` variable in `embedder.py`
- To change Qdrant port, modify the `QDRANT_PORT` environment variable in the embedder service in `docker-compose.yml`

## Network Configuration

All services now run in host network mode for improved performance and simplified networking. This means:

- Services can access each other using localhost
- No port mapping is required in docker-compose.yml
- Services use their default ports (Qdrant on 6333, Ollama on 11434)