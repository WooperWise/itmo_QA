#!/usr/bin/env python3
"""
Database migration script for the educational consultant bot.
This script handles database schema updates and data migrations safely.
"""

import logging
import os
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DatabaseMigrator:
    """Handles database migrations and schema updates."""

    def __init__(self, db_path: str):
        """
        Initialize the database migrator.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.current_schema_version = 1
        self.migrations = {1: self._migration_v1_initial_schema}

    def get_current_version(self) -> int:
        """
        Get the current schema version from the database.

        Returns:
            Current schema version, or 0 if not found
        """
        try:
            if not os.path.exists(self.db_path):
                return 0

            connection = sqlite3.connect(self.db_path)

            # Check if schema_version table exists
            cursor = connection.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='schema_version'
            """
            )

            if not cursor.fetchone():
                connection.close()
                return 0

            # Get current version
            cursor = connection.execute("SELECT MAX(version) FROM schema_version")
            version = cursor.fetchone()[0]
            connection.close()

            return version if version is not None else 0

        except Exception as e:
            logger.error(f"Failed to get current schema version: {e}")
            return 0

    def create_backup(self) -> Optional[str]:
        """
        Create a backup of the database before migration.

        Returns:
            Path to backup file, or None if backup failed
        """
        try:
            if not os.path.exists(self.db_path):
                logger.info("No existing database to backup")
                return None

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.db_path}.backup_{timestamp}"

            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Database backup created: {backup_path}")
            return backup_path

        except Exception as e:
            logger.error(f"Failed to create database backup: {e}")
            return None

    def restore_backup(self, backup_path: str) -> bool:
        """
        Restore database from backup.

        Args:
            backup_path: Path to backup file

        Returns:
            True if restore was successful
        """
        try:
            if not os.path.exists(backup_path):
                logger.error(f"Backup file not found: {backup_path}")
                return False

            shutil.copy2(backup_path, self.db_path)
            logger.info(f"Database restored from backup: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to restore database from backup: {e}")
            return False

    def _migration_v1_initial_schema(self, connection: sqlite3.Connection) -> bool:
        """
        Migration v1: Create initial schema.

        Args:
            connection: SQLite database connection

        Returns:
            True if migration was successful
        """
        try:
            logger.info("Running migration v1: Initial schema")

            # Create conversations table
            connection.execute(
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
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_user_timestamp 
                ON conversations (user_id, timestamp DESC)
            """
            )

            # Create schema version table
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            connection.commit()
            logger.info("Migration v1 completed successfully")
            return True

        except Exception as e:
            logger.error(f"Migration v1 failed: {e}")
            return False

    def apply_migration(self, connection: sqlite3.Connection, version: int) -> bool:
        """
        Apply a specific migration.

        Args:
            connection: SQLite database connection
            version: Migration version to apply

        Returns:
            True if migration was successful
        """
        if version not in self.migrations:
            logger.error(f"Migration v{version} not found")
            return False

        try:
            # Apply migration
            if not self.migrations[version](connection):
                return False

            # Record migration in schema_version table
            connection.execute(
                """
                INSERT OR REPLACE INTO schema_version (version) VALUES (?)
            """,
                (version,),
            )

            connection.commit()
            logger.info(f"Migration v{version} applied successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to apply migration v{version}: {e}")
            return False

    def migrate(self) -> bool:
        """
        Run all pending migrations.

        Returns:
            True if all migrations were successful
        """
        logger.info("Starting database migration")

        # Get current version
        current_version = self.get_current_version()
        logger.info(f"Current schema version: {current_version}")
        logger.info(f"Target schema version: {self.current_schema_version}")

        if current_version >= self.current_schema_version:
            logger.info("Database is already up to date")
            return True

        # Create backup before migration
        backup_path = self.create_backup()

        try:
            # Ensure database directory exists
            db_dir = Path(self.db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)

            # Connect to database
            connection = sqlite3.connect(self.db_path)
            connection.row_factory = sqlite3.Row

            # Apply pending migrations
            for version in range(current_version + 1, self.current_schema_version + 1):
                logger.info(f"Applying migration v{version}")

                if not self.apply_migration(connection, version):
                    logger.error(f"Migration v{version} failed, rolling back")
                    connection.close()

                    # Restore backup if available
                    if backup_path:
                        self.restore_backup(backup_path)

                    return False

            connection.close()
            logger.info("All migrations completed successfully")

            # Clean up old backups (keep only the most recent 5)
            self.cleanup_old_backups()

            return True

        except Exception as e:
            logger.error(f"Migration failed: {e}")

            # Restore backup if available
            if backup_path:
                self.restore_backup(backup_path)

            return False

    def cleanup_old_backups(self, keep_count: int = 5) -> None:
        """
        Clean up old backup files, keeping only the most recent ones.

        Args:
            keep_count: Number of backup files to keep
        """
        try:
            db_dir = Path(self.db_path).parent
            backup_pattern = f"{Path(self.db_path).name}.backup_*"

            backup_files = list(db_dir.glob(backup_pattern))
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

            # Remove old backups
            for backup_file in backup_files[keep_count:]:
                backup_file.unlink()
                logger.info(f"Removed old backup: {backup_file}")

        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")

    def verify_migration(self) -> bool:
        """
        Verify that the migration was successful.

        Returns:
            True if verification passed
        """
        try:
            connection = sqlite3.connect(self.db_path)

            # Check schema version
            current_version = self.get_current_version()
            if current_version != self.current_schema_version:
                logger.error(
                    f"Schema version mismatch after migration: expected {self.current_schema_version}, got {current_version}"
                )
                return False

            # Check that required tables exist
            cursor = connection.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('conversations', 'schema_version')
            """
            )

            tables = {row[0] for row in cursor.fetchall()}
            required_tables = {"conversations", "schema_version"}

            if not required_tables.issubset(tables):
                missing = required_tables - tables
                logger.error(f"Missing required tables after migration: {missing}")
                return False

            # Test basic operations
            cursor = connection.execute("SELECT COUNT(*) FROM conversations")
            cursor.fetchone()

            connection.close()
            logger.info("Migration verification passed")
            return True

        except Exception as e:
            logger.error(f"Migration verification failed: {e}")
            return False

    def get_migration_info(self) -> Dict[str, Any]:
        """
        Get information about the migration status.

        Returns:
            Dictionary with migration information
        """
        current_version = self.get_current_version()

        return {
            "current_version": current_version,
            "target_version": self.current_schema_version,
            "needs_migration": current_version < self.current_schema_version,
            "available_migrations": list(self.migrations.keys()),
            "pending_migrations": [
                v for v in self.migrations.keys() if v > current_version
            ],
            "database_exists": os.path.exists(self.db_path),
        }


def main():
    """Main function to run database migration."""
    # Get database path from environment or use default
    db_path = os.getenv("DATABASE_PATH", "/app/data/conversations.db")

    logger.info(f"Starting database migration for: {db_path}")

    # Initialize migrator
    migrator = DatabaseMigrator(db_path)

    # Get migration info
    migration_info = migrator.get_migration_info()
    logger.info(f"Migration info: {migration_info}")

    # Run migration if needed
    if migration_info["needs_migration"]:
        logger.info("Running database migration...")
        success = migrator.migrate()

        if success:
            # Verify migration
            if migrator.verify_migration():
                logger.info("Database migration completed and verified successfully!")
                sys.exit(0)
            else:
                logger.error("Migration verification failed!")
                sys.exit(1)
        else:
            logger.error("Database migration failed!")
            sys.exit(1)
    else:
        logger.info("Database is already up to date, no migration needed")
        sys.exit(0)


if __name__ == "__main__":
    main()
