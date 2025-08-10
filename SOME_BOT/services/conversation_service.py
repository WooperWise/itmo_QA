"""
Conversation service for storing and retrieving user conversation history.
"""

import logging
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from utils.logging_utils import log_error_with_context, log_performance

logger = logging.getLogger(__name__)


class ConversationService:
    """Service for managing conversation history with SQLite database."""

    def __init__(self, db_path: str = "conversations.db"):
        """
        Initialize the conversation service.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.connection = None
        self._init_database()

    def _init_database(self) -> None:
        """Initialize SQLite database and create tables if they don't exist."""
        try:
            # Ensure directory exists
            db_dir = Path(self.db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)

            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row  # Enable dict-like access

            # Create conversations table
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    message_type TEXT NOT NULL CHECK (message_type IN ('user', 'bot')),
                    content TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create index for faster queries
            self.connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_user_timestamp 
                ON conversations (user_id, timestamp DESC)
            """
            )

            self.connection.commit()
            logger.info(f"Conversation database initialized at {self.db_path}")

        except Exception as e:
            logger.error(f"Failed to initialize conversation database: {e}")
            log_error_with_context(e, {"db_path": self.db_path})
            self.connection = None

    def _ensure_connection(self) -> bool:
        """Ensure database connection is active."""
        if self.connection is None:
            self._init_database()
        return self.connection is not None

    @log_performance
    def store_message(self, user_id: int, message_type: str, content: str) -> bool:
        """
        Store a message in the conversation history.

        Args:
            user_id: Telegram user ID
            message_type: Type of message ('user' or 'bot')
            content: Message content

        Returns:
            True if stored successfully, False otherwise
        """
        if not self._ensure_connection():
            logger.error("Cannot store message: no database connection")
            return False

        if message_type not in ["user", "bot"]:
            logger.error(f"Invalid message type: {message_type}")
            return False

        try:
            # Clean content before storing
            cleaned_content = self.clean_response(content)
            current_time = time.time()

            cursor = self.connection.execute(
                """
                INSERT INTO conversations (user_id, message_type, content, timestamp)
                VALUES (?, ?, ?, ?)
            """,
                (user_id, message_type, cleaned_content, current_time),
            )

            self.connection.commit()

            logger.debug(
                f"Stored {message_type} message for user {user_id}: {len(cleaned_content)} chars"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to store message for user {user_id}: {e}")
            log_error_with_context(
                e,
                {
                    "user_id": user_id,
                    "message_type": message_type,
                    "content_length": len(content),
                },
            )
            return False

    @log_performance
    def get_recent_conversations(
        self, user_id: int, limit: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get recent conversation exchanges for a user.

        Args:
            user_id: Telegram user ID
            limit: Number of recent exchanges to retrieve (default: 3)

        Returns:
            List of conversation dictionaries with user-bot message pairs
        """
        if not self._ensure_connection():
            logger.error("Cannot get conversations: no database connection")
            return []

        try:
            # Get recent messages ordered by timestamp (newest first)
            cursor = self.connection.execute(
                """
                SELECT message_type, content, timestamp, created_at
                FROM conversations
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """,
                (user_id, limit * 2),
            )  # Get more messages to ensure we have complete exchanges

            messages = cursor.fetchall()

            if not messages:
                logger.debug(f"No conversation history found for user {user_id}")
                return []

            # Group messages into exchanges (user question + bot response pairs)
            exchanges = []
            current_exchange = {}

            for message in reversed(messages):  # Process in chronological order
                msg_dict = {
                    "type": message["message_type"],
                    "content": message["content"],
                    "timestamp": message["timestamp"],
                    "created_at": message["created_at"],
                }

                if message["message_type"] == "user":
                    # Start new exchange
                    if current_exchange:
                        exchanges.append(current_exchange)
                    current_exchange = {"user": msg_dict}
                elif message["message_type"] == "bot" and "user" in current_exchange:
                    # Complete current exchange
                    current_exchange["bot"] = msg_dict
                    exchanges.append(current_exchange)
                    current_exchange = {}

            # Add incomplete exchange if exists
            if current_exchange:
                exchanges.append(current_exchange)

            # Return most recent exchanges (up to limit)
            recent_exchanges = (
                exchanges[-limit:] if len(exchanges) > limit else exchanges
            )

            logger.info(
                f"Retrieved {len(recent_exchanges)} recent exchanges for user {user_id}"
            )
            return recent_exchanges

        except Exception as e:
            logger.error(f"Failed to get conversations for user {user_id}: {e}")
            log_error_with_context(e, {"user_id": user_id, "limit": limit})
            return []

    def clean_response(self, text: str) -> str:
        """
        Clean response text by removing <think>, <reasoning>, and similar tags.

        Args:
            text: Text to clean

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

        return text

    @log_performance
    def get_conversation_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Get conversation statistics for a user.

        Args:
            user_id: Telegram user ID

        Returns:
            Dictionary with conversation statistics
        """
        if not self._ensure_connection():
            return {}

        try:
            cursor = self.connection.execute(
                """
                SELECT 
                    COUNT(*) as total_messages,
                    COUNT(CASE WHEN message_type = 'user' THEN 1 END) as user_messages,
                    COUNT(CASE WHEN message_type = 'bot' THEN 1 END) as bot_messages,
                    MIN(timestamp) as first_message_time,
                    MAX(timestamp) as last_message_time
                FROM conversations
                WHERE user_id = ?
            """,
                (user_id,),
            )

            stats = cursor.fetchone()

            if stats and stats["total_messages"] > 0:
                return {
                    "total_messages": stats["total_messages"],
                    "user_messages": stats["user_messages"],
                    "bot_messages": stats["bot_messages"],
                    "first_message_time": stats["first_message_time"],
                    "last_message_time": stats["last_message_time"],
                    "conversation_span_hours": (
                        (stats["last_message_time"] - stats["first_message_time"])
                        / 3600
                        if stats["first_message_time"]
                        else 0
                    ),
                }
            else:
                return {
                    "total_messages": 0,
                    "user_messages": 0,
                    "bot_messages": 0,
                    "first_message_time": None,
                    "last_message_time": None,
                    "conversation_span_hours": 0,
                }

        except Exception as e:
            logger.error(f"Failed to get conversation stats for user {user_id}: {e}")
            return {}

    def cleanup_old_conversations(self, days_to_keep: int = 30) -> int:
        """
        Clean up old conversations to manage database size.

        Args:
            days_to_keep: Number of days of conversations to keep

        Returns:
            Number of deleted records
        """
        if not self._ensure_connection():
            return 0

        try:
            cutoff_time = time.time() - (days_to_keep * 24 * 3600)

            cursor = self.connection.execute(
                """
                DELETE FROM conversations
                WHERE timestamp < ?
            """,
                (cutoff_time,),
            )

            deleted_count = cursor.rowcount
            self.connection.commit()

            logger.info(
                f"Cleaned up {deleted_count} old conversation records (older than {days_to_keep} days)"
            )
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup old conversations: {e}")
            return 0

    def health_check(self) -> bool:
        """
        Check if the conversation service is healthy.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            if not self._ensure_connection():
                return False

            # Test database connection with a simple query
            cursor = self.connection.execute(
                "SELECT COUNT(*) FROM conversations LIMIT 1"
            )
            cursor.fetchone()

            return True

        except Exception as e:
            logger.error(f"Conversation service health check failed: {e}")
            return False

    def get_service_info(self) -> Dict[str, Any]:
        """
        Get information about the conversation service.

        Returns:
            Dictionary with service information
        """
        try:
            if not self._ensure_connection():
                return {
                    "db_path": self.db_path,
                    "connected": False,
                    "total_conversations": 0,
                    "unique_users": 0,
                    "healthy": False,
                }

            # Get total conversations count
            cursor = self.connection.execute(
                "SELECT COUNT(*) as total FROM conversations"
            )
            total_conversations = cursor.fetchone()["total"]

            # Get unique users count
            cursor = self.connection.execute(
                "SELECT COUNT(DISTINCT user_id) as unique_users FROM conversations"
            )
            unique_users = cursor.fetchone()["unique_users"]

            return {
                "db_path": self.db_path,
                "connected": True,
                "total_conversations": total_conversations,
                "unique_users": unique_users,
                "healthy": self.health_check(),
            }

        except Exception as e:
            logger.error(f"Failed to get conversation service info: {e}")
            return {
                "db_path": self.db_path,
                "connected": False,
                "total_conversations": 0,
                "unique_users": 0,
                "healthy": False,
            }

    def close(self) -> None:
        """Close database connection."""
        if self.connection:
            try:
                self.connection.close()
                self.connection = None
                logger.info("Conversation database connection closed")
            except Exception as e:
                logger.error(f"Error closing conversation database: {e}")

    def __del__(self):
        """Cleanup when object is destroyed."""
        self.close()
