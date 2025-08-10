"""
Language detection utilities for the QA bot.
"""

import logging

logger = logging.getLogger(__name__)


def is_russian(text: str) -> bool:
    """
    Detect if text is primarily in Russian by checking for Cyrillic characters.

    Args:
        text: Input text to analyze

    Returns:
        True if text appears to be Russian (>30% Cyrillic characters)
    """
    if not text or not text.strip():
        return False

    # Remove whitespace and punctuation for more accurate detection
    text_clean = "".join(c for c in text if c.isalpha())

    if not text_clean:
        return False

    # Count Cyrillic characters (Russian alphabet range)
    cyrillic_chars = sum(1 for c in text_clean if "\u0400" <= c <= "\u04ff")

    # Consider text Russian if >30% of alphabetic characters are Cyrillic
    ratio = cyrillic_chars / len(text_clean)

    logger.debug(
        f"Language detection: {cyrillic_chars}/{len(text_clean)} Cyrillic chars, ratio: {ratio:.2f}"
    )

    return ratio > 0.3


def get_response_language(user_text: str) -> str:
    """
    Determine the appropriate response language based on user input.

    Args:
        user_text: User's message text

    Returns:
        'ru' for Russian, 'en' for English
    """
    if is_russian(user_text):
        logger.info("Detected Russian input, will respond in Russian")
        return "ru"
    else:
        logger.info("Detected English input, will respond in English")
        return "en"
