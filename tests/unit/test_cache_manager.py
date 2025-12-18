"""
Unit Tests for CacheManager

Tests individual cache operations in isolation:
- Setting and getting cache entries
- Cache expiry logic
- LRU eviction strategy
- Timestamp tracking for incremental fetching
- Metadata management
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

import pytest
#from freezegun import freeze_time  # Disabled - Python 3.14 incompatible

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from core.cache_manager import CacheManager


# ==============================================================================
# UNIT TEST: Basic Cache Operations (GET/SET/HAS)
# ==============================================================================

@pytest.mark.unit
@pytest.mark.basic
def test_cache_set_and_get(test_cache_manager):
    """
    Test basic cache set and get operations.

    Verifies:
    - set() stores data correctly
    - get() retrieves the same data
    - has() correctly identifies cached items
    """
    # Set a cache entry
    email_id = "test_email_123"
    email_data = {
        'category': 'FYI',
        'subcategory': 'General',
        'summary': 'Test email summary',
        'action_item': 'None',
        'date_due': None
    }

    result = test_cache_manager.set(email_id, email_data)
    assert result is True, "set() should return True on success"

    # Verify has() works
    assert test_cache_manager.has(email_id), "has() should return True for cached item"

    # Retrieve and verify
    cached_data = test_cache_manager.get(email_id)
    assert cached_data is not None, "get() should return data"
    assert cached_data['category'] == 'FYI', "Cached category should match"
    assert cached_data['summary'] == 'Test email summary', "Cached summary should match"


@pytest.mark.unit
@pytest.mark.basic
def test_cache_get_nonexistent(test_cache_manager):
    """
    Test that get() returns None for non-existent cache keys.

    Verifies:
    - get() on missing key returns None
    - has() returns False for missing key
    """
    result = test_cache_manager.get("nonexistent_id")
    assert result is None, "get() should return None for missing key"

    assert not test_cache_manager.has("nonexistent_id"), "has() should return False for missing key"


# ==============================================================================
# UNIT TEST: Timestamp Tracking for Incremental Fetching
# ==============================================================================

@pytest.mark.unit
@pytest.mark.basic
def test_last_fetch_timestamp_tracking(test_cache_manager):
    """
    Test timestamp tracking for incremental email fetching.

    Verifies:
    - Initial timestamp is None
    - update_last_fetch_timestamp() updates the timestamp
    - get_last_fetch_timestamp() returns correct value
    - Timestamp persists after save/load cycle
    """
    # Initially should be None
    assert test_cache_manager.get_last_fetch_timestamp() is None

    # Update timestamp
    test_timestamp = "2025-01-15T10:30:00"
    test_cache_manager.update_last_fetch_timestamp(test_timestamp)

    # Verify update
    assert test_cache_manager.get_last_fetch_timestamp() == test_timestamp

    # Save and reload to verify persistence
    test_cache_manager.save()

    # Create new cache instance (simulates app restart)
    new_cache = CacheManager(
        cache_file=test_cache_manager.cache_file,
        max_size=10,
        expiry_hours=24
    )

    # Timestamp should persist
    assert new_cache.get_last_fetch_timestamp() == test_timestamp


# ==============================================================================
# UNIT TEST: Cache Expiry Logic
# ==============================================================================

@pytest.mark.unit
@pytest.mark.extended
def test_cache_expiry_removes_old_entries(tmp_path):
    """
    Test that expired cache entries are automatically removed.

    Verifies:
    - Fresh entries are kept
    - Entries older than expiry_hours are removed
    - Expiry is calculated correctly based on cached_at timestamp
    """
    cache_file = tmp_path / 'expiry_cache.json'

    # Create cache with 2-hour expiry
    with freeze_time("2025-01-15 10:00:00"):
        cache = CacheManager(
            cache_file=str(cache_file),
            max_size=30,
            expiry_hours=2
        )

        # Add entry at 10:00
        cache.set("email_old", {'category': 'FYI', 'summary': 'Old email'})
        cache.save()

    # Advance time by 1 hour (still valid)
    with freeze_time("2025-01-15 11:00:00"):
        cache_1h = CacheManager(cache_file=str(cache_file), max_size=30, expiry_hours=2)
        assert cache_1h.has("email_old"), "Entry should still be valid after 1 hour"

    # Advance time by 3 hours (expired)
    with freeze_time("2025-01-15 13:00:00"):
        cache_3h = CacheManager(cache_file=str(cache_file), max_size=30, expiry_hours=2)
        assert not cache_3h.has("email_old"), "Entry should be expired after 3 hours"


@pytest.mark.unit
@pytest.mark.extended
def test_cache_expiry_mixed_ages(tmp_path):
    """
    Test cache expiry with mixed fresh and old entries.

    Verifies:
    - Multiple entries with different ages
    - Only expired entries are removed
    - Fresh entries are preserved
    """
    cache_file = tmp_path / 'mixed_expiry_cache.json'

    with freeze_time("2025-01-15 10:00:00"):
        cache = CacheManager(cache_file=str(cache_file), max_size=30, expiry_hours=1)

        # Add old email at 10:00
        cache.set("email_old_1", {'category': 'FYI', 'summary': 'Old 1'})
        cache.set("email_old_2", {'category': 'FYI', 'summary': 'Old 2'})
        cache.save()

    # Advance 30 minutes, add fresh email
    with freeze_time("2025-01-15 10:30:00"):
        cache_mid = CacheManager(cache_file=str(cache_file), max_size=30, expiry_hours=1)
        cache_mid.set("email_fresh", {'category': 'Need-Action', 'summary': 'Fresh'})
        cache_mid.save()

    # Advance to 11:30 (old emails expired, fresh still valid)
    with freeze_time("2025-01-15 11:30:00"):
        cache_check = CacheManager(cache_file=str(cache_file), max_size=30, expiry_hours=1)

        # Old emails should be gone
        assert not cache_check.has("email_old_1"), "Old email 1 should be expired"
        assert not cache_check.has("email_old_2"), "Old email 2 should be expired"

        # Fresh email should remain
        assert cache_check.has("email_fresh"), "Fresh email should still be valid"


# ==============================================================================
# UNIT TEST: LRU Eviction Strategy
# ==============================================================================

@pytest.mark.unit
@pytest.mark.comprehensive
def test_lru_eviction_oldest_removed(tmp_path):
    """
    Test that LRU eviction removes the oldest (least recently used) entries.

    Verifies:
    - When cache exceeds max_size, oldest entries are evicted
    - Eviction count is correct
    - Newest entries are preserved
    """
    cache_file = tmp_path / 'lru_cache.json'
    cache = CacheManager(cache_file=str(cache_file), max_size=3, expiry_hours=24)

    # Add 5 emails (exceeds max_size of 3)
    for i in range(5):
        cache.set(f"email_{i}", {'category': 'FYI', 'summary': f'Email {i}'})

    # Should only have newest 3 emails + metadata
    email_count = len([k for k in cache.cache.keys() if k != '_metadata'])
    assert email_count == 3, "Should have only 3 emails after eviction"

    # Oldest should be evicted
    assert not cache.has("email_0"), "Oldest email should be evicted"
    assert not cache.has("email_1"), "Second oldest should be evicted"

    # Newest should remain
    assert cache.has("email_2"), "Third email should be kept"
    assert cache.has("email_3"), "Fourth email should be kept"
    assert cache.has("email_4"), "Newest email should be kept"


@pytest.mark.unit
@pytest.mark.comprehensive
def test_lru_eviction_accessed_items_preserved(tmp_path):
    """
    Test that recently accessed items are preserved during LRU eviction.

    Verifies:
    - Accessing an item updates its access time
    - Recently accessed items are not evicted
    - LRU prioritizes by access time, not just creation time
    """
    from time import sleep

    cache_file = tmp_path / 'lru_access_cache.json'
    cache = CacheManager(cache_file=str(cache_file), max_size=3, expiry_hours=24)

    # Add 3 emails (fills cache)
    cache.set("email_0", {'category': 'FYI', 'summary': 'Email 0'})
    sleep(0.01)  # Small delay to ensure different timestamps
    cache.set("email_1", {'category': 'FYI', 'summary': 'Email 1'})
    sleep(0.01)
    cache.set("email_2", {'category': 'FYI', 'summary': 'Email 2'})

    # Access email_0 (updates its access time to most recent)
    cache.get("email_0")
    sleep(0.01)

    # Add new email (triggers eviction)
    cache.set("email_3", {'category': 'FYI', 'summary': 'Email 3'})

    # email_1 should be evicted (oldest access time)
    # email_0 should be kept (recently accessed)
    assert cache.has("email_0"), "Recently accessed email should be preserved"
    assert not cache.has("email_1"), "Least recently used should be evicted"
    assert cache.has("email_2"), "Recent email should be kept"
    assert cache.has("email_3"), "New email should be kept"


# ==============================================================================
# UNIT TEST: Cache Save and Load
# ==============================================================================

@pytest.mark.unit
@pytest.mark.basic
def test_cache_save_and_load_persistence(tmp_path):
    """
    Test that cache data persists across save/load cycles.

    Verifies:
    - save() writes data to file correctly
    - Load creates new CacheManager with persisted data
    - All email data is preserved
    - Metadata is preserved
    """
    cache_file = tmp_path / 'persist_cache.json'

    # Create cache and add data
    cache1 = CacheManager(cache_file=str(cache_file), max_size=10, expiry_hours=24)
    cache1.set("email_1", {'category': 'FYI', 'summary': 'Email 1'})
    cache1.set("email_2", {'category': 'Need-Action', 'summary': 'Email 2'})
    cache1.update_last_fetch_timestamp("2025-01-15T12:00:00")

    # Save
    result = cache1.save()
    assert result is True, "save() should return True"
    assert cache_file.exists(), "Cache file should be created"

    # Load in new instance
    cache2 = CacheManager(cache_file=str(cache_file), max_size=10, expiry_hours=24)

    # Verify data persisted
    assert cache2.has("email_1"), "Email 1 should be loaded"
    assert cache2.has("email_2"), "Email 2 should be loaded"
    email1_data = cache2.get("email_1")
    assert email1_data['category'] == 'FYI', "Category should be preserved"
    assert cache2.get_last_fetch_timestamp() == "2025-01-15T12:00:00", "Timestamp should persist"


# ==============================================================================
# UNIT TEST: Cache Clear
# ==============================================================================

@pytest.mark.unit
@pytest.mark.basic
def test_cache_clear_removes_all_data(test_cache_manager):
    """
    Test that clear() removes all cached data and file.

    Verifies:
    - clear() empties the cache
    - Cache file is deleted
    - clear() returns True on success
    """
    # Add data
    test_cache_manager.set("email_1", {'category': 'FYI'})
    test_cache_manager.set("email_2", {'category': 'FYI'})
    test_cache_manager.save()

    assert test_cache_manager.has("email_1"), "Email should be cached before clear"

    # Clear cache
    result = test_cache_manager.clear()
    assert result is True, "clear() should return True"

    # Verify empty
    assert len(test_cache_manager.cache) == 0, "Cache should be empty"
    assert not test_cache_manager.has("email_1"), "Email should not exist after clear"


# ==============================================================================
# UNIT TEST: get_all_cached_emails
# ==============================================================================

@pytest.mark.unit
@pytest.mark.extended
def test_get_all_cached_emails_excludes_metadata(test_cache_manager):
    """
    Test that get_all_cached_emails() returns only email data, not metadata.

    Verifies:
    - Returns dictionary of email_id -> email_data
    - Excludes _metadata entry
    - Returns all cached emails
    """
    # Add emails and metadata
    test_cache_manager.set("email_1", {'category': 'FYI', 'summary': 'Email 1'})
    test_cache_manager.set("email_2", {'category': 'Need-Action', 'summary': 'Email 2'})
    test_cache_manager.update_last_fetch_timestamp("2025-01-15T10:00:00")

    # Get all cached emails
    all_emails = test_cache_manager.get_all_cached_emails()

    # Verify
    assert len(all_emails) == 2, "Should return only emails, not metadata"
    assert "email_1" in all_emails, "Should include email_1"
    assert "email_2" in all_emails, "Should include email_2"
    assert "_metadata" not in all_emails, "Should exclude metadata"

    # Verify data structure
    assert all_emails["email_1"]['category'] == 'FYI'
    assert all_emails["email_2"]['category'] == 'Need-Action'


# ==============================================================================
# UNIT TEST: Cache Stats
# ==============================================================================

@pytest.mark.unit
@pytest.mark.extended
def test_cache_stats_returns_correct_info(test_cache_manager):
    """
    Test that stats() returns accurate cache statistics.

    Verifies:
    - Returns total_entries count
    - Returns max_size
    - Returns utilization_percent
    - Returns oldest/newest entry timestamps
    """
    # Add 3 emails
    test_cache_manager.set("email_1", {'category': 'FYI'})
    test_cache_manager.set("email_2", {'category': 'FYI'})
    test_cache_manager.set("email_3", {'category': 'FYI'})

    # Get stats
    stats = test_cache_manager.stats()

    # Verify stats
    assert stats['total_entries'] == 4, "Should count emails + metadata"
    assert stats['max_size'] == 10, "Should return configured max_size"
    assert stats['utilization_percent'] == 40.0, "Should calculate utilization (4/10 = 40%)"
    assert 'oldest_entry' in stats, "Should include oldest entry timestamp"
    assert 'newest_entry' in stats, "Should include newest entry timestamp"
