# QA Telegram Bot - Technical Specification

## Implementation Requirements

### 1. Two-Phase RAG Pipeline Components

#### Vector Search Service
- **Input**: User query text
- **Process**: Generate embedding → Search Qdrant → Return 50 most similar chunks
- **Output**: List of 50 document chunks with similarity scores
- **Logging**: Log all 50 results with scores and URLs

#### Phase 1: Top Chunks Extraction
- **Input**: 50 vector search results
- **Process**: Extract top 5 chunks for immediate context (Block 1)
- **Output**: Top 5 chunks with vector search scores
- **Logging**: Log selected chunks with URLs and scores

#### Phase 2: Complete Page Reconstruction
- **Input**: All 50 vector search results
- **Process**:
  1. Identify unique pages from all results
  2. Fetch ALL chunks for each page from Qdrant database
  3. Reconstruct complete pages ordered by `chunk_index`
  4. Use Qwen3-Reranker to score complete pages → Select top 5
- **Output**: Top 5 complete reconstructed pages
- **Logging**: Log page reconstruction process and reranking decisions

#### Two-Phase Answer Generation
- **Input**: Query + Top 5 chunks (Block 1) + Top 5 complete pages (Block 2) + Russian language flag
- **Process**: Create two-phase context prompt → Generate answer with 90% source fidelity
- **Output**: Generated answer text
- **Constraint**: Must base 90% of response on provided sources from both blocks

### 2. Language Handling

#### Russian Detection
```python
def is_russian(text: str) -> bool:
    cyrillic_chars = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
    return cyrillic_chars / len(text) > 0.3 if text else False
```

#### Response Language
- If input is Russian → Respond in Russian
- If input is English → Respond in English
- Use appropriate message templates from constants

### 3. Message Processing

#### Long Message Splitting
- **Trigger**: Response > 4000 characters
- **Process**: Split at sentence boundaries, preserve context
- **Sources**: Add source URLs only to the final message part
- **Format**: `\n\n📚 Источники:\n• Page X: URL\n• Page Y: URL`

#### Enhanced Source Attribution
- **Format**: `{index}. {url} (score: {score:.3f})`
- **Placement**: At the end of response (or final message part)
- **No Deduplication**: Show ALL sources from both chunks and complete pages
- **Dual Sources**: Include both vector search scores and rerank scores
- **Complete Transparency**: Users see exactly which chunks and pages contributed

### 4. Error Handling Strategy

#### Service Failures
- **Qdrant Unavailable**: Return "Database temporarily unavailable" message
- **Ollama Models Down**: Return "AI services temporarily unavailable" message  
- **No Results Found**: Return "No relevant information found" message
- **Timeout Errors**: Retry once, then graceful failure

#### Enhanced Logging Requirements
```python
# Log format for vector search (all 50 results)
logger.info(f"Vector search: {len(results)} results for query '{query[:100]}...', scores: max={max_score:.3f}, min={min_score:.3f}, avg={avg_score:.3f}")

# Log format for top chunks selection
logger.info(f"Selected {len(top_chunks)} top chunks for Block 1")

# Log format for page reconstruction
logger.info(f"Identified {len(unique_pages)} unique pages for reconstruction")
logger.info(f"Successfully reconstructed {len(reconstructed_pages)} complete pages")

# Log format for complete page reranking
logger.info(f"Reranker: selected {len(reranked)} from {len(candidates)} results in {duration:.2f}s for query '{query[:100]}...'")

# Log format for two-phase generation
logger.info(f"Two-phase context assembled: {len(chunks)} chunks + {len(pages)} pages, {total_chars} chars (limit: {max_chars})")
logger.info(f"Generated {len(response)} chars ({word_count} words) from {context_chars} chars context in {duration:.2f}s, language: {lang}")
```

### 5. Docker Configuration

#### Environment Variables
```yaml
environment:
  - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
  - QDRANT_HOST=localhost
  - QDRANT_PORT=6333
  - OLLAMA_HOST=host.orb.internal
  - OLLAMA_PORT=11434
  - QDRANT_COLLECTION_NAME=markdown_pages
  - OLLAMA_EMBEDDING_MODEL=dengcao/Qwen3-Embedding-0.6B:Q8_0
  - OLLAMA_RERANKER_MODEL=dengcao/Qwen3-Reranker-0.6B:Q8_0
  - OLLAMA_GENERATION_MODEL=qwen3:4b
```

#### Network Configuration
- Connect to `embeder_app-network` (external)
- Ensure connectivity to Qdrant and Ollama services

### 6. Code Structure

```
botik/
├── bot.py              # Main bot entry point
├── services/
│   ├── __init__.py
│   ├── rag_service.py  # RAG pipeline orchestration
│   ├── embedding_service.py  # Ollama embedding client
│   ├── reranker_service.py   # Ollama reranker client
│   └── llm_service.py        # Ollama generation client
├── utils/
│   ├── __init__.py
│   ├── language_utils.py     # Russian detection
│   ├── message_utils.py      # Message splitting
│   └── logging_utils.py      # Structured logging
├── constants.py        # All constants and messages
└── requirements.txt    # Dependencies
```

### 7. Performance Targets

- **Vector Search**: < 2 seconds for 50 results
- **Reranking**: < 3 seconds for top 10 selection  
- **Generation**: < 10 seconds for typical response
- **Total Response Time**: < 15 seconds end-to-end
- **Memory Usage**: < 512MB per container

### 8. Testing Strategy

#### Unit Tests
- Test each service component independently
- Mock external dependencies (Qdrant, Ollama)
- Verify error handling paths

#### Integration Tests  
- Test complete RAG pipeline
- Test Russian/English language switching
- Test message splitting with various lengths
- Verify source attribution accuracy

#### Manual Testing
- Deploy with docker-compose
- Test with sample Russian and English queries
- Verify logging output and performance metrics
- Test error scenarios (services down, no results)