#!/usr/bin/env python3
"""
Full integration test for the educational consultant bot.
Tests all components working together including database persistence.
"""

import asyncio
import logging
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FullIntegrationTest:
    """Comprehensive integration test for the bot system."""

    def __init__(self):
        """Initialize the test environment."""
        self.test_db_path = None
        self.temp_dir = None
        self.original_db_path = None

    def setup_test_environment(self):
        """Set up isolated test environment."""
        logger.info("Setting up test environment...")

        # Create temporary directory for test database
        self.temp_dir = tempfile.mkdtemp(prefix="bot_test_")
        self.test_db_path = os.path.join(self.temp_dir, "test_conversations.db")

        # Store original DATABASE_PATH
        self.original_db_path = os.getenv("DATABASE_PATH")

        # Set test database path
        os.environ["DATABASE_PATH"] = self.test_db_path

        logger.info(f"Test environment created: {self.temp_dir}")
        logger.info(f"Test database path: {self.test_db_path}")

    def cleanup_test_environment(self):
        """Clean up test environment."""
        logger.info("Cleaning up test environment...")

        # Restore original DATABASE_PATH
        if self.original_db_path:
            os.environ["DATABASE_PATH"] = self.original_db_path
        elif "DATABASE_PATH" in os.environ:
            del os.environ["DATABASE_PATH"]

        # Remove temporary directory
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            logger.info(f"Removed test directory: {self.temp_dir}")

    def test_database_initialization(self):
        """Test database initialization script."""
        logger.info("Testing database initialization...")

        try:
            from init_db import DatabaseInitializer

            # Initialize database
            initializer = DatabaseInitializer(self.test_db_path)
            success = initializer.initialize()

            if not success:
                raise Exception("Database initialization failed")

            # Verify database exists and has correct structure
            if not os.path.exists(self.test_db_path):
                raise Exception("Database file was not created")

            # Get database info
            db_info = initializer.get_database_info()

            if not db_info["exists"]:
                raise Exception("Database info indicates database doesn't exist")

            if "conversations" not in db_info["tables"]:
                raise Exception("Conversations table not found")

            if "schema_version" not in db_info["tables"]:
                raise Exception("Schema version table not found")

            logger.info("✓ Database initialization test passed")
            return True

        except Exception as e:
            logger.error(f"✗ Database initialization test failed: {e}")
            return False

    def test_database_migration(self):
        """Test database migration script."""
        logger.info("Testing database migration...")

        try:
            from migrate_db import DatabaseMigrator

            # Test migration
            migrator = DatabaseMigrator(self.test_db_path)
            migration_info = migrator.get_migration_info()

            logger.info(f"Migration info: {migration_info}")

            if migration_info["needs_migration"]:
                success = migrator.migrate()
                if not success:
                    raise Exception("Database migration failed")

            # Verify migration
            if not migrator.verify_migration():
                raise Exception("Migration verification failed")

            logger.info("✓ Database migration test passed")
            return True

        except Exception as e:
            logger.error(f"✗ Database migration test failed: {e}")
            return False

    def test_conversation_service(self):
        """Test conversation service functionality."""
        logger.info("Testing conversation service...")

        try:
            from services.conversation_service import ConversationService

            # Initialize service
            service = ConversationService(self.test_db_path)

            # Test health check
            if not service.health_check():
                raise Exception("Conversation service health check failed")

            # Test storing messages
            test_user_id = 12345

            # Store user message
            success = service.store_message(
                test_user_id, "user", "Test question about ITMO programs"
            )
            if not success:
                raise Exception("Failed to store user message")

            # Store bot response
            success = service.store_message(
                test_user_id, "bot", "Test response about educational programs"
            )
            if not success:
                raise Exception("Failed to store bot message")

            # Test retrieving conversations
            conversations = service.get_recent_conversations(test_user_id, limit=1)
            if not conversations:
                raise Exception("No conversations retrieved")

            if len(conversations) != 1:
                raise Exception(f"Expected 1 conversation, got {len(conversations)}")

            conversation = conversations[0]
            if "user" not in conversation or "bot" not in conversation:
                raise Exception("Conversation missing user or bot message")

            # Test conversation stats
            stats = service.get_conversation_stats(test_user_id)
            if stats["total_messages"] != 2:
                raise Exception(f"Expected 2 messages, got {stats['total_messages']}")

            # Test service info
            info = service.get_service_info()
            if not info["healthy"]:
                raise Exception("Service info indicates unhealthy state")

            logger.info("✓ Conversation service test passed")
            return True

        except Exception as e:
            logger.error(f"✗ Conversation service test failed: {e}")
            return False

    def test_rag_service_initialization(self):
        """Test RAG service initialization with database path."""
        logger.info("Testing RAG service initialization...")

        try:
            # Mock external dependencies
            with patch("services.rag_service.QdrantClient") as mock_qdrant, patch(
                "services.rag_service.EmbeddingService"
            ) as mock_embedding, patch(
                "services.rag_service.RerankerService"
            ) as mock_reranker, patch(
                "services.rag_service.LLMService"
            ) as mock_llm:

                # Configure mocks
                mock_qdrant.return_value.get_collections.return_value.collections = []

                from services.rag_service import RAGService

                # Initialize RAG service
                rag_service = RAGService()

                # Verify conversation service was initialized with correct path
                if not hasattr(rag_service, "conversation_service"):
                    raise Exception("RAG service missing conversation service")

                if rag_service.conversation_service.db_path != self.test_db_path:
                    raise Exception(
                        f"RAG service using wrong database path: {rag_service.conversation_service.db_path}"
                    )

                logger.info("✓ RAG service initialization test passed")
                return True

        except Exception as e:
            logger.error(f"✗ RAG service initialization test failed: {e}")
            return False

    def test_bot_initialization(self):
        """Test bot initialization with database path."""
        logger.info("Testing bot initialization...")

        try:
            # Mock external dependencies
            with patch("bot.RAGService") as mock_rag, patch(
                "bot.ConversationService"
            ) as mock_conv:

                # Import bot module
                import bot

                # Verify conversation service was called with correct path
                mock_conv.assert_called_with(self.test_db_path)

                logger.info("✓ Bot initialization test passed")
                return True

        except Exception as e:
            logger.error(f"✗ Bot initialization test failed: {e}")
            return False

    def test_persistence_across_restarts(self):
        """Test data persistence across service restarts."""
        logger.info("Testing persistence across restarts...")

        try:
            from services.conversation_service import ConversationService

            test_user_id = 54321
            test_message = "Persistence test message"

            # First service instance - store data
            service1 = ConversationService(self.test_db_path)
            success = service1.store_message(test_user_id, "user", test_message)
            if not success:
                raise Exception("Failed to store message in first instance")

            # Close first instance
            service1.close()

            # Second service instance - retrieve data
            service2 = ConversationService(self.test_db_path)
            conversations = service2.get_recent_conversations(test_user_id, limit=1)

            if not conversations:
                raise Exception("No conversations found after restart")

            if conversations[0]["user"]["content"] != test_message:
                raise Exception("Message content doesn't match after restart")

            service2.close()

            logger.info("✓ Persistence test passed")
            return True

        except Exception as e:
            logger.error(f"✗ Persistence test failed: {e}")
            return False

    def test_educational_consultant_context(self):
        """Test educational consultant context building."""
        logger.info("Testing educational consultant context building...")

        try:
            from services.conversation_service import ConversationService

            # Mock educational programs data
            test_programs_data = """
            # ИТМО Образовательные Программы
            
            ## Магистратура "Искусственный интеллект"
            - Длительность: 2 года
            - Форма обучения: очная
            - Стоимость: 350,000 руб/год
            """

            # Create cool_diff.md file for testing
            cool_diff_path = Path("cool_diff.md")
            original_content = None

            if cool_diff_path.exists():
                with open(cool_diff_path, "r", encoding="utf-8") as f:
                    original_content = f.read()

            # Write test content
            with open(cool_diff_path, "w", encoding="utf-8") as f:
                f.write(test_programs_data)

            try:
                # Test conversation service with educational context
                service = ConversationService(self.test_db_path)

                test_user_id = 98765

                # Store conversation about educational programs
                service.store_message(
                    test_user_id, "user", "Расскажи о программе ИИ в ИТМО"
                )
                service.store_message(
                    test_user_id,
                    "bot",
                    'Программа "Искусственный интеллект" в ИТМО - это 2-летняя магистратура...',
                )

                # Retrieve and verify
                conversations = service.get_recent_conversations(test_user_id, limit=1)

                if not conversations:
                    raise Exception("No educational conversations found")

                conversation = conversations[0]
                if "ИТМО" not in conversation["user"]["content"]:
                    raise Exception("Educational context not preserved")

                service.close()

            finally:
                # Restore original content
                if original_content is not None:
                    with open(cool_diff_path, "w", encoding="utf-8") as f:
                        f.write(original_content)
                elif cool_diff_path.exists():
                    cool_diff_path.unlink()

            logger.info("✓ Educational consultant context test passed")
            return True

        except Exception as e:
            logger.error(f"✗ Educational consultant context test failed: {e}")
            return False

    def run_all_tests(self):
        """Run all integration tests."""
        logger.info("Starting full integration test suite...")

        try:
            self.setup_test_environment()

            tests = [
                ("Database Initialization", self.test_database_initialization),
                ("Database Migration", self.test_database_migration),
                ("Conversation Service", self.test_conversation_service),
                ("RAG Service Initialization", self.test_rag_service_initialization),
                ("Bot Initialization", self.test_bot_initialization),
                ("Persistence Across Restarts", self.test_persistence_across_restarts),
                (
                    "Educational Consultant Context",
                    self.test_educational_consultant_context,
                ),
            ]

            passed = 0
            failed = 0

            for test_name, test_func in tests:
                logger.info(f"\n--- Running {test_name} Test ---")
                try:
                    if test_func():
                        passed += 1
                    else:
                        failed += 1
                except Exception as e:
                    logger.error(f"Test {test_name} crashed: {e}")
                    failed += 1

            logger.info(f"\n=== Test Results ===")
            logger.info(f"Passed: {passed}")
            logger.info(f"Failed: {failed}")
            logger.info(f"Total: {passed + failed}")

            if failed == 0:
                logger.info("🎉 All tests passed!")
                return True
            else:
                logger.error(f"❌ {failed} test(s) failed!")
                return False

        finally:
            self.cleanup_test_environment()


def main():
    """Main function to run integration tests."""
    logger.info("Educational Consultant Bot - Full Integration Test")
    logger.info("=" * 60)

    # Run tests
    test_runner = FullIntegrationTest()
    success = test_runner.run_all_tests()

    if success:
        logger.info("\n✅ All integration tests passed successfully!")
        sys.exit(0)
    else:
        logger.error("\n❌ Some integration tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
