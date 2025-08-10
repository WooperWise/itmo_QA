#!/bin/bash

# Wait for Ollama service to be ready
echo "Waiting for Ollama service to be ready..."
until curl -s http://localhost:11434/api/tags >/dev/null; do
    sleep 5
done

echo "Ollama service is ready. Pulling dengcao/Qwen3-Embedding-0.6B:Q8_0 model..."
curl -X POST http://localhost:11434/api/pull -d '{
  "name": "dengcao/Qwen3-Embedding-0.6B:Q8_0"
}'

echo "Model pull completed!"