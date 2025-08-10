"""
Logging utilities for the QA bot.
"""

import logging
import time
from functools import wraps
from typing import Any, Dict, List


def setup_logging(level: str = "INFO") -> None:
    """
    Setup logging configuration for the bot.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()],
    )


def log_performance(func):
    """
    Decorator to log function performance metrics.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        logger = logging.getLogger(func.__module__)

        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(f"{func.__name__} completed in {duration:.2f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"{func.__name__} failed after {duration:.2f}s: {e}")
            raise

    return wrapper


def log_vector_search_results(results: List[Dict[str, Any]], query: str) -> None:
    """
    Log vector search results with detailed information.

    Args:
        results: List of search results from Qdrant
        query: Original search query
    """
    logger = logging.getLogger(__name__)

    if not results:
        logger.warning(
            f"Vector search returned no results for query: '{query[:100]}...'"
        )
        return

    # Log summary
    scores = [result.get("score", 0) for result in results]
    max_score = max(scores) if scores else 0
    min_score = min(scores) if scores else 0
    avg_score = sum(scores) / len(scores) if scores else 0

    logger.info(
        f"Vector search: {len(results)} results for query '{query[:50]}...', "
        f"scores: max={max_score:.3f}, min={min_score:.3f}, avg={avg_score:.3f}"
    )

    # Log ALL results with scores and URLs
    logger.info(f"=== ALL {len(results)} VECTOR SEARCH RESULTS ===")
    for i, result in enumerate(results):
        score = result.get("score", 0)
        url = result.get("payload", {}).get("url", "No URL")
        page_info = result.get("payload", {}).get("page_info", "No page info")

        logger.info(f"Vector #{i+1}: score={score:.3f}, {page_info}, {url}")
    logger.info(f"=== END VECTOR SEARCH RESULTS ===")

    # Also log grouped by page information
    page_chunks = {}
    for result in results:
        url = result.get("payload", {}).get("url", "No URL")
        if url not in page_chunks:
            page_chunks[url] = 0
        page_chunks[url] += 1

    logger.info(f"Grouped into {len(page_chunks)} pages:")
    for url, chunk_count in list(page_chunks.items())[:20]:  # Show top 20 pages
        logger.info(f"  {url}: {chunk_count} chunks")
    if len(page_chunks) > 20:
        logger.info(f"  ... and {len(page_chunks) - 20} more pages")


def log_reranker_results(
    original_results: List[Dict[str, Any]],
    reranked_results: List[Dict[str, Any]],
    query: str,
    duration: float,
    page_groups: Dict[str, List[Dict[str, Any]]] = None,
) -> None:
    """
    Log reranker results with performance metrics.

    Args:
        original_results: Original search results before reranking
        reranked_results: Results after reranking
        query: Original search query
        duration: Time taken for reranking
        page_groups: Optional page groups for page-level reranking
    """
    logger = logging.getLogger(__name__)

    if page_groups:
        logger.info(
            f"Reranker: selected {len(reranked_results)} from {len(page_groups)} "
            f"pages in {duration:.2f}s for query '{query[:50]}...'"
        )
        logger.info("=== PAGE-LEVEL RERANKER RESULTS ===")

        # Create a mapping of URL to original position for comparison
        original_url_positions = {}
        for i, result in enumerate(original_results):
            url = result.get("payload", {}).get("url", f"no_url_{i}")
            if url not in original_url_positions:
                original_url_positions[url] = i + 1

        for i, result in enumerate(reranked_results):
            score = result.get("rerank_score", result.get("score", 0))
            original_score = result.get("original_score", result.get("score", 0))
            url = result.get("payload", {}).get("url", "No URL")
            page_info = result.get("payload", {}).get("page_info", "No page info")
            chunks_in_page = len(page_groups.get(url, [])) if url in page_groups else 1
            original_position = original_url_positions.get(url, "Unknown")

            logger.info(
                f"Reranked #{i+1}: rerank_score={score:.3f} (orig={original_score:.3f}), "
                f"original_pos={original_position}, {chunks_in_page} chunks, {page_info}, {url}"
            )
    else:
        logger.info(
            f"Reranker: selected {len(reranked_results)} from {len(original_results)} "
            f"results in {duration:.2f}s for query '{query[:50]}...'"
        )
        logger.info("=== CHUNK-LEVEL RERANKER RESULTS ===")
        # Log reranked results with their new scores/positions
        for i, result in enumerate(reranked_results):
            score = result.get("rerank_score", result.get("score", 0))
            original_score = result.get("original_score", result.get("score", 0))
            url = result.get("payload", {}).get("url", "No URL")
            page_info = result.get("payload", {}).get("page_info", "No page info")

            logger.info(
                f"Reranked #{i+1}: rerank_score={score:.3f} (orig={original_score:.3f}), "
                f"{page_info}, {url}"
            )

    logger.info("=== END RERANKER RESULTS ===")


def log_generation_metrics(
    response: str, context_length: int, duration: float, language: str
) -> None:
    """
    Log LLM generation metrics.

    Args:
        response: Generated response text
        context_length: Length of context provided to LLM
        duration: Time taken for generation
        language: Response language
    """
    logger = logging.getLogger(__name__)

    response_length = len(response)
    words_count = len(response.split())

    logger.info(
        f"Generated {response_length} chars ({words_count} words) "
        f"from {context_length} chars context in {duration:.2f}s, "
        f"language: {language}"
    )

    # Log response preview
    preview = response[:200].replace("\n", " ")
    logger.debug(f"Response preview: '{preview}...'")


def log_user_interaction(
    user_id: int, username: str, query: str, response_parts: int, total_duration: float
) -> None:
    """
    Log user interaction summary.

    Args:
        user_id: Telegram user ID
        username: Telegram username
        query: User's query
        response_parts: Number of message parts sent
        total_duration: Total processing time
    """
    logger = logging.getLogger(__name__)

    logger.info(
        f"User interaction: {username} (ID: {user_id}) asked '{query[:100]}...', "
        f"responded with {response_parts} messages in {total_duration:.2f}s"
    )


def log_error_with_context(
    error: Exception, context: Dict[str, Any], user_id: int = None
) -> None:
    """
    Log error with additional context information.

    Args:
        error: The exception that occurred
        context: Additional context information
        user_id: User ID if applicable
    """
    logger = logging.getLogger(__name__)

    context_str = ", ".join([f"{k}={v}" for k, v in context.items()])
    user_info = f" (User: {user_id})" if user_id else ""

    logger.error(
        f"Error: {type(error).__name__}: {error}{user_info}, Context: {context_str}"
    )
