"""
Cache Manager for Email Assistant
Handles caching of email summaries to reduce API calls with error handling and logging.
"""

import json
import os
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional, Dict

# Import logging utilities
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.logger_utils import setup_logger, log_exception, log_cache_operation
from utils.metrics_utils import get_metrics_tracker

# Initialize logger
logger = setup_logger(__name__)


class CacheError(Exception):
    """Raised when cache operations fail."""
    pass


class CacheManager:
    """Manages email summary cache with LRU eviction (max 30 emails)."""

    def __init__(self, cache_file: Optional[str] = None, max_size: int = 30, expiry_hours: int = 24):
        """
        Initialize CacheManager.

        Args:
            cache_file: Path to cache file. If None, uses default location.
            max_size: Maximum number of cached emails (default: 30)
            expiry_hours: Cache expiry time in hours (default: 24)
        """
        if cache_file is None:
            # Use data/cache/email_cache.json in project root
            cache_dir = Path(__file__).parent.parent.parent / 'data' / 'cache'
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = cache_dir / 'email_cache.json'

        self.cache_file = str(cache_file)
        self.max_size = max_size
        self.expiry_hours = expiry_hours
        self.cache = self.load_cache()
        self.last_fetch_timestamp = self.cache.get('_metadata', {}).get('last_fetch_timestamp')
        logger.info(f"CacheManager initialized: file={self.cache_file}, max_size={max_size}, expiry={expiry_hours}h, last_fetch={self.last_fetch_timestamp}")

    def load_cache(self) -> Dict[str, Any]:
        """
        Load cache from JSON file.

        Returns:
            dict: Cache dictionary

        Note:
            Automatically cleans expired entries on load.
        """
        metrics = get_metrics_tracker()

        try:
            if not os.path.exists(self.cache_file):
                logger.info(f"Cache file does not exist, starting with empty cache")
                return {}

            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)

            logger.info(f"Loaded {len(cache_data)} entries from cache")

            # Clean expired entries
            cleaned_cache = self._clean_expired(cache_data)
            expired_count = len(cache_data) - len(cleaned_cache)
            if expired_count > 0:
                logger.info(f"Removed {expired_count} expired cache entries")

            return cleaned_cache

        except json.JSONDecodeError as e:
            error_msg = f"Error parsing cache file: {e}"
            logger.error(error_msg)
            metrics.record_error(__name__, "JSONDecodeError", error_msg)
            print(f"⚠️  {error_msg}. Starting with empty cache.")
            return {}

        except PermissionError as e:
            error_msg = f"Permission denied reading cache file: {e}"
            logger.error(error_msg)
            metrics.record_error(__name__, "PermissionError", error_msg)
            print(f"⚠️  {error_msg}. Starting with empty cache.")
            return {}

        except Exception as e:
            log_exception(logger, e, "Error loading cache")
            metrics.record_error(__name__, type(e).__name__, str(e), traceback.format_exc())
            print(f"⚠️  Error loading cache: {e}. Starting with empty cache.")
            return {}

    def _clean_expired(self, cache_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove expired cache entries.

        Args:
            cache_data: Cache dictionary to clean

        Returns:
            dict: Cleaned cache dictionary
        """
        try:
            now = datetime.now()
            cleaned = {}

            for email_id, entry in cache_data.items():
                # Skip metadata entry
                if email_id == '_metadata':
                    cleaned[email_id] = entry
                    continue

                try:
                    cached_time = datetime.fromisoformat(entry['cached_at'])
                    if now - cached_time < timedelta(hours=self.expiry_hours):
                        cleaned[email_id] = entry
                    else:
                        logger.debug(f"Expired cache entry removed: {email_id}")
                except (KeyError, ValueError) as e:
                    logger.warning(f"Invalid cache entry for {email_id}: {e}")
                    continue

            return cleaned

        except Exception as e:
            logger.error(f"Error cleaning expired entries: {e}")
            return cache_data

    def _enforce_size_limit(self) -> None:
        """
        Enforce maximum cache size using LRU (Least Recently Used).

        Note:
            Removes oldest entries when cache exceeds max_size.
        """
        try:
            if len(self.cache) > self.max_size:
                eviction_count = len(self.cache) - self.max_size
                logger.info(f"Cache size limit exceeded, evicting {eviction_count} entries")

                # Sort by access time (oldest first)
                sorted_items = sorted(
                    self.cache.items(),
                    key=lambda x: x[1].get('accessed_at', x[1]['cached_at'])
                )

                # Keep only the most recent max_size items
                self.cache = dict(sorted_items[-self.max_size:])

                metrics = get_metrics_tracker()
                for _ in range(eviction_count):
                    metrics.record_cache_operation('EVICT', 'email_summary', None)

                logger.debug(f"Cache size after eviction: {len(self.cache)}")

        except Exception as e:
            logger.error(f"Error enforcing cache size limit: {e}")

    def get(self, email_id: str) -> Optional[Any]:
        """
        Retrieve cached summary for an email.
        Updates access time for LRU.

        Args:
            email_id: Email ID to retrieve

        Returns:
            Cached data or None if not found
        """
        try:
            if email_id in self.cache:
                # Update access time
                self.cache[email_id]['accessed_at'] = datetime.now().isoformat()
                data = self.cache[email_id]['data']

                log_cache_operation(logger, 'GET', email_id, True)
                logger.debug(f"Cache hit for: {email_id}")

                return data

            log_cache_operation(logger, 'GET', email_id, False)
            logger.debug(f"Cache miss for: {email_id}")
            return None

        except Exception as e:
            logger.error(f"Error retrieving from cache for {email_id}: {e}")
            return None

    def set(self, email_id: str, data: Any) -> bool:
        """
        Cache email summary data.

        Args:
            email_id: Email ID
            data: Data to cache (should include: category, summary, newsletter_summary, etc.)

        Returns:
            bool: True if successful, False otherwise
        """
        metrics = get_metrics_tracker()

        try:
            self.cache[email_id] = {
                'data': data,
                'cached_at': datetime.now().isoformat(),
                'accessed_at': datetime.now().isoformat()
            }

            # Enforce size limit
            self._enforce_size_limit()

            log_cache_operation(logger, 'SET', email_id, None)
            logger.debug(f"Cached data for: {email_id}")

            return True

        except Exception as e:
            log_exception(logger, e, f"Error caching data for {email_id}")
            metrics.record_error(__name__, type(e).__name__, f"Cache set failed: {e}")
            return False

    def save(self) -> bool:
        """
        Save cache to JSON file.

        Returns:
            bool: True if successful, False otherwise
        """
        metrics = get_metrics_tracker()

        try:
            # Update last fetch timestamp in metadata
            if '_metadata' not in self.cache:
                self.cache['_metadata'] = {}
            if self.last_fetch_timestamp:
                self.cache['_metadata']['last_fetch_timestamp'] = self.last_fetch_timestamp

            # Ensure directory exists
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)

            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)

            email_count = len([k for k in self.cache.keys() if k != '_metadata'])
            logger.info(f"Cache saved to {self.cache_file} ({email_count} entries)")
            return True

        except PermissionError as e:
            error_msg = f"Permission denied saving cache: {e}"
            logger.error(error_msg)
            metrics.record_error(__name__, "PermissionError", error_msg)
            print(f"⚠️  {error_msg}")
            return False

        except Exception as e:
            log_exception(logger, e, "Error saving cache")
            metrics.record_error(__name__, type(e).__name__, str(e), traceback.format_exc())
            print(f"⚠️  Error saving cache: {e}")
            return False

    def clear(self) -> bool:
        """
        Clear all cached data.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.cache = {}
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)

            logger.info("Cache cleared successfully")
            print("✅ Cache cleared")
            return True

        except Exception as e:
            log_exception(logger, e, "Error clearing cache")
            print(f"⚠️  Error clearing cache: {e}")
            return False

    def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            dict: Cache statistics including size, oldest/newest entries
        """
        try:
            total_entries = len(self.cache)

            if total_entries > 0:
                oldest_entry = min(
                    self.cache.values(),
                    key=lambda x: x['cached_at']
                )['cached_at']
                newest_entry = max(
                    self.cache.values(),
                    key=lambda x: x['cached_at']
                )['cached_at']

                stats_data = {
                    'total_entries': total_entries,
                    'max_size': self.max_size,
                    'utilization_percent': round((total_entries / self.max_size) * 100, 2),
                    'cache_file': self.cache_file,
                    'expiry_hours': self.expiry_hours,
                    'oldest_entry': oldest_entry,
                    'newest_entry': newest_entry
                }

                print("\n" + "=" * 80)
                print("CACHE STATISTICS")
                print("=" * 80)
                print(f"Total cached emails: {total_entries}/{self.max_size} ({stats_data['utilization_percent']}%)")
                print(f"Cache file: {self.cache_file}")
                print(f"Expiry time: {self.expiry_hours} hours")
                print(f"Oldest entry: {oldest_entry}")
                print(f"Newest entry: {newest_entry}")
                print("=" * 80 + "\n")

                return stats_data
            else:
                print("📭 Cache is empty")
                return {
                    'total_entries': 0,
                    'max_size': self.max_size,
                    'utilization_percent': 0,
                    'cache_file': self.cache_file,
                    'expiry_hours': self.expiry_hours
                }

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            print(f"⚠️  Error getting cache statistics: {e}")
            return {}

    def has(self, email_id: str) -> bool:
        """
        Check if email_id is in cache.

        Args:
            email_id: Email ID to check

        Returns:
            bool: True if in cache, False otherwise
        """
        return email_id in self.cache

    def get_last_fetch_timestamp(self) -> Optional[str]:
        """
        Get the timestamp of the last email fetch.

        Returns:
            ISO format timestamp string or None if never fetched
        """
        return self.last_fetch_timestamp

    def update_last_fetch_timestamp(self, timestamp: str) -> None:
        """
        Update the last fetch timestamp.

        Args:
            timestamp: ISO format timestamp string
        """
        self.last_fetch_timestamp = timestamp
        logger.info(f"Updated last fetch timestamp: {timestamp}")

    def get_all_cached_emails(self) -> Dict[str, Any]:
        """
        Get all cached email data (excluding metadata).

        Returns:
            dict: Dictionary of email_id -> email data
        """
        return {k: v['data'] for k, v in self.cache.items() if k != '_metadata'}


# Example usage
if __name__ == '__main__':
    cache = CacheManager()
    cache.stats()
