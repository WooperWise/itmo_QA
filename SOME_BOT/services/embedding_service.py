"""
Embedding service using Ollama for generating text embeddings.
"""
import logging
import time
from typing import List, Optional
import ollama
from constants import OLLAMA_HOST, OLLAMA_PORT, OLLAMA_EMBEDDING_MODEL
from utils.logging_utils import log_performance, log_error_with_context

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings using Ollama."""
    
    def __init__(self):
        """Initialize the embedding service."""
        self.client = None
        self.model = OLLAMA_EMBEDDING_MODEL
        self._connect()
    
    def _connect(self) -> None:
        """Connect to Ollama service."""
        try:
            host_url = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"
            self.client = ollama.Client(host=host_url)
            logger.info(f"Connected to Ollama at {host_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            self.client = None
    
    def _ensure_connection(self) -> bool:
        """Ensure connection to Ollama service."""
        if self.client is None:
            self._connect()
        return self.client is not None
    
    @log_performance
    def generate_embedding(self, text: str, max_retries: int = 3) -> Optional[List[float]]:
        """
        Generate embedding for given text.
        
        Args:
            text: Text to embed
            max_retries: Maximum number of retry attempts
            
        Returns:
            Embedding vector or None if failed
        """
        if not self._ensure_connection():
            logger.error("Cannot generate embedding: no connection to Ollama")
            return None
        
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return None
        
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                
                response = self.client.embeddings(
                    model=self.model,
                    prompt=text.strip()
                )
                
                duration = time.time() - start_time
                embedding = response.get("embedding")
                
                if embedding:
                    logger.debug(f"Generated embedding of size {len(embedding)} "
                               f"for text length {len(text)} in {duration:.2f}s")
                    return embedding
                else:
                    logger.warning(f"No embedding returned from Ollama for attempt {attempt + 1}")
                    
            except Exception as e:
                duration = time.time() - start_time if 'start_time' in locals() else 0
                logger.warning(f"Embedding attempt {attempt + 1} failed after {duration:.2f}s: {e}")
                
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    log_error_with_context(
                        e, 
                        {
                            'text_length': len(text),
                            'model': self.model,
                            'attempt': attempt + 1
                        }
                    )
        
        logger.error(f"Failed to generate embedding after {max_retries} attempts")
        return None
    
    def generate_embeddings_batch(self, texts: List[str], max_retries: int = 3) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            max_retries: Maximum number of retry attempts per text
            
        Returns:
            List of embedding vectors (None for failed embeddings)
        """
        if not texts:
            return []
        
        logger.info(f"Generating embeddings for {len(texts)} texts")
        embeddings = []
        
        for i, text in enumerate(texts):
            logger.debug(f"Processing text {i+1}/{len(texts)}")
            embedding = self.generate_embedding(text, max_retries)
            embeddings.append(embedding)
        
        successful_count = sum(1 for emb in embeddings if emb is not None)
        logger.info(f"Successfully generated {successful_count}/{len(texts)} embeddings")
        
        return embeddings
    
    def health_check(self) -> bool:
        """
        Check if the embedding service is healthy.
        
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            if not self._ensure_connection():
                return False
            
            # Test with a simple embedding
            test_embedding = self.generate_embedding("test", max_retries=1)
            return test_embedding is not None
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def get_model_info(self) -> dict:
        """
        Get information about the current embedding model.
        
        Returns:
            Dictionary with model information
        """
        return {
            'model': self.model,
            'host': f"{OLLAMA_HOST}:{OLLAMA_PORT}",
            'healthy': self.health_check()
        }