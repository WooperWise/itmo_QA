"""
Reranker service using Ollama for reranking search results.
"""
import logging
import time
from typing import List, Dict, Any, Optional, Tuple
import ollama
from constants import OLLAMA_HOST, OLLAMA_PORT, OLLAMA_RERANKER_MODEL, RERANKER_LIMIT
from utils.logging_utils import log_performance, log_error_with_context, log_reranker_results

logger = logging.getLogger(__name__)


class RerankerService:
    """Service for reranking search results using Ollama."""
    
    def __init__(self):
        """Initialize the reranker service."""
        self.client = None
        self.model = OLLAMA_RERANKER_MODEL
        self._connect()
    
    def _connect(self) -> None:
        """Connect to Ollama service."""
        try:
            host_url = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"
            self.client = ollama.Client(host=host_url)
            logger.info(f"Connected to Ollama reranker at {host_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Ollama reranker: {e}")
            self.client = None
    
    def _ensure_connection(self) -> bool:
        """Ensure connection to Ollama service."""
        if self.client is None:
            self._connect()
        return self.client is not None
    
    def _create_reranking_prompt(self, query: str, document: str, document_url: str = "") -> str:
        """
        Create a specialized prompt for reranking documents with focus on ITMO AI programs.
        
        Args:
            query: User's search query
            document: Document content to rank
            document_url: Document URL for additional context
            
        Returns:
            Formatted prompt for reranking with AI program specialization
        """
        return f"""КРИТИЧЕСКАЯ ЗАДАЧА: Оцени релевантность документа для запроса об ИИ программах ИТМО.

ЗАПРОС: {query}

URL ДОКУМЕНТА: {document_url}

ДОКУМЕНТ: {document}

СТРОГИЕ ПРАВИЛА ОЦЕНКИ:

ОЦЕНКА 10 - ТОЛЬКО ДЛЯ ЭТИХ URL:
- https://abit.itmo.ru/program/master/ai
- https://abit.itmo.ru/program/master/ai_product
- URL содержащие "/program/master/ai" или "/program/master/ai_product"

ОЦЕНКА 9 - ДЛЯ СТРАНИЦ С СОДЕРЖАНИЕМ:
- Программа "Искусственный интеллект"
- Программа "Управление ИИ-продуктами"
- Детали этих программ (учебный план, требования, карьера)

ОЦЕНКА 1-3 - ДЛЯ ВСЕХ ОСТАЛЬНЫХ URL:
- student.itmo.ru (любые страницы)
- aspirantura.itmo.ru (любые страницы)
- start.itmo.ru (любые страницы)
- contacts, scholarship, стипендии
- Любые административные страницы

ПРИМЕРЫ ОЦЕНОК:
- URL "https://abit.itmo.ru/program/master/ai" = ОЦЕНКА 10
- URL "https://abit.itmo.ru/program/master/ai_product" = ОЦЕНКА 10
- URL "https://student.itmo.ru/ru/alfa" = ОЦЕНКА 1
- URL "https://aspirantura.itmo.ru?main=4" = ОЦЕНКА 1
- URL "https://mega.itmo.ru/megaschool" = ОЦЕНКА 1
- URL "https://start.itmo.ru" = ОЦЕНКА 1

ФОРМАТ ОТВЕТА: Верни ТОЛЬКО число от 0 до 10. НИКАКОГО текста, объяснений или дополнительных слов.

ПРИМЕРЫ ПРАВИЛЬНЫХ ОТВЕТОВ:
10
1
5

ОТВЕТ:"""
    
    def _get_url_based_score_boost(self, url: str) -> float:
        """
        Get score boost based on URL patterns for AI program prioritization.
        CRITICAL: Ensures target AI program URLs always get maximum scores.
        
        Args:
            url: Document URL
            
        Returns:
            Score boost factor - designed to guarantee score 10 for target URLs
        """
        if not url:
            return 1.0
        
        url_lower = url.lower()
        
        # CRITICAL: Target URLs must ALWAYS get score 10
        # These patterns guarantee maximum score regardless of LLM response
        target_url_patterns = [
            '/program/master/ai_product',
            '/program/master/ai',
            'abit.itmo.ru/program/master/ai'
        ]
        
        for pattern in target_url_patterns:
            if pattern in url_lower:
                # Return boost that guarantees score 10 even if LLM gives low score
                # If LLM gives 1, boost of 10.0 makes final score = 1 * 10 = 10
                # If LLM gives 5, boost of 2.0 makes final score = 5 * 2 = 10
                # We use maximum boost to ensure score 10
                return 10.0  # Maximum boost for target AI programs
        
        # CRITICAL: Low priority URLs get severe penalty
        # These URLs should NEVER rank high
        low_priority_patterns = [
            'student.itmo.ru',
            'aspirantura.itmo.ru',
            'mega.itmo.ru',
            'start.itmo.ru',
            'contacts',
            'scholarship',
            'стипенди',
            'stars.itmo.ru'
        ]
        
        for pattern in low_priority_patterns:
            if pattern in url_lower:
                return 0.1  # Severe penalty - even score 10 becomes 1.0
        
        # Medium priority for other AI-related content
        medium_priority_patterns = [
            'ai.itmo.ru',
            'artificial',
            'intelligence'
        ]
        
        for pattern in medium_priority_patterns:
            if pattern in url_lower:
                return 1.5  # Moderate boost for AI-related content
        
        return 1.0  # No boost or penalty for neutral URLs
    
    @log_performance
    def rerank_documents(self, query: str, documents: List[Dict[str, Any]],
                        limit: int = None, page_groups: Dict[str, List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        Rerank documents based on relevance to the query.
        
        Args:
            query: User's search query
            documents: List of document dictionaries from vector search
            limit: Maximum number of documents to return (default: RERANKER_LIMIT)
            page_groups: Optional dictionary of page groups for page-level reranking
            
        Returns:
            List of reranked documents, sorted by relevance
        """
        if not documents:
            logger.warning("No documents provided for reranking")
            return []
        
        if not self._ensure_connection():
            logger.error("Cannot rerank: no connection to Ollama")
            return documents[:limit or RERANKER_LIMIT]  # Fallback to original order
        
        limit = limit or RERANKER_LIMIT
        start_time = time.time()
        
        # If page groups provided, rerank at page level instead of chunk level
        if page_groups:
            logger.info(f"Reranking {len(page_groups)} pages for query: '{query[:50]}...'")
            scored_documents = self._rerank_pages(query, page_groups)
        else:
            logger.info(f"Reranking {len(documents)} documents for query: '{query[:50]}...'")
            scored_documents = self._rerank_chunks(query, documents)
        
        # Sort by reranker scores (descending)
        scored_documents.sort(key=lambda x: x[1], reverse=True)
        
        # Extract top documents and update their scores
        reranked_docs = []
        for doc, score in scored_documents[:limit]:
            doc_copy = doc.copy()
            doc_copy['rerank_score'] = score
            doc_copy['original_score'] = doc.get('score', 0.0)
            reranked_docs.append(doc_copy)
        
        duration = time.time() - start_time
        
        # Log reranking results
        log_reranker_results(documents, reranked_docs, query, duration, page_groups if 'page_groups' in locals() else None)
        
        logger.info(f"Reranking completed: selected {len(reranked_docs)} documents in {duration:.2f}s")
        
        return reranked_docs
    
    def _get_relevance_score(self, prompt: str, max_retries: int = 3) -> float:
        """
        Get relevance score from the reranker model.
        
        Args:
            prompt: Reranking prompt
            max_retries: Maximum number of retry attempts
            
        Returns:
            Relevance score (0.0-10.0)
        """
        for attempt in range(max_retries):
            try:
                response = self.client.generate(
                    model=self.model,
                    prompt=prompt,
                    options={
                        'temperature': 0.0,  # Zero temperature for deterministic scoring
                        'num_predict': 50,   # More space for response
                        'top_p': 0.1,       # Very focused sampling
                        'repeat_penalty': 1.0,  # No repeat penalty
                    }
                )
                
                response_text = response.get('response', '').strip()
                
                # Extract numeric score from response
                score = self._extract_score(response_text)
                
                if score is not None:
                    return score
                else:
                    logger.warning(f"Attempt {attempt + 1}/{max_retries}: Could not extract score from response: '{response_text}'")
                    
            except Exception as e:
                logger.warning(f"Reranking attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(0.5)  # Brief wait before retry
        
        # Return neutral score if all attempts failed
        logger.warning(f"All {max_retries} reranking attempts failed, returning neutral score")
        return 5.0
    
    def _extract_score(self, response_text: str) -> Optional[float]:
        """
        Enhanced score extraction from reranker response with better fallback handling.
        
        Args:
            response_text: Raw response from reranker
            
        Returns:
            Extracted score or None if not found
        """
        import re
        
        # Clean the response text
        response_text = response_text.strip()
        logger.debug(f"Extracting score from response: '{response_text}'")
        
        # Look for numeric patterns in order of preference
        patterns = [
            r'^(\d+(?:\.\d+)?)$',                    # Just a number (most preferred)
            r'^(\d+)$',                              # Just an integer
            r'SCORE:\s*(\d+(?:\.\d+)?)',             # SCORE: X format
            r'Score:\s*(\d+(?:\.\d+)?)',             # Score: X format
            r'(\d+(?:\.\d+)?)\s*/\s*10',             # X/10 or X.X/10 format
            r'(\d+)/10',                             # X/10 format
            r'Rating:\s*(\d+(?:\.\d+)?)',            # Rating: X format
            r'Relevance:\s*(\d+(?:\.\d+)?)',         # Relevance: X format
            r'(\d+(?:\.\d+)?)\s*out\s*of\s*10',     # X out of 10 format
            r'(\d+(?:\.\d+)?)\s*\/\s*10',           # X / 10 format with spaces
            r'\b(\d+(?:\.\d+)?)\b',                  # Any number in text (last resort)
        ]
        
        for i, pattern in enumerate(patterns):
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                try:
                    score = float(match.group(1))
                    # Clamp score to 0-10 range
                    clamped_score = max(0.0, min(10.0, score))
                    logger.debug(f"Extracted score {clamped_score} using pattern {i+1}: '{pattern}'")
                    return clamped_score
                except ValueError:
                    logger.debug(f"Failed to convert '{match.group(1)}' to float")
                    continue
        
        # Additional fallback: look for words that might indicate scores
        word_scores = {
            'excellent': 9.0, 'perfect': 10.0, 'outstanding': 9.5,
            'very good': 8.0, 'good': 7.0, 'decent': 6.0,
            'average': 5.0, 'mediocre': 4.0, 'poor': 3.0,
            'bad': 2.0, 'terrible': 1.0, 'irrelevant': 0.0,
            'highly relevant': 9.0, 'relevant': 7.0, 'somewhat relevant': 5.0,
            'not relevant': 2.0, 'completely irrelevant': 0.0
        }
        
        response_lower = response_text.lower()
        for phrase, score in word_scores.items():
            if phrase in response_lower:
                logger.debug(f"Extracted score {score} from phrase: '{phrase}'")
                return score
        
        logger.warning(f"Could not extract score from response: '{response_text}'")
        return None
    
    def health_check(self) -> bool:
        """
        Check if the reranker service is healthy.
        
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            if not self._ensure_connection():
                return False
            
            # Test with a simple reranking using new prompt format
            test_prompt = self._create_reranking_prompt("test query about AI programs", "test document content", "test.url")
            score = self._get_relevance_score(test_prompt, max_retries=1)
            return score is not None
            
        except Exception as e:
            logger.error(f"Reranker health check failed: {e}")
            return False
    
    def get_model_info(self) -> dict:
        """
        Get information about the current reranker model.
        
        Returns:
            Dictionary with model information
        """
        return {
            'model': self.model,
            'host': f"{OLLAMA_HOST}:{OLLAMA_PORT}",
            'healthy': self.health_check(),
            'default_limit': RERANKER_LIMIT
        }
    
    def _rerank_chunks(self, query: str, documents: List[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], float]]:
        """
        Rerank individual chunks with AI program specialization and URL-based scoring.
        
        Args:
            query: User's search query
            documents: List of document dictionaries from vector search
            
        Returns:
            List of (document, score) tuples sorted by score
        """
        scored_documents = []
        
        for i, doc in enumerate(documents):
            try:
                # Extract content and URL for reranking
                payload = doc.get('payload', {})
                content = payload.get('content', '')
                url = payload.get('url', '')
                
                if not content:
                    logger.warning(f"Document {i} has no content, skipping reranking")
                    scored_documents.append((doc, 0.0))
                    continue
                
                # Truncate content if too long (to avoid token limits)
                content_truncated = content[:2000] if len(content) > 2000 else content
                
                # Create specialized reranking prompt with URL
                prompt = self._create_reranking_prompt(query, content_truncated, url)
                
                # Get relevance score from reranker
                base_score = self._get_relevance_score(prompt)
                
                # Apply URL-based score boost
                url_boost = self._get_url_based_score_boost(url)
                final_score = base_score * url_boost
                
                # Clamp final score to 0-10 range
                final_score = max(0.0, min(10.0, final_score))
                
                scored_documents.append((doc, final_score))
                
                logger.debug(f"Document {i+1}: base_score={base_score:.2f}, url_boost={url_boost:.2f}, final_score={final_score:.2f}, url='{url}'")
                
            except Exception as e:
                logger.warning(f"Failed to rerank document {i}: {e}")
                # Use original vector similarity score as fallback
                original_score = doc.get('score', 0.0)
                scored_documents.append((doc, original_score))
        
        # Sort by reranker scores (descending)
        scored_documents.sort(key=lambda x: x[1], reverse=True)
        return scored_documents
    
    def _rerank_pages(self, query: str, page_groups: Dict[str, List[Dict[str, Any]]]) -> List[Tuple[Dict[str, Any], float]]:
        """
        Rerank entire pages with AI program specialization and URL-based scoring.
        
        Args:
            query: User's search query
            page_groups: Dictionary mapping page identifiers to lists of chunks
            
        Returns:
            List of (representative_document, combined_score) tuples sorted by score
        """
        scored_pages = []
        
        for page_id, chunks in page_groups.items():
            try:
                if not chunks:
                    logger.warning(f"Page {page_id} has no chunks, skipping reranking")
                    continue
                
                # Combine content from all chunks in the page
                combined_content = "\n\n".join([
                    chunk.get('payload', {}).get('content', '')
                    for chunk in chunks
                    if chunk.get('payload', {}).get('content', '')
                ])
                
                if not combined_content:
                    logger.warning(f"Page {page_id} has no content, skipping reranking")
                    continue
                
                # Get URL from the first chunk (should be same for all chunks in page)
                url = chunks[0].get('payload', {}).get('url', page_id)
                
                # Truncate combined content if too long
                combined_content_truncated = combined_content[:4000] if len(combined_content) > 4000 else combined_content
                
                # Create specialized reranking prompt with URL
                prompt = self._create_reranking_prompt(query, combined_content_truncated, url)
                
                # Get relevance score from reranker
                base_score = self._get_relevance_score(prompt)
                
                # Apply URL-based score boost
                url_boost = self._get_url_based_score_boost(url)
                final_score = base_score * url_boost
                
                # Clamp final score to 0-10 range
                final_score = max(0.0, min(10.0, final_score))
                
                # Use the first chunk as representative document for this page
                representative_doc = chunks[0]
                scored_pages.append((representative_doc, final_score))
                
                logger.debug(f"Page {page_id}: base_score={base_score:.2f}, url_boost={url_boost:.2f}, final_score={final_score:.2f}, chunks={len(chunks)}, url='{url}'")
                
            except Exception as e:
                logger.warning(f"Failed to rerank page {page_id}: {e}")
                # Use average of original vector similarity scores as fallback
                original_scores = [chunk.get('score', 0.0) for chunk in chunks]
                avg_score = sum(original_scores) / len(original_scores) if original_scores else 0.0
                representative_doc = chunks[0] if chunks else {}
                scored_pages.append((representative_doc, avg_score))
        
        # Sort by reranker scores (descending)
        scored_pages.sort(key=lambda x: x[1], reverse=True)
        return scored_pages