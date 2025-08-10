"""
Message processing utilities for the QA bot.
"""

import logging
import re
from typing import List, Set, Tuple

logger = logging.getLogger(__name__)


def split_long_message(text: str, max_length: int = 4000) -> List[str]:
    """
    Split a long message into multiple parts at sentence boundaries.

    Args:
        text: The text to split
        max_length: Maximum length per message part

    Returns:
        List of message parts
    """
    if len(text) <= max_length:
        return [text]

    parts = []
    current_part = ""

    # Split by sentences first
    sentences = re.split(r"(?<=[.!?])\s+", text)

    for sentence in sentences:
        # If adding this sentence would exceed the limit
        if len(current_part) + len(sentence) + 1 > max_length:
            if current_part:
                parts.append(current_part.strip())
                current_part = sentence
            else:
                # Single sentence is too long, split by words
                words = sentence.split()
                temp_part = ""
                for word in words:
                    if len(temp_part) + len(word) + 1 > max_length:
                        if temp_part:
                            parts.append(temp_part.strip())
                            temp_part = word
                        else:
                            # Single word is too long, force split
                            parts.append(word[:max_length])
                            temp_part = word[max_length:]
                    else:
                        temp_part += (" " + word) if temp_part else word
                current_part = temp_part
        else:
            current_part += (" " + sentence) if current_part else sentence

    if current_part:
        parts.append(current_part.strip())

    logger.info(f"Split message of {len(text)} chars into {len(parts)} parts")
    return parts


def format_sources(sources: List[dict], language: str = "en") -> str:
    """
    Format source information for display at the end of messages.
    Shows all sources without deduplication to display both top chunks and complete pages.

    Args:
        sources: List of source dictionaries with 'page_info', 'url', 'score', and 'type' keys
        language: Response language ('en' or 'ru')

    Returns:
        Formatted sources string
    """
    if not sources:
        return ""

    # Format header based on language
    if language == "ru":
        header = "\n\n📚 Источники:"
    else:
        header = "\n\n📚 Sources:"

    source_lines = []
    for i, source in enumerate(sources, 1):
        url = source.get("url", "")
        score = source.get("score", 0)
        source_type = source.get("type", "unknown")

        if url:
            # Format score based on type - rerank scores are typically much higher
            if source_type == "page" and score >= 10.0:
                # This is likely a rerank score
                source_lines.append(f"{i}. {url} (score: {score:.3f})")
            else:
                # This is likely a vector search score
                source_lines.append(f"{i}. {url} (score: {score:.3f})")

    if not source_lines:
        return ""

    result = header + "\n" + "\n".join(source_lines)
    logger.debug(
        f"Formatted {len(sources)} sources (no deduplication) for language: {language}"
    )

    return result


def prepare_messages_with_sources(
    text: str, sources: List[dict], language: str = "en", max_length: int = 4000
) -> List[str]:
    """
    Prepare messages by splitting long text and adding sources to the final message.

    Args:
        text: The main response text
        sources: List of source dictionaries
        language: Response language ('en' or 'ru')
        max_length: Maximum length per message

    Returns:
        List of messages ready to send
    """
    sources_text = format_sources(sources, language)

    # If the text + sources fits in one message, return as single message
    if len(text) + len(sources_text) <= max_length:
        return [text + sources_text]

    # Split the main text
    text_parts = split_long_message(text, max_length)

    # Add sources to the last part if it fits
    if text_parts:
        last_part = text_parts[-1]
        if len(last_part) + len(sources_text) <= max_length:
            text_parts[-1] = last_part + sources_text
        else:
            # Sources don't fit, add as separate message
            text_parts.append(sources_text.strip())

    logger.info(f"Prepared {len(text_parts)} messages with sources")
    return text_parts


def filter_think_blocks(text: str) -> Tuple[str, List[str]]:
    """
    Log <tool_call> blocks separately but return original text unchanged.

    Args:
        text: Text that may contain <tool_call> blocks

    Returns:
        Tuple of (original_text, think_blocks)
    """
    import re

    # Find all <tool_call> blocks
    think_pattern = r"<tool_call>(.*?)</tool_call>"
    think_blocks = re.findall(think_pattern, text, re.DOTALL)

    # Log think blocks if found
    if think_blocks:
        logger.debug("=== THINK BLOCKS FOUND (kept in user response) ===")
        for i, block in enumerate(think_blocks, 1):
            logger.debug(f"Think block {i}: {block.strip()}")
        logger.debug("=== END THINK BLOCKS ===")

    # Return original text unchanged and the think blocks
    return text, think_blocks


def log_full_response(
    filtered_answer: str, sources: List[dict], think_blocks: List[str]
) -> None:
    """
    Log the complete response that will be sent to user.

    Args:
        filtered_answer: The filtered answer text
        sources: List of source dictionaries
        think_blocks: List of think block contents
    """
    logger.info("=== FULL RESPONSE LOGGING ===")
    logger.info(f"Filtered answer ({len(filtered_answer)} chars):")
    logger.info(f"{filtered_answer}")

    if sources:
        logger.info(f"Sources ({len(sources)} items):")
        for i, source in enumerate(sources, 1):
            url = source.get("url", "No URL")
            page_info = source.get("page_info", "No page info")
            logger.info(f"  {i}. {page_info} - {url}")

    if think_blocks:
        logger.info(f"Think blocks ({len(think_blocks)} items):")
        for i, block in enumerate(think_blocks, 1):
            logger.info(f"  Think {i}: {block.strip()}")

    logger.info("=== END FULL RESPONSE LOGGING ===")


def clean_think_sections(text: str) -> str:
    """
    Remove <think>, <reasoning>, <tool_call>, and similar tags from text.

    Args:
        text: Text that may contain think/reasoning sections

    Returns:
        Cleaned text without think/reasoning tags
    """
    if not text:
        return text

    # Remove <think> blocks
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)

    # Remove <reasoning> blocks
    text = re.sub(
        r"<reasoning>.*?</reasoning>", "", text, flags=re.DOTALL | re.IGNORECASE
    )

    # Remove <tool_call> blocks
    text = re.sub(
        r"<tool_call>.*?</tool_call>", "", text, flags=re.DOTALL | re.IGNORECASE
    )

    # Remove other common thinking tags
    text = re.sub(
        r"<analysis>.*?</analysis>", "", text, flags=re.DOTALL | re.IGNORECASE
    )
    text = re.sub(
        r"<planning>.*?</planning>", "", text, flags=re.DOTALL | re.IGNORECASE
    )
    text = re.sub(
        r"<internal>.*?</internal>", "", text, flags=re.DOTALL | re.IGNORECASE
    )

    # Clean up extra whitespace
    text = re.sub(r"\n\s*\n\s*\n", "\n\n", text)  # Multiple newlines to double
    text = text.strip()

    logger.debug(f"Cleaned think sections from text: {len(text)} chars remaining")
    return text


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to maximum length with suffix.

    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to add when truncating

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)] + suffix
