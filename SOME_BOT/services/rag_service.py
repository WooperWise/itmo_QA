"""
RAG (Retrieval-Augmented Generation) service that orchestrates the complete pipeline.
"""

import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from constants import (
    MAX_CONTEXT_CHARS,
    QDRANT_COLLECTION_NAME,
    QDRANT_HOST,
    QDRANT_PORT,
    RERANKER_LIMIT,
    TOP_CHUNKS_FOR_CONTEXT,
    TOP_COMPLETE_PAGES,
    TOP_EMBEDDER_RESULTS,
    TOP_RERANKER_RESULTS,
    VECTOR_SEARCH_LIMIT,
)
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue
from services.conversation_service import ConversationService
from services.embedding_service import EmbeddingService
from services.llm_service import LLMService
from services.reranker_service import RerankerService
from utils.logging_utils import (
    log_error_with_context,
    log_performance,
    log_user_interaction,
    log_vector_search_results,
)

logger = logging.getLogger(__name__)


class RAGService:
    """Complete RAG service for question answering."""

    def __init__(self):
        """Initialize the RAG service with all components."""
        self.qdrant_client = None
        self.embedding_service = EmbeddingService()
        self.reranker_service = RerankerService()
        self.llm_service = LLMService()
        # Get database path from environment
        database_path = os.getenv("DATABASE_PATH", "conversations.db")
        self.conversation_service = ConversationService(database_path)
        self.educational_programs_data = None

        # Target AI programs keywords for prioritization
        self.target_programs_keywords = {
            "ru": [
                "искусственный интеллект",
                "ии",
                "машинное обучение",
                "нейросети",
                "управление ии-продуктами",
                "ии-продукты",
                "продуктовый менеджмент",
                "artificial intelligence",
                "ai product management",
                "ai products",
            ],
            "en": [
                "artificial intelligence",
                "ai",
                "machine learning",
                "neural networks",
                "ai product management",
                "ai products",
                "product management",
                "искусственный интеллект",
                "управление ии-продуктами",
                "ии-продукты",
            ],
        }

        self._connect_qdrant()
        self._load_educational_programs()

    def _connect_qdrant(self) -> None:
        """Connect to Qdrant vector database."""
        try:
            self.qdrant_client = QdrantClient(
                host=QDRANT_HOST,
                port=QDRANT_PORT,
                prefer_grpc=False,  # Use HTTP to avoid version issues
            )

            # Test connection
            collections = self.qdrant_client.get_collections()
            logger.info(f"Connected to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}")
            logger.info(
                f"Available collections: {[c.name for c in collections.collections]}"
            )

        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            self.qdrant_client = None

    def _load_educational_programs(self) -> None:
        """Load educational programs data from cool_diff.md file."""
        try:
            educational_file_path = Path("cool_diff.md")
            if not educational_file_path.exists():
                logger.warning(
                    f"Educational programs file not found: {educational_file_path}"
                )
                self.educational_programs_data = ""
                return

            with open(educational_file_path, "r", encoding="utf-8") as f:
                self.educational_programs_data = f.read()

            logger.info(
                f"Loaded educational programs data: {len(self.educational_programs_data)} characters"
            )

        except Exception as e:
            logger.error(f"Failed to load educational programs data: {e}")
            log_error_with_context(
                e,
                {
                    "file_path": (
                        str(educational_file_path)
                        if "educational_file_path" in locals()
                        else "unknown"
                    )
                },
            )
            self.educational_programs_data = ""

    def _group_chunks_by_page(
        self, chunks: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group chunks by their page identifier (URL or page_info).

        Args:
            chunks: List of chunk dictionaries from vector search

        Returns:
            Dictionary mapping page identifiers to lists of chunks
        """
        grouped = {}

        for chunk in chunks:
            payload = chunk.get("payload", {})
            # Use URL as primary identifier, fallback to page_info
            page_id = payload.get("url") or payload.get("page_info", "unknown")

            if page_id not in grouped:
                grouped[page_id] = []
            grouped[page_id].append(chunk)

        return grouped

    @log_performance
    def fetch_all_chunks_for_page(self, page_identifier: str) -> List[Dict[str, Any]]:
        """
        Fetch all chunks for a given page from Qdrant database.

        Args:
            page_identifier: URL or page_info to search for

        Returns:
            List of all chunks belonging to the page, ordered by chunk_index
        """
        if not self._ensure_qdrant_connection():
            logger.error("Cannot fetch page chunks: no Qdrant connection")
            return []

        try:
            # Search for all chunks with matching URL or page_info
            # We'll use scroll to get all results without limit
            scroll_result = self.qdrant_client.scroll(
                collection_name=QDRANT_COLLECTION_NAME,
                scroll_filter=Filter(
                    should=[
                        FieldCondition(
                            key="url", match=MatchValue(value=page_identifier)
                        ),
                        FieldCondition(
                            key="page_info", match=MatchValue(value=page_identifier)
                        ),
                    ]
                ),
                limit=1000,  # Large limit to get all chunks
                with_payload=True,
                with_vectors=False,
            )

            chunks = []
            for point in scroll_result[
                0
            ]:  # scroll_result is (points, next_page_offset)
                chunks.append(
                    {
                        "id": point.id,
                        "payload": point.payload,
                        "score": 1.0,  # Default score since this isn't from vector search
                    }
                )

            # Sort by chunk_index to maintain page order
            chunks.sort(key=lambda x: x.get("payload", {}).get("chunk_index", 0))

            logger.info(f"Fetched {len(chunks)} chunks for page: {page_identifier}")
            return chunks

        except Exception as e:
            log_error_with_context(
                e,
                {
                    "page_identifier": page_identifier,
                    "collection": QDRANT_COLLECTION_NAME,
                },
            )
            return []

    def reconstruct_complete_pages(
        self, page_identifiers: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Reconstruct complete pages by fetching all chunks for each page.

        Args:
            page_identifiers: List of page URLs or page_info values

        Returns:
            Dictionary mapping page_identifier to reconstructed page data
        """
        reconstructed_pages = {}

        for page_id in page_identifiers:
            try:
                # Fetch all chunks for this page
                page_chunks = self.fetch_all_chunks_for_page(page_id)

                if not page_chunks:
                    logger.warning(f"No chunks found for page: {page_id}")
                    continue

                # Combine all chunk content in order
                combined_content = "\n\n".join(
                    [
                        chunk.get("payload", {}).get("content", "")
                        for chunk in page_chunks
                        if chunk.get("payload", {}).get("content", "")
                    ]
                )

                # Use metadata from the first chunk
                first_chunk = page_chunks[0]
                payload = first_chunk.get("payload", {})

                reconstructed_pages[page_id] = {
                    "page_identifier": page_id,
                    "content": combined_content,
                    "chunk_count": len(page_chunks),
                    "payload": {
                        "url": payload.get("url", ""),
                        "page_info": payload.get("page_info", ""),
                        "filename": payload.get("filename", ""),
                        "content": combined_content,
                        "content_preview": (
                            combined_content[:500] if combined_content else ""
                        ),
                    },
                    "chunks": page_chunks,  # Keep reference to original chunks
                }

                logger.debug(
                    f"Reconstructed page {page_id}: {len(combined_content)} chars from {len(page_chunks)} chunks"
                )

            except Exception as e:
                logger.error(f"Failed to reconstruct page {page_id}: {e}")
                continue

        logger.info(
            f"Successfully reconstructed {len(reconstructed_pages)} complete pages"
        )
        return reconstructed_pages

    def _enhance_query_for_ai_programs(self, query: str, language: str = "en") -> str:
        """
        Enhance query with AI program-specific keywords to improve search relevance.

        Args:
            query: Original user query
            language: Query language

        Returns:
            Enhanced query with AI program keywords
        """
        enhanced_query = query.lower()

        # Check if query already contains target program keywords
        keywords = self.target_programs_keywords.get(
            language, self.target_programs_keywords["en"]
        )
        has_ai_keywords = any(keyword in enhanced_query for keyword in keywords)

        if not has_ai_keywords:
            # Add AI context to generic queries
            if language == "ru":
                enhanced_query += (
                    " искусственный интеллект ИИ-продукты ИТМО магистратура"
                )
            else:
                enhanced_query += (
                    " artificial intelligence AI products ITMO master's program"
                )

        logger.debug(f"Enhanced query from '{query}' to '{enhanced_query}'")
        return enhanced_query

    def _prioritize_ai_program_results(
        self, results: List[Dict[str, Any]], query: str, language: str = "en"
    ) -> List[Dict[str, Any]]:
        """
        Prioritize search results that are related to target AI programs.

        Args:
            results: Original search results
            query: User query
            language: Query language

        Returns:
            Reordered results with AI program content prioritized
        """
        if not results:
            return results

        keywords = self.target_programs_keywords.get(
            language, self.target_programs_keywords["en"]
        )

        ai_program_results = []
        other_results = []

        for result in results:
            payload = result.get("payload", {})
            content = payload.get("content", "").lower()
            page_info = payload.get("page_info", "").lower()
            url = payload.get("url", "").lower()

            # Check if result contains AI program keywords
            is_ai_program_related = any(
                keyword in content or keyword in page_info or keyword in url
                for keyword in keywords
            )

            if is_ai_program_related:
                # Boost score for AI program related content
                result["score"] = result.get("score", 0) * 1.2
                ai_program_results.append(result)
            else:
                other_results.append(result)

        # Combine results with AI program content first
        prioritized_results = ai_program_results + other_results

        logger.info(
            f"Prioritized {len(ai_program_results)} AI program results out of {len(results)} total"
        )
        return prioritized_results

    def _ensure_qdrant_connection(self) -> bool:
        """Ensure connection to Qdrant."""
        if self.qdrant_client is None:
            self._connect_qdrant()
        return self.qdrant_client is not None

    @log_performance
    def vector_search(
        self, query_embedding: List[float], limit: int = None
    ) -> List[Dict[str, Any]]:
        """
        Perform vector search in Qdrant.

        Args:
            query_embedding: Query embedding vector
            limit: Maximum number of results (default: VECTOR_SEARCH_LIMIT)

        Returns:
            List of search results with scores and payloads
        """
        if not self._ensure_qdrant_connection():
            logger.error("Cannot perform vector search: no Qdrant connection")
            return []

        limit = limit or VECTOR_SEARCH_LIMIT

        try:
            start_time = time.time()

            search_results = self.qdrant_client.search(
                collection_name=QDRANT_COLLECTION_NAME,
                query_vector=query_embedding,
                limit=limit,
                with_payload=True,
                with_vectors=False,  # Don't return vectors to save bandwidth
            )

            duration = time.time() - start_time

            # Convert to dictionaries for easier handling
            results = []
            for result in search_results:
                results.append(
                    {"id": result.id, "score": result.score, "payload": result.payload}
                )

            logger.info(
                f"Vector search completed: {len(results)} results in {duration:.2f}s"
            )

            return results

        except Exception as e:
            log_error_with_context(
                e,
                {
                    "collection": QDRANT_COLLECTION_NAME,
                    "embedding_size": len(query_embedding),
                    "limit": limit,
                },
            )
            return []

    @log_performance
    def answer_question(
        self, query: str, language: str = "en", user_id: int = None
    ) -> Tuple[Optional[str], List[Dict[str, Any]]]:
        """
        Answer a question using the enhanced three-phase RAG pipeline with educational programs and conversation context.

        Args:
            query: User's question
            language: Response language ('en' or 'ru')
            user_id: User ID for logging and conversation context

        Returns:
            Tuple of (answer, source_documents) or (None, []) if failed
        """
        start_time = time.time()

        try:
            logger.info(
                f"Processing question: '{query[:100]}...' in {language} for user {user_id}"
            )

            # Step 1: Get conversation context if user_id is provided
            conversation_context = []
            if user_id:
                logger.debug("Step 1a: Retrieving conversation context")
                try:
                    conversation_context = (
                        self.conversation_service.get_recent_conversations(
                            user_id, limit=3
                        )
                    )
                    logger.info(
                        f"Retrieved {len(conversation_context)} recent conversation exchanges"
                    )
                except Exception as e:
                    logger.warning(f"Failed to retrieve conversation context: {e}")
                    conversation_context = []

            # Step 2: Enhance query for AI programs
            logger.debug("Step 2: Enhancing query for AI program specialization")
            enhanced_query = self._enhance_query_for_ai_programs(query, language)

            # Step 3: Generate query embedding (using enhanced query)
            logger.debug("Step 3: Generating query embedding")
            query_embedding = self.embedding_service.generate_embedding(enhanced_query)
            if not query_embedding:
                logger.error("Failed to generate query embedding")
                return None, []

            # Step 4: Vector search
            logger.debug("Step 4: Performing vector search")
            search_results = self.vector_search(query_embedding, VECTOR_SEARCH_LIMIT)
            if not search_results:
                logger.warning("No results from vector search")
                return None, []

            # Step 5: Prioritize AI program results
            logger.debug("Step 5: Prioritizing AI program results")
            search_results = self._prioritize_ai_program_results(
                search_results, query, language
            )

            # Log vector search results
            log_vector_search_results(search_results, enhanced_query)

            # Step 6: Extract top chunks for Block 3
            logger.debug(
                f"Step 6: Extracting top {TOP_CHUNKS_FOR_CONTEXT} chunks for context block 3"
            )
            top_chunks = search_results[:TOP_CHUNKS_FOR_CONTEXT]
            logger.info(f"Selected {len(top_chunks)} top chunks for Block 3")

            # Step 7: Identify unique pages from all search results
            logger.debug("Step 7: Identifying unique pages for reconstruction")
            unique_pages = set()
            for chunk in search_results:
                payload = chunk.get("payload", {})
                page_id = payload.get("url") or payload.get("page_info", "unknown")
                if page_id != "unknown":
                    unique_pages.add(page_id)

            unique_pages = list(unique_pages)
            logger.info(
                f"Identified {len(unique_pages)} unique pages for reconstruction"
            )

            # Step 8: Reconstruct complete pages
            logger.debug("Step 8: Reconstructing complete pages")
            reconstructed_pages = self.reconstruct_complete_pages(unique_pages)

            if not reconstructed_pages:
                logger.warning("No pages could be reconstructed")
                return None, []

            # Step 9: Rerank complete pages
            logger.debug("Step 9: Reranking complete pages")
            # Convert reconstructed pages to format expected by reranker
            page_docs_for_reranking = []
            for page_id, page_data in reconstructed_pages.items():
                page_docs_for_reranking.append(
                    {
                        "id": f"page_{page_id}",
                        "payload": page_data["payload"],
                        "score": 1.0,  # Default score
                    }
                )

            reranked_pages = self.reranker_service.rerank_documents(
                query, page_docs_for_reranking, TOP_COMPLETE_PAGES
            )

            if not reranked_pages:
                logger.warning("No pages after reranking")
                return None, []

            logger.info(
                f"Selected {len(reranked_pages)} complete pages after reranking"
            )

            # Step 10: Generate answer with three-phase context assembly
            logger.debug("Step 10: Generating answer with three-phase context assembly")
            answer = self.llm_service.generate_answer_two_phase(
                query,
                top_chunks,
                reranked_pages,
                language,
                max_context_chars=MAX_CONTEXT_CHARS,
                conversation_context=conversation_context,
                educational_programs_data=self.educational_programs_data,
            )

            if not answer:
                logger.warning("Failed to generate answer")
                return None, []

            # Extract source information for attribution
            sources = []

            # Add educational programs as a source if data exists
            if self.educational_programs_data:
                sources.append(
                    {
                        "page_info": "Образовательные программы ИТМО по ИИ",
                        "url": "",
                        "score": 1.0,
                        "type": "educational_programs",
                    }
                )

            # Add sources from top chunks
            for doc in top_chunks:
                payload = doc.get("payload", {})
                if payload.get("url") or payload.get("page_info"):
                    sources.append(
                        {
                            "page_info": payload.get("page_info", "Unknown"),
                            "url": payload.get("url", ""),
                            "score": doc.get("score", 0),
                            "type": "chunk",
                        }
                    )

            # Add sources from reranked pages
            for doc in reranked_pages:
                payload = doc.get("payload", {})
                if payload.get("url") or payload.get("page_info"):
                    sources.append(
                        {
                            "page_info": payload.get("page_info", "Unknown"),
                            "url": payload.get("url", ""),
                            "score": doc.get("rerank_score", doc.get("score", 0)),
                            "type": "page",
                        }
                    )

            duration = time.time() - start_time

            # Log user interaction
            if user_id:
                log_user_interaction(user_id, "unknown", query, 1, duration)

            logger.info(
                f"Question answered successfully in {duration:.2f}s using three-phase approach"
            )

            return answer, sources

        except Exception as e:
            duration = time.time() - start_time
            log_error_with_context(
                e,
                {
                    "query_length": len(query),
                    "language": language,
                    "duration": duration,
                },
                user_id,
            )
            return None, []

    def health_check(self) -> Dict[str, Any]:
        """
        Check health of all RAG components.

        Returns:
            Dictionary with health status of each component
        """
        health_status = {
            "qdrant": False,
            "embedding": False,
            "reranker": False,
            "llm": False,
            "conversation": False,
            "educational_programs": False,
            "overall": False,
        }

        try:
            # Check Qdrant
            if self._ensure_qdrant_connection():
                collections = self.qdrant_client.get_collections()
                health_status["qdrant"] = QDRANT_COLLECTION_NAME in [
                    c.name for c in collections.collections
                ]

            # Check services
            health_status["embedding"] = self.embedding_service.health_check()
            health_status["reranker"] = self.reranker_service.health_check()
            health_status["llm"] = self.llm_service.health_check()
            health_status["conversation"] = self.conversation_service.health_check()

            # Check educational programs data
            health_status["educational_programs"] = bool(self.educational_programs_data)

            # Overall health
            health_status["overall"] = all(
                [
                    health_status["qdrant"],
                    health_status["embedding"],
                    health_status["reranker"],
                    health_status["llm"],
                    health_status["conversation"],
                    health_status["educational_programs"],
                ]
            )

        except Exception as e:
            logger.error(f"Health check failed: {e}")

        logger.info(f"RAG health check: {health_status}")
        return health_status

    def get_system_info(self) -> Dict[str, Any]:
        """
        Get comprehensive system information.

        Returns:
            Dictionary with system information
        """
        return {
            "qdrant": {
                "host": f"{QDRANT_HOST}:{QDRANT_PORT}",
                "collection": QDRANT_COLLECTION_NAME,
                "connected": self._ensure_qdrant_connection(),
            },
            "embedding": self.embedding_service.get_model_info(),
            "reranker": self.reranker_service.get_model_info(),
            "llm": self.llm_service.get_model_info(),
            "config": {
                "vector_search_limit": VECTOR_SEARCH_LIMIT,
                "reranker_limit": RERANKER_LIMIT,
            },
            "health": self.health_check(),
        }

    def search_documents(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search documents without generating an answer (for debugging).

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of search results
        """
        query_embedding = self.embedding_service.generate_embedding(query)
        if not query_embedding:
            return []

        search_results = self.vector_search(query_embedding, limit)
        return search_results
