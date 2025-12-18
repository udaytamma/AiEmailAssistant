"""
Cache Manager for Email Assistant
Handles caching of email summaries to reduce API calls
"""

import json
import os
from datetime import datetime, timedelta

class CacheManager:
    """Manages email summary cache with LRU eviction (max 30 emails)"""

    def __init__(self, cache_file='email_cache.json', max_size=30, expiry_hours=24):
        self.cache_file = cache_file
        self.max_size = max_size
        self.expiry_hours = expiry_hours
        self.cache = self.load_cache()

    def load_cache(self):
        """Load cache from JSON file"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                    # Clean expired entries
                    return self._clean_expired(cache_data)
            return {}
        except Exception as e:
            print(f"⚠️  Error loading cache: {e}")
            return {}

    def _clean_expired(self, cache_data):
        """Remove expired cache entries"""
        now = datetime.now()
        cleaned = {}

        for email_id, entry in cache_data.items():
            cached_time = datetime.fromisoformat(entry['cached_at'])
            if now - cached_time < timedelta(hours=self.expiry_hours):
                cleaned[email_id] = entry

        return cleaned

    def _enforce_size_limit(self):
        """Enforce maximum cache size using LRU (Least Recently Used)"""
        if len(self.cache) > self.max_size:
            # Sort by access time (oldest first)
            sorted_items = sorted(
                self.cache.items(),
                key=lambda x: x[1].get('accessed_at', x[1]['cached_at'])
            )
            # Keep only the most recent max_size items
            self.cache = dict(sorted_items[-self.max_size:])

    def get(self, email_id):
        """
        Retrieve cached summary for an email
        Updates access time for LRU
        """
        if email_id in self.cache:
            # Update access time
            self.cache[email_id]['accessed_at'] = datetime.now().isoformat()
            return self.cache[email_id]['data']
        return None

    def set(self, email_id, data):
        """
        Cache email summary data
        data should include: category, summary, newsletter_summary, etc.
        """
        self.cache[email_id] = {
            'data': data,
            'cached_at': datetime.now().isoformat(),
            'accessed_at': datetime.now().isoformat()
        }

        # Enforce size limit
        self._enforce_size_limit()

    def save(self):
        """Save cache to JSON file"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            print(f"⚠️  Error saving cache: {e}")

    def clear(self):
        """Clear all cached data"""
        self.cache = {}
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)
        print("✅ Cache cleared")

    def stats(self):
        """Display cache statistics"""
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

            print("\n" + "=" * 80)
            print("CACHE STATISTICS")
            print("=" * 80)
            print(f"Total cached emails: {total_entries}/{self.max_size}")
            print(f"Cache file: {self.cache_file}")
            print(f"Expiry time: {self.expiry_hours} hours")
            print(f"Oldest entry: {oldest_entry}")
            print(f"Newest entry: {newest_entry}")
            print("=" * 80 + "\n")
        else:
            print("📭 Cache is empty")

    def has(self, email_id):
        """Check if email_id is in cache"""
        return email_id in self.cache

# Example usage
if __name__ == '__main__':
    cache = CacheManager()
    cache.stats()
