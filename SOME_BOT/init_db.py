#!/usr/bin/env python3
"""
Database initialization script for the educational consultant bot.
This script ensures the SQLite database is properly initialized before the bot starts.
"""

import os
import sys
import logging
import sqlite3
from pathlib import Path
from typing import Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """Handles database initialization and schema creation."""
    
    def __init__(self, db_path: str):
        """
        Initialize the database initializer.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.schema_version = 1
    
    def ensure_directory_exists(self) -> bool:
        """
        Ensure the database directory exists.
        
        Returns:
            True if directory exists or was created successfully
        """
        try:
            db_dir = Path(self.db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Database directory ensured: {db_dir}")
            return True
        except Exception as e:
            logger.error(f"Failed to create database directory: {e}")
            return False
    
    def create_tables(self, connection: sqlite3.Connection) -> bool:
        """
        Create database tables if they don't exist.
        
        Args:
            connection: SQLite database connection
            
        Returns:
            True if tables were created successfully
        """
        try:
            # Create conversations table
            connection.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    message_type TEXT NOT NULL CHECK (message_type IN ('user', 'bot')),
                    content TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create index for faster queries
            connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_timestamp 
                ON conversations (user_id, timestamp DESC)
            """)
            
            # Create schema version table
            connection.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert current schema version if not exists
            connection.execute("""
                INSERT OR IGNORE INTO schema_version (version) VALUES (?)
            """, (self.schema_version,))
            
            connection.commit()
            logger.info("Database tables created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            return False
    
    def verify_schema(self, connection: sqlite3.Connection) -> bool:
        """
        Verify the database schema is correct.
        
        Args:
            connection: SQLite database connection
            
        Returns:
            True if schema is valid
        """
        try:
            # Check if conversations table exists with correct columns
            cursor = connection.execute("""
                SELECT sql FROM sqlite_master 
                WHERE type='table' AND name='conversations'
            """)
            
            table_schema = cursor.fetchone()
            if not table_schema:
                logger.error("Conversations table does not exist")
                return False
            
            # Check required columns exist
            cursor = connection.execute("PRAGMA table_info(conversations)")
            columns = {row[1] for row in cursor.fetchall()}
            
            required_columns = {'id', 'user_id', 'message_type', 'content', 'timestamp', 'created_at'}
            if not required_columns.issubset(columns):
                missing = required_columns - columns
                logger.error(f"Missing required columns: {missing}")
                return False
            
            # Check schema version
            cursor = connection.execute("SELECT MAX(version) FROM schema_version")
            current_version = cursor.fetchone()[0]
            
            if current_version != self.schema_version:
                logger.warning(f"Schema version mismatch: expected {self.schema_version}, got {current_version}")
            
            logger.info("Database schema verification passed")
            return True
            
        except Exception as e:
            logger.error(f"Schema verification failed: {e}")
            return False
    
    def test_database_operations(self, connection: sqlite3.Connection) -> bool:
        """
        Test basic database operations.
        
        Args:
            connection: SQLite database connection
            
        Returns:
            True if operations work correctly
        """
        try:
            # Test insert
            test_user_id = 999999999
            cursor = connection.execute("""
                INSERT INTO conversations (user_id, message_type, content, timestamp)
                VALUES (?, ?, ?, ?)
            """, (test_user_id, 'user', 'Test message', 1234567890.0))
            
            # Test select
            cursor = connection.execute("""
                SELECT COUNT(*) FROM conversations WHERE user_id = ?
            """, (test_user_id,))
            
            count = cursor.fetchone()[0]
            if count != 1:
                logger.error(f"Insert test failed: expected 1 record, got {count}")
                return False
            
            # Test delete (cleanup)
            connection.execute("""
                DELETE FROM conversations WHERE user_id = ?
            """, (test_user_id,))
            
            connection.commit()
            logger.info("Database operations test passed")
            return True
            
        except Exception as e:
            logger.error(f"Database operations test failed: {e}")
            return False
    
    def initialize(self) -> bool:
        """
        Initialize the database completely.
        
        Returns:
            True if initialization was successful
        """
        logger.info(f"Starting database initialization: {self.db_path}")
        
        # Ensure directory exists
        if not self.ensure_directory_exists():
            return False
        
        try:
            # Connect to database
            connection = sqlite3.connect(self.db_path)
            connection.row_factory = sqlite3.Row
            
            # Create tables
            if not self.create_tables(connection):
                return False
            
            # Verify schema
            if not self.verify_schema(connection):
                return False
            
            # Test operations
            if not self.test_database_operations(connection):
                return False
            
            connection.close()
            logger.info("Database initialization completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            return False
    
    def get_database_info(self) -> dict:
        """
        Get information about the database.
        
        Returns:
            Dictionary with database information
        """
        try:
            if not os.path.exists(self.db_path):
                return {
                    'exists': False,
                    'size_bytes': 0,
                    'tables': [],
                    'schema_version': None
                }
            
            connection = sqlite3.connect(self.db_path)
            
            # Get file size
            size_bytes = os.path.getsize(self.db_path)
            
            # Get tables
            cursor = connection.execute("""
                SELECT name FROM sqlite_master WHERE type='table'
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            # Get schema version
            schema_version = None
            if 'schema_version' in tables:
                cursor = connection.execute("SELECT MAX(version) FROM schema_version")
                schema_version = cursor.fetchone()[0]
            
            connection.close()
            
            return {
                'exists': True,
                'size_bytes': size_bytes,
                'tables': tables,
                'schema_version': schema_version
            }
            
        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            return {
                'exists': False,
                'size_bytes': 0,
                'tables': [],
                'schema_version': None,
                'error': str(e)
            }


def main():
    """Main function to run database initialization."""
    # Get database path from environment or use default
    db_path = os.getenv('DATABASE_PATH', '/app/data/conversations.db')
    
    logger.info(f"Initializing database at: {db_path}")
    
    # Initialize database
    initializer = DatabaseInitializer(db_path)
    
    # Get current database info
    db_info = initializer.get_database_info()
    logger.info(f"Database info before initialization: {db_info}")
    
    # Run initialization
    success = initializer.initialize()
    
    if success:
        # Get updated database info
        db_info = initializer.get_database_info()
        logger.info(f"Database info after initialization: {db_info}")
        logger.info("Database initialization completed successfully!")
        sys.exit(0)
    else:
        logger.error("Database initialization failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()