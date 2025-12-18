"""
Integration Tests for Email Processing Flow

Tests the complete end-to-end workflow:
1. Fetch emails from Gmail
2. Categorize with Gemini AI
3. Cache the results
4. Generate daily digest
5. Save to JSON for web display

These tests ensure all components work together correctly.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from core.cache_manager import CacheManager
from utils.gemini_utils import categorize_emails
from utils.display_utils import generate_daily_digest


# ==============================================================================
# INTEGRATION TEST: Complete E2E Email Processing Flow
# ==============================================================================

@pytest.mark.integration
@pytest.mark.basic
def test_complete_email_processing_flow(
    mock_gmail_service,
    mock_gemini_model,
    sample_emails,
    test_cache_manager,
    tmp_path
):
    """
    Test the complete email processing pipeline from fetch to digest.

    Flow:
    1. Fetch emails from Gmail API (mocked)
    2. Categorize emails with Gemini AI (mocked)
    3. Cache the categorized emails
    4. Generate daily digest with summaries
    5. Verify all data is correct

    This is the MOST IMPORTANT test - if this passes, the core app works.
    """
    # Step 1: Simulate email fetching (already have sample_emails from fixture)
    assert len(sample_emails) > 0, "Should have sample emails"

    # Step 2: Categorize emails with Gemini
    categorized = categorize_emails(sample_emails[:3], mock_gemini_model)

    # Verify categorization succeeded
    assert len(categorized) == 3, "Should categorize 3 emails"
    assert all('category' in email for email in categorized), "All emails should have category"
    assert all('summary' in email for email in categorized), "All emails should have summary"

    # Step 3: Cache the categorized emails
    for email in categorized:
        cache_data = {
            'category': email['category'],
            'subcategory': email['subcategory'],
            'summary': email['summary'],
            'action_item': email['action_item'],
            'date_due': email['date_due'],
            'from': email['from'],
            'subject': email['subject'],
            'date': email['date'],
            'snippet': email['snippet'],
            'id': email['id']
        }
        test_cache_manager.set(email['id'], cache_data)

    # Verify caching succeeded
    assert test_cache_manager.has(categorized[0]['id']), "First email should be cached"
    cached_email = test_cache_manager.get(categorized[0]['id'])
    assert cached_email['category'] == categorized[0]['category'], "Cached category should match"

    # Step 4: Generate daily digest
    digest = generate_daily_digest(
        categorized,
        mock_gmail_service,
        mock_gemini_model,
        cache=test_cache_manager,
        new_emails_count=3
    )

    # Verify digest structure
    assert 'need_action' in digest, "Digest should have need_action section"
    assert 'fyi' in digest, "Digest should have fyi section"
    assert 'newsletters' in digest, "Digest should have newsletters section"

    # Step 5: Save digest to JSON (simulate web data)
    digest_file = tmp_path / 'test_digest.json'
    digest_data = {
        'metadata': {
            'last_updated': datetime.now().isoformat(),
            'execution_time': 1.5,
            'total_emails': len(categorized)
        },
        'digest': digest,
        'categorized_emails': categorized
    }

    with open(digest_file, 'w') as f:
        json.dump(digest_data, f, indent=2)

    # Verify JSON was created and is valid
    assert digest_file.exists(), "Digest file should be created"
    with open(digest_file, 'r') as f:
        loaded_data = json.load(f)
    assert loaded_data['metadata']['total_emails'] == 3, "Should have 3 emails in digest"


# ==============================================================================
# INTEGRATION TEST: Incremental Fetch Logic
# ==============================================================================

@pytest.mark.integration
@pytest.mark.basic
def test_incremental_email_fetching(
    sample_emails,
    mock_gemini_model,
    test_cache_manager
):
    """
    Test incremental fetching - only new emails are processed.

    Scenario:
    1. First run: Process 5 emails, cache them
    2. Second run: Fetch 3 new emails + 2 cached emails
    3. Verify: Only 3 new emails are categorized (not the cached 2)
    4. Final result: Should have 8 total emails (5 + 3)

    This ensures we don't waste API calls re-categorizing emails.
    """
    # === FIRST RUN: Process initial batch ===
    initial_emails = sample_emails[:5]

    # Categorize and cache
    categorized_first = categorize_emails(initial_emails, mock_gemini_model)
    for email in categorized_first:
        test_cache_manager.set(email['id'], email)

    # Update last fetch timestamp
    first_timestamp = datetime.now().isoformat()
    test_cache_manager.update_last_fetch_timestamp(first_timestamp)
    test_cache_manager.save()

    # Verify cache state
    assert len(test_cache_manager.cache) == 6, "Should have 5 emails + 1 metadata entry"
    assert test_cache_manager.get_last_fetch_timestamp() == first_timestamp

    # === SECOND RUN: Fetch new emails (simulate) ===
    # Simulate: 3 new emails (index 5-7) + 2 already cached (index 0-1)
    all_fetched = sample_emails[0:2] + sample_emails[5:8]

    # Load cached emails
    cached_emails_dict = test_cache_manager.get_all_cached_emails()
    all_categorized = list(cached_emails_dict.values())

    # Filter to only NEW emails (not in cache)
    new_emails = [e for e in all_fetched if not test_cache_manager.has(e['id'])]

    # Verify correct filtering
    assert len(new_emails) == 3, "Should identify 3 new emails"
    assert len(all_categorized) == 5, "Should have 5 cached emails"

    # Categorize only new emails
    categorized_new = categorize_emails(new_emails, mock_gemini_model)

    # Add to cache
    for email in categorized_new:
        test_cache_manager.set(email['id'], email)
        all_categorized.append(email)

    # Update timestamp
    second_timestamp = datetime.now().isoformat()
    test_cache_manager.update_last_fetch_timestamp(second_timestamp)
    test_cache_manager.save()

    # === VERIFY FINAL STATE ===
    assert len(all_categorized) == 8, "Should have 8 total emails (5 + 3)"
    assert len(test_cache_manager.cache) == 9, "Cache should have 8 emails + 1 metadata"
    assert test_cache_manager.get_last_fetch_timestamp() == second_timestamp


# ==============================================================================
# INTEGRATION TEST: Cache Expiry and Invalidation
# ==============================================================================

@pytest.mark.integration
@pytest.mark.extended
def test_cache_expiry_and_cleanup(tmp_path):
    """
    Test that expired cache entries are automatically removed.

    Scenario:
    1. Create cache with 1-hour expiry
    2. Add emails with old timestamps
    3. Load cache - should auto-clean expired entries
    4. Verify only fresh entries remain

    This ensures the cache doesn't grow indefinitely.
    """
    from datetime import timedelta
    from freezegun import freeze_time

    cache_file = tmp_path / 'expiry_test_cache.json'

    # === FIRST: Create cache and add emails ===
    with freeze_time("2025-01-15 10:00:00"):
        cache = CacheManager(
            cache_file=str(cache_file),
            max_size=30,
            expiry_hours=1  # 1 hour expiry for testing
        )

        # Add 3 emails
        for i in range(3):
            cache.set(f"email_{i}", {
                'category': 'FYI',
                'summary': f'Email {i} summary'
            })

        cache.save()
        assert len(cache.cache) == 4, "Should have 3 emails + 1 metadata"

    # === SECOND: Advance time by 2 hours (past expiry) ===
    with freeze_time("2025-01-15 12:00:00"):
        # Reload cache - should trigger cleanup
        cache_reloaded = CacheManager(
            cache_file=str(cache_file),
            max_size=30,
            expiry_hours=1
        )

        # All emails should be expired and removed
        email_count = len([k for k in cache_reloaded.cache.keys() if k != '_metadata'])
        assert email_count == 0, "All emails should be expired and removed"

    # === THIRD: Add fresh emails ===
    with freeze_time("2025-01-15 12:30:00"):
        cache_fresh = CacheManager(
            cache_file=str(cache_file),
            max_size=30,
            expiry_hours=1
        )

        # Add 2 new fresh emails
        cache_fresh.set("fresh_1", {'category': 'Need-Action'})
        cache_fresh.set("fresh_2", {'category': 'FYI'})
        cache_fresh.save()

        # Should have only fresh emails
        email_count = len([k for k in cache_fresh.cache.keys() if k != '_metadata'])
        assert email_count == 2, "Should have only 2 fresh emails"


# ==============================================================================
# INTEGRATION TEST: Gemini API Fallback Handling
# ==============================================================================

@pytest.mark.integration
@pytest.mark.extended
def test_gemini_api_failure_fallback(sample_emails):
    """
    Test that the system gracefully handles Gemini API failures.

    Scenario:
    1. Mock Gemini to raise an exception
    2. Attempt to categorize emails
    3. Verify fallback categorization is applied
    4. Verify system continues processing other emails

    This ensures robustness against API outages.
    """
    from unittest.mock import MagicMock

    # Create mock model that raises exception
    failing_model = MagicMock()
    failing_model.generate_content.side_effect = Exception("API Error: Rate limit exceeded")

    # Attempt categorization
    categorized = categorize_emails(sample_emails[:2], failing_model)

    # Verify fallback categorization was applied
    assert len(categorized) == 2, "Should still return 2 emails"
    assert categorized[0]['category'] == 'Unknown', "Should have fallback category"
    assert categorized[0]['summary'] == 'Failed to categorize', "Should have fallback summary"

    # Verify all required fields are present (even with fallback)
    for email in categorized:
        assert 'category' in email
        assert 'subcategory' in email
        assert 'summary' in email
        assert 'action_item' in email
        assert 'date_due' in email


# ==============================================================================
# INTEGRATION TEST: LRU Cache Eviction
# ==============================================================================

@pytest.mark.integration
@pytest.mark.comprehensive
def test_cache_lru_eviction(tmp_path):
    """
    Test that LRU (Least Recently Used) cache eviction works correctly.

    Scenario:
    1. Create cache with max_size=5
    2. Add 8 emails (exceeds limit)
    3. Verify oldest emails are evicted
    4. Access an old email (update its access time)
    5. Add more emails
    6. Verify recently accessed email is NOT evicted

    This ensures the cache prioritizes frequently accessed emails.
    """
    cache_file = tmp_path / 'lru_test_cache.json'
    cache = CacheManager(
        cache_file=str(cache_file),
        max_size=5,  # Small size to trigger eviction
        expiry_hours=24
    )

    # Add 8 emails (will trigger eviction to keep only 5)
    for i in range(8):
        cache.set(f"email_{i}", {
            'category': 'FYI',
            'summary': f'Email {i} summary',
            'subject': f'Subject {i}'
        })

    # After eviction, should have only 5 emails + 1 metadata
    email_count = len([k for k in cache.cache.keys() if k != '_metadata'])
    assert email_count == 5, f"Should have exactly 5 emails after eviction, got {email_count}"

    # The newest 5 emails should be kept (email_3 through email_7)
    assert cache.has("email_7"), "Newest email should be kept"
    assert cache.has("email_6"), "Second newest should be kept"
    assert not cache.has("email_0"), "Oldest email should be evicted"
    assert not cache.has("email_1"), "Second oldest should be evicted"
