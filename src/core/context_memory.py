"""
Context Memory Manager
Manages compressed context and elaborate summaries for Need-Action and FYI emails.
Stores context in SQLite database for historical tracking.
"""

import sqlite3
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from utils.logger_utils import setup_logger, log_exception
from utils.metrics_utils import get_metrics_tracker

# Initialize logger
logger = setup_logger(__name__)


class ContextMemoryManager:
    """
    Manages email context memory with compressed storage and elaborate summaries.

    Stores:
    - compressed_context: Token-efficient representation for future AI queries
    - elaborate_summary: Human-readable 10-bullet summary
    - metadata: Timestamp, email count, categories
    """

    def __init__(self, db_path: str = "data/context_memory.db"):
        """
        Initialize Context Memory Manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        self.metrics = get_metrics_tracker()

        logger.info(f"Initializing ContextMemoryManager: {self.db_path}")
        self._init_database()

    def _init_database(self) -> None:
        """Initialize SQLite database with schema."""
        try:
            self.conn = sqlite3.connect(str(self.db_path))
            cursor = self.conn.cursor()

            # Create context_memory table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS context_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    compressed_context TEXT NOT NULL,
                    elaborate_summary TEXT NOT NULL,
                    email_count INTEGER NOT NULL,
                    categories TEXT NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create index on timestamp for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON context_memory(timestamp DESC)
            """)

            self.conn.commit()
            logger.info("Database initialized successfully")

        except Exception as e:
            log_exception(logger, e, "Failed to initialize database")
            self.metrics.record_error(__name__, type(e).__name__, str(e), traceback.format_exc())
            raise

    def save_context(
        self,
        compressed_context: str,
        elaborate_summary: List[str],
        email_count: int,
        categories: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Save compressed context and elaborate summary to database.

        Args:
            compressed_context: Token-efficient context representation
            elaborate_summary: List of bullet points (max 10)
            email_count: Number of emails in this context
            categories: List of categories included (e.g., ['Need-Action', 'FYI'])
            metadata: Optional additional metadata

        Returns:
            bool: True if saved successfully, False otherwise
        """
        logger.info(f"Saving context memory: {email_count} emails, {len(categories)} categories")

        try:
            cursor = self.conn.cursor()

            # Convert lists to JSON
            categories_json = json.dumps(categories)
            summary_json = json.dumps(elaborate_summary)
            metadata_json = json.dumps(metadata) if metadata else None

            # Get current timestamp
            timestamp = datetime.now().isoformat()

            # Insert into database
            cursor.execute("""
                INSERT INTO context_memory
                (timestamp, compressed_context, elaborate_summary, email_count, categories, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (timestamp, compressed_context, summary_json, email_count, categories_json, metadata_json))

            self.conn.commit()

            logger.info(f"Context memory saved successfully: ID={cursor.lastrowid}")
            return True

        except Exception as e:
            log_exception(logger, e, "Failed to save context memory")
            self.metrics.record_error(__name__, type(e).__name__, str(e), traceback.format_exc())
            return False

    def get_latest_context(self) -> Optional[Dict[str, Any]]:
        """
        Get the most recent context memory entry.

        Returns:
            dict: Latest context with keys:
                - id: Database ID
                - timestamp: ISO format timestamp
                - compressed_context: Compressed context string
                - elaborate_summary: List of bullet points
                - email_count: Number of emails
                - categories: List of categories
                - metadata: Additional metadata
                - created_at: Database creation timestamp
            None if no entries exist
        """
        try:
            cursor = self.conn.cursor()

            cursor.execute("""
                SELECT id, timestamp, compressed_context, elaborate_summary,
                       email_count, categories, metadata, created_at
                FROM context_memory
                ORDER BY timestamp DESC
                LIMIT 1
            """)

            row = cursor.fetchone()

            if not row:
                logger.info("No context memory entries found")
                return None

            return {
                'id': row[0],
                'timestamp': row[1],
                'compressed_context': row[2],
                'elaborate_summary': json.loads(row[3]),
                'email_count': row[4],
                'categories': json.loads(row[5]),
                'metadata': json.loads(row[6]) if row[6] else None,
                'created_at': row[7]
            }

        except Exception as e:
            log_exception(logger, e, "Failed to get latest context")
            self.metrics.record_error(__name__, type(e).__name__, str(e), traceback.format_exc())
            return None

    def get_context_by_date(self, date: str) -> Optional[Dict[str, Any]]:
        """
        Get context memory for a specific date.

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            dict: Context for the specified date
            None if not found
        """
        try:
            cursor = self.conn.cursor()

            cursor.execute("""
                SELECT id, timestamp, compressed_context, elaborate_summary,
                       email_count, categories, metadata, created_at
                FROM context_memory
                WHERE DATE(timestamp) = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (date,))

            row = cursor.fetchone()

            if not row:
                logger.info(f"No context memory found for date: {date}")
                return None

            return {
                'id': row[0],
                'timestamp': row[1],
                'compressed_context': row[2],
                'elaborate_summary': json.loads(row[3]),
                'email_count': row[4],
                'categories': json.loads(row[5]),
                'metadata': json.loads(row[6]) if row[6] else None,
                'created_at': row[7]
            }

        except Exception as e:
            log_exception(logger, e, f"Failed to get context for date: {date}")
            self.metrics.record_error(__name__, type(e).__name__, str(e), traceback.format_exc())
            return None

    def get_all_contexts(self, limit: int = 30) -> List[Dict[str, Any]]:
        """
        Get all context memory entries (most recent first).

        Args:
            limit: Maximum number of entries to return (default: 30)

        Returns:
            list: List of context dictionaries
        """
        try:
            cursor = self.conn.cursor()

            cursor.execute("""
                SELECT id, timestamp, compressed_context, elaborate_summary,
                       email_count, categories, metadata, created_at
                FROM context_memory
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))

            rows = cursor.fetchall()

            contexts = []
            for row in rows:
                contexts.append({
                    'id': row[0],
                    'timestamp': row[1],
                    'compressed_context': row[2],
                    'elaborate_summary': json.loads(row[3]),
                    'email_count': row[4],
                    'categories': json.loads(row[5]),
                    'metadata': json.loads(row[6]) if row[6] else None,
                    'created_at': row[7]
                })

            logger.info(f"Retrieved {len(contexts)} context memory entries")
            return contexts

        except Exception as e:
            log_exception(logger, e, "Failed to get all contexts")
            self.metrics.record_error(__name__, type(e).__name__, str(e), traceback.format_exc())
            return []

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about stored context memory.

        Returns:
            dict: Statistics with keys:
                - total_entries: Total number of entries
                - total_emails: Total emails across all contexts
                - earliest_date: Earliest timestamp
                - latest_date: Latest timestamp
        """
        try:
            cursor = self.conn.cursor()

            cursor.execute("""
                SELECT
                    COUNT(*) as total_entries,
                    SUM(email_count) as total_emails,
                    MIN(timestamp) as earliest_date,
                    MAX(timestamp) as latest_date
                FROM context_memory
            """)

            row = cursor.fetchone()

            return {
                'total_entries': row[0] or 0,
                'total_emails': row[1] or 0,
                'earliest_date': row[2],
                'latest_date': row[3]
            }

        except Exception as e:
            log_exception(logger, e, "Failed to get context stats")
            self.metrics.record_error(__name__, type(e).__name__, str(e), traceback.format_exc())
            return {
                'total_entries': 0,
                'total_emails': 0,
                'earliest_date': None,
                'latest_date': None
            }

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.debug("Database connection closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
