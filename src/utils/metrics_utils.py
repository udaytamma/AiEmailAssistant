"""
Metrics Utility Module
Provides observability metrics tracking using SQLite database.
Tracks 24h, 7d, and all-time statistics.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
import threading

# Thread-safe database connection
_db_lock = threading.Lock()


class MetricsTracker:
    """Tracks and stores observability metrics in SQLite database."""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize metrics tracker.

        Args:
            db_path: Path to SQLite database file. If None, uses default location.
        """
        if db_path is None:
            db_dir = Path(__file__).parent.parent.parent / 'data' / 'metrics'
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = db_dir / 'metrics.db'

        self.db_path = str(db_path)
        self._initialize_database()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a thread-safe database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize_database(self):
        """Create database tables if they don't exist."""
        with _db_lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()

                # Script runs table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS script_runs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        execution_time REAL,
                        total_emails INTEGER,
                        success BOOLEAN,
                        error_message TEXT
                    )
                ''')

                # Email processing table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS email_processing (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        email_id TEXT,
                        category TEXT,
                        processing_time REAL
                    )
                ''')

                # API calls table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS api_calls (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        api_name TEXT,
                        operation TEXT,
                        success BOOLEAN,
                        cached BOOLEAN,
                        response_time REAL
                    )
                ''')

                # Cache operations table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS cache_operations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        operation TEXT,
                        key_type TEXT,
                        hit BOOLEAN
                    )
                ''')

                # Errors table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS errors (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        module TEXT,
                        error_type TEXT,
                        error_message TEXT,
                        stack_trace TEXT
                    )
                ''')

                # Create indexes for faster queries
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_script_runs_timestamp ON script_runs(timestamp)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_email_processing_timestamp ON email_processing(timestamp)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_api_calls_timestamp ON api_calls(timestamp)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_cache_operations_timestamp ON cache_operations(timestamp)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_errors_timestamp ON errors(timestamp)')

                conn.commit()
            finally:
                conn.close()

    def record_script_run(self, execution_time: float, total_emails: int, success: bool, error_message: str = None):
        """Record a script execution."""
        with _db_lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO script_runs (execution_time, total_emails, success, error_message)
                    VALUES (?, ?, ?, ?)
                ''', (execution_time, total_emails, success, error_message))
                conn.commit()
            finally:
                conn.close()

    def record_email_processing(self, email_id: str, category: str, processing_time: float):
        """Record email processing metrics."""
        with _db_lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO email_processing (email_id, category, processing_time)
                    VALUES (?, ?, ?)
                ''', (email_id, category, processing_time))
                conn.commit()
            finally:
                conn.close()

    def record_api_call(self, api_name: str, operation: str, success: bool, cached: bool, response_time: float):
        """Record API call metrics."""
        with _db_lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO api_calls (api_name, operation, success, cached, response_time)
                    VALUES (?, ?, ?, ?, ?)
                ''', (api_name, operation, success, cached, response_time))
                conn.commit()
            finally:
                conn.close()

    def record_cache_operation(self, operation: str, key_type: str, hit: bool = None):
        """Record cache operation metrics."""
        with _db_lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO cache_operations (operation, key_type, hit)
                    VALUES (?, ?, ?)
                ''', (operation, key_type, hit))
                conn.commit()
            finally:
                conn.close()

    def record_error(self, module: str, error_type: str, error_message: str, stack_trace: str = None):
        """Record error information."""
        with _db_lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO errors (module, error_type, error_message, stack_trace)
                    VALUES (?, ?, ?, ?)
                ''', (module, error_type, error_message, stack_trace))
                conn.commit()
            finally:
                conn.close()

    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive metrics summary for 24h, 7d, and all-time.

        Returns:
            Dict containing all tracked metrics
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now()
            day_ago = now - timedelta(days=1)
            week_ago = now - timedelta(days=7)

            metrics = {
                '24h': {},
                '7d': {},
                'all_time': {}
            }

            # Total emails processed
            for period, time_filter in [('24h', day_ago), ('7d', week_ago), ('all_time', None)]:
                if time_filter:
                    cursor.execute('''
                        SELECT SUM(total_emails) as total FROM script_runs
                        WHERE timestamp >= ? AND success = 1
                    ''', (time_filter,))
                else:
                    cursor.execute('SELECT SUM(total_emails) as total FROM script_runs WHERE success = 1')

                result = cursor.fetchone()
                metrics[period]['total_emails_processed'] = result['total'] or 0

            # Script run count and success rate
            for period, time_filter in [('24h', day_ago), ('7d', week_ago), ('all_time', None)]:
                if time_filter:
                    cursor.execute('''
                        SELECT COUNT(*) as total, SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful
                        FROM script_runs WHERE timestamp >= ?
                    ''', (time_filter,))
                else:
                    cursor.execute('SELECT COUNT(*) as total, SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful FROM script_runs')

                result = cursor.fetchone()
                total = result['total'] or 0
                successful = result['successful'] or 0
                metrics[period]['script_run_count'] = total
                metrics[period]['success_rate'] = (successful / total * 100) if total > 0 else 0

            # Average execution time
            for period, time_filter in [('24h', day_ago), ('7d', week_ago), ('all_time', None)]:
                if time_filter:
                    cursor.execute('''
                        SELECT AVG(execution_time) as avg_time FROM script_runs
                        WHERE timestamp >= ? AND success = 1
                    ''', (time_filter,))
                else:
                    cursor.execute('SELECT AVG(execution_time) as avg_time FROM script_runs WHERE success = 1')

                result = cursor.fetchone()
                metrics[period]['avg_execution_time'] = round(result['avg_time'] or 0, 2)

            # API calls count
            for period, time_filter in [('24h', day_ago), ('7d', week_ago), ('all_time', None)]:
                if time_filter:
                    cursor.execute('SELECT COUNT(*) as total FROM api_calls WHERE timestamp >= ?', (time_filter,))
                else:
                    cursor.execute('SELECT COUNT(*) as total FROM api_calls')

                result = cursor.fetchone()
                metrics[period]['api_calls_made'] = result['total'] or 0

            # Cache hit rate
            for period, time_filter in [('24h', day_ago), ('7d', week_ago), ('all_time', None)]:
                if time_filter:
                    cursor.execute('''
                        SELECT COUNT(*) as total, SUM(CASE WHEN hit = 1 THEN 1 ELSE 0 END) as hits
                        FROM cache_operations WHERE operation = 'GET' AND timestamp >= ?
                    ''', (time_filter,))
                else:
                    cursor.execute('''
                        SELECT COUNT(*) as total, SUM(CASE WHEN hit = 1 THEN 1 ELSE 0 END) as hits
                        FROM cache_operations WHERE operation = 'GET'
                    ''')

                result = cursor.fetchone()
                total = result['total'] or 0
                hits = result['hits'] or 0
                metrics[period]['cache_hit_rate'] = round((hits / total * 100) if total > 0 else 0, 2)

            # Emails by category (all-time only)
            cursor.execute('''
                SELECT category, COUNT(*) as count
                FROM email_processing
                GROUP BY category
            ''')
            category_counts = {row['category']: row['count'] for row in cursor.fetchall()}
            metrics['all_time']['emails_by_category'] = category_counts

            # Error count (24h only)
            cursor.execute('SELECT COUNT(*) as count FROM errors WHERE timestamp >= ?', (day_ago,))
            result = cursor.fetchone()
            metrics['24h']['error_count'] = result['count'] or 0

            # Average API response time (all-time)
            cursor.execute('SELECT AVG(response_time) as avg_time FROM api_calls WHERE success = 1')
            result = cursor.fetchone()
            metrics['all_time']['avg_api_response_time'] = round(result['avg_time'] or 0, 2)

            # Estimated API cost (assuming $0.01 per Gemini call)
            metrics['all_time']['estimated_api_cost'] = round(metrics['all_time']['api_calls_made'] * 0.01, 2)

            return metrics

        finally:
            conn.close()

    def get_recent_errors(self, limit: int = 10) -> list:
        """
        Get recent errors for display.

        Args:
            limit: Maximum number of errors to return

        Returns:
            List of error dictionaries
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT timestamp, module, error_type, error_message
                FROM errors
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))

            errors = []
            for row in cursor.fetchall():
                errors.append({
                    'timestamp': row['timestamp'],
                    'module': row['module'],
                    'error_type': row['error_type'],
                    'error_message': row['error_message']
                })

            return errors

        finally:
            conn.close()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get current cache statistics."""
        # This will be populated by cache_manager
        return {
            'current_size': 0,
            'max_size': 30,
            'utilization_percent': 0
        }


# Global metrics tracker instance
_metrics_tracker = None


def get_metrics_tracker() -> MetricsTracker:
    """Get or create the global metrics tracker instance."""
    global _metrics_tracker
    if _metrics_tracker is None:
        _metrics_tracker = MetricsTracker()
    return _metrics_tracker
