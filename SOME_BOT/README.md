# QA Telegram Bot with RAG

A Telegram bot that answers questions about website content using Retrieval-Augmented Generation (RAG) with Qdrant vector database and Ollama models.

## Features

- 🤖 **Two-Phase RAG Pipeline**: Vector search (50 results) → Top 5 chunks + Complete page reconstruction → Reranking (top 5 pages) → Answer generation
- 🌍 **Multilingual**: Automatic Russian/English detection and response
- 📚 **Enhanced Source Attribution**: Shows all sources from both chunks and complete pages without deduplication
- 📝 **Smart Splitting**: Automatically splits long responses (>4000 chars)
- 🔍 **Comprehensive Logging**: Detailed logs with performance metrics
- 🐳 **Docker Ready**: Complete containerized deployment

## Architecture

```
User Question → Language Detection → Embedding → Vector Search (50)
    ↓
Extract Top 5 Chunks → Identify Unique Pages → Reconstruct Complete Pages
    ↓
Rerank Complete Pages (5) → Two-Phase Context Assembly → LLM Generation → Message Splitting → Response
```

## Models Used

- **Embedding**: `dengcao/Qwen3-Embedding-0.6B:Q8_0`
- **Reranker**: `dengcao/Qwen3-Reranker-0.6B:Q8_0`
- **Generator**: `qwen3:4b`

## Prerequisites

1. **Running Services** (from embeder directory):
   ```bash
   cd ../embeder
   docker-compose up -d  # Starts Qdrant and Ollama
   ```

2. **Indexed Data**: Ensure your website content is already embedded in Qdrant using the embedder service.

3. **Telegram Bot Token**: Create a bot via [@BotFather](https://t.me/botfather) and get the token.

## Quick Start

1. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your Telegram bot token
   ```

2. **Pull Required Models**:
   ```bash
   # Run this to ensure all models are available
   ./pull_models.sh
   ```

3. **Test the Pipeline**:
   ```bash
   python test_rag.py
   ```

4. **Deploy with Docker**:
   ```bash
   docker-compose up -d
   ```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | Required |
| `QDRANT_HOST` | Qdrant hostname | `qdrant` |
| `QDRANT_PORT` | Qdrant port | `6333` |
| `QDRANT_COLLECTION_NAME` | Collection name | `markdown_pages` |
| `OLLAMA_HOST` | Ollama hostname | `host.orb.internal` |
| `OLLAMA_PORT` | Ollama port | `11434` |
| `OLLAMA_EMBEDDING_MODEL` | Embedding model | `dengcao/Qwen3-Embedding-0.6B:Q8_0` |
| `OLLAMA_RERANKER_MODEL` | Reranker model | `dengcao/Qwen3-Reranker-0.6B:Q8_0` |
| `OLLAMA_GENERATION_MODEL` | Generation model | `qwen3:4b` |

### RAG Configuration

- **Vector Search Limit**: 50 initial results
- **Top Chunks for Context**: 5 chunks (Block 1)
- **Complete Pages Limit**: 5 reconstructed pages (Block 2)
- **Max Message Length**: 4000 characters
- **Language Detection**: Cyrillic character ratio > 30%
- **Two-Phase Context**: Separate blocks for chunks and complete pages

## Usage

### Bot Commands

- `/start` - Welcome message and instructions
- `/help` - Show help information
- `/health` - System health check (admin only)

### Asking Questions

Simply send any text message to the bot:

**English Example:**
```
User: What is the main topic of this website?
Bot: Based on the website content, the main topic is...
📚 Sources:
• Page 1: https://example.com/page1
• Page 2: https://example.com/page2
```

**Russian Example:**
```
User: О чём этот сайт?
Bot: На основе содержимого сайта, основная тема...
📚 Источники:
1. https://example.com/page1 (score: 0.832)
2. https://example.com/page2 (score: 0.622)
3. https://example.com/page3 (score: 0.584)
4. https://example.com/page1 (score: 10.000)
5. https://example.com/page2 (score: 10.000)
```

## Development

### Project Structure

```
botik/
├── services/
│   ├── embedding_service.py    # Ollama embedding client
│   ├── reranker_service.py     # Ollama reranker client
│   ├── llm_service.py          # Ollama generation client
│   └── rag_service.py          # RAG pipeline orchestration
├── utils/
│   ├── language_utils.py       # Russian detection
│   ├── message_utils.py        # Message splitting
│   └── logging_utils.py        # Structured logging
├── bot.py                      # Main bot entry point
├── constants.py                # Configuration constants
├── test_rag.py                 # Test script
└── requirements.txt            # Dependencies
```

### Testing

Run the test suite to verify all components:

```bash
python test_rag.py
```

This will test:
- Language detection
- Message splitting
- Service health checks
- RAG pipeline functionality
- Document search

### Logging

The bot generates comprehensive logs:

- **bot.log**: Main application log
- **Console output**: Real-time logging
- **Performance metrics**: Response times, token counts
- **User interactions**: Query logging with anonymization

### Debugging

1. **Check Service Health**:
   ```bash
   python -c "from services.rag_service import RAGService; print(RAGService().health_check())"
   ```

2. **Test Individual Components**:
   ```bash
   python -c "from services.embedding_service import EmbeddingService; print(EmbeddingService().health_check())"
   ```

3. **View Logs**:
   ```bash
   docker-compose logs -f bot
   ```

## Deployment

### Production Deployment

1. **Update Environment**:
   ```bash
   # Set production values in .env
   LOG_LEVEL=INFO
   ```

2. **Deploy**:
   ```bash
   docker-compose up -d
   ```

3. **Monitor**:
   ```bash
   docker-compose logs -f bot
   ```

### Scaling Considerations

- **Memory**: ~512MB per container
- **CPU**: Moderate usage, spikes during inference
- **Network**: Requires connectivity to Qdrant and Ollama
- **Storage**: Logs only, no persistent data

## Troubleshooting

### Common Issues

1. **"No connection to Ollama"**:
   - Verify Ollama is running: `curl http://host.orb.internal:11434/api/tags`
   - Check network connectivity between containers

2. **"Qdrant connection failed"**:
   - Verify Qdrant is running: `curl http://qdrant:6333/collections`
   - Check if collection exists and has data

3. **"Models not found"**:
   - Pull required models: `./pull_models.sh`
   - Verify models are available: `curl http://host.orb.internal:11434/api/tags`

4. **"No relevant content found"**:
   - Check if data is properly indexed in Qdrant
   - Verify embedding model consistency between indexing and querying

### Health Checks

The bot provides health endpoints for monitoring:

```bash
# Check overall health
python -c "from services.rag_service import RAGService; print(RAGService().get_system_info())"
```

## Performance

### Expected Response Times

- **Vector Search**: < 2 seconds
- **Reranking**: < 3 seconds  
- **Generation**: < 10 seconds
- **Total**: < 15 seconds end-to-end

### Optimization Tips

1. **Reduce Context Size**: Limit document chunk sizes
2. **Adjust Limits**: Reduce vector search/reranker limits for faster responses
3. **Model Selection**: Use smaller models for faster inference
4. **Caching**: Implement response caching for common queries

## License

This project is part of a larger RAG system for website QA functionality.