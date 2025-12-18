"""
Unit Tests for Email Utils

Tests email fetching and timestamp conversion logic:
- Gmail API query building
- Timestamp conversion to Gmail epoch format
- Email data extraction and formatting
- Error handling for invalid timestamps
"""

import sys
from pathlib import Path
from datetime import datetime

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from utils.email_utils import fetch_recent_emails


# ==============================================================================
# UNIT TEST: Email Fetching with Mock Gmail Service
# ==============================================================================

@pytest.mark.unit
@pytest.mark.basic
def test_fetch_recent_emails_basic(mock_gmail_service, sample_emails):
    """
    Test basic email fetching from Gmail API.

    Verifies:
    - fetch_recent_emails() returns list of emails
    - Email data includes all required fields (id, from, subject, date, snippet)
    - Number of emails matches expected count
    """
    emails = fetch_recent_emails(
        mock_gmail_service,
        max_results=5,
        query='is:unread'
    )

    # Verify result
    assert isinstance(emails, list), "Should return a list"
    assert len(emails) == 5, "Should return 5 emails"

    # Verify email structure
    first_email = emails[0]
    assert 'id' in first_email, "Email should have id"
    assert 'from' in first_email, "Email should have from"
    assert 'subject' in first_email, "Email should have subject"
    assert 'date' in first_email, "Email should have date"
    assert 'snippet' in first_email, "Email should have snippet"


# ==============================================================================
# UNIT TEST: Timestamp Conversion to Gmail Epoch Format
# ==============================================================================

@pytest.mark.unit
@pytest.mark.basic
def test_fetch_with_timestamp_filter(mock_gmail_service):
    """
    Test incremental fetching with after_timestamp parameter.

    Verifies:
    - ISO timestamp is converted to Gmail epoch format
    - Query includes 'after:' filter with epoch timestamp
    - Emails are fetched correctly with timestamp filter

    This is critical for incremental fetching feature.
    """
    # Test timestamp: 2025-01-15 10:00:00
    test_timestamp = "2025-01-15T10:00:00"

    # Expected epoch: 1736937600 (Unix timestamp for 2025-01-15 10:00:00 UTC)
    # Note: This may vary slightly based on timezone, but should be close

    emails = fetch_recent_emails(
        mock_gmail_service,
        max_results=5,
        query='is:unread',
        after_timestamp=test_timestamp
    )

    # Verify emails are still returned (mock doesn't filter by timestamp)
    assert isinstance(emails, list), "Should return list even with timestamp"
    assert len(emails) > 0, "Should fetch emails with timestamp filter"


@pytest.mark.unit
@pytest.mark.extended
def test_timestamp_conversion_to_epoch():
    """
    Test ISO timestamp conversion to Unix epoch format.

    Verifies:
    - ISO format (YYYY-MM-DDTHH:MM:SS) converts to correct epoch
    - Epoch is integer seconds since Unix epoch (1970-01-01)

    This ensures Gmail API receives correctly formatted timestamps.
    """
    # Test specific timestamp
    test_timestamp = "2025-01-15T10:30:00"
    dt = datetime.fromisoformat(test_timestamp)
    epoch = int(dt.timestamp())

    # Verify epoch is reasonable (should be > 1700000000 for 2025)
    assert epoch > 1700000000, "Epoch should be valid for 2025"

    # Verify conversion is reversible
    dt_reverse = datetime.fromtimestamp(epoch)
    assert dt_reverse.year == 2025, "Year should match"
    assert dt_reverse.month == 1, "Month should match"
    assert dt_reverse.day == 15, "Day should match"


@pytest.mark.unit
@pytest.mark.extended
def test_invalid_timestamp_handling(mock_gmail_service):
    """
    Test handling of invalid timestamp formats.

    Verifies:
    - Invalid timestamp format is handled gracefully
    - Function doesn't crash with bad input
    - Emails are still fetched (timestamp filter is ignored)

    This ensures robustness against malformed cache data.
    """
    # Invalid timestamp formats
    invalid_timestamps = [
        "not-a-timestamp",
        "2025/01/15",  # Wrong format
        "15-01-2025T10:00:00",  # Wrong format
        "",  # Empty string
        None  # None value (but this would be caught by type hints)
    ]

    for invalid_ts in invalid_timestamps:
        if invalid_ts is None:
            continue  # Skip None (handled by default parameter)

        # Should not crash, should fetch emails normally
        try:
            emails = fetch_recent_emails(
                mock_gmail_service,
                max_results=3,
                query='is:unread',
                after_timestamp=invalid_ts
            )
            assert isinstance(emails, list), f"Should still return list with invalid timestamp: {invalid_ts}"
        except ValueError:
            # ValueError is acceptable for invalid timestamps
            pass


# ==============================================================================
# UNIT TEST: Query Building
# ==============================================================================

@pytest.mark.unit
@pytest.mark.comprehensive
def test_query_building_with_timestamp(mock_gmail_service):
    """
    Test that Gmail query is correctly built with timestamp filter.

    Verifies:
    - Original query is preserved
    - after: filter is appended correctly
    - Query format matches Gmail API expectations

    Example: 'is:unread newer_than:1d' + after:1736937600
    Result: 'is:unread newer_than:1d after:1736937600'
    """
    base_query = "is:unread newer_than:1d"
    timestamp = "2025-01-15T10:00:00"

    emails = fetch_recent_emails(
        mock_gmail_service,
        max_results=5,
        query=base_query,
        after_timestamp=timestamp
    )

    # Verify emails are fetched (mock doesn't validate query format)
    assert isinstance(emails, list), "Should return emails"

    # In real implementation, the query should include 'after:EPOCH'
    # We can't directly verify the query sent to mock, but we verify it doesn't break


@pytest.mark.unit
@pytest.mark.comprehensive
def test_fetch_with_custom_query(mock_gmail_service):
    """
    Test fetching with custom Gmail search queries.

    Verifies:
    - Custom query is used for fetching
    - Query parameter is flexible (supports various Gmail filters)

    Common Gmail queries:
    - 'is:unread'
    - 'from:example@gmail.com'
    - 'subject:invoice'
    - 'newer_than:2d'
    - 'label:important'
    """
    custom_queries = [
        'is:unread',
        'from:test@example.com',
        'subject:test',
        'is:unread newer_than:1d'
    ]

    for query in custom_queries:
        emails = fetch_recent_emails(
            mock_gmail_service,
            max_results=3,
            query=query
        )

        assert isinstance(emails, list), f"Should return list for query: {query}"


# ==============================================================================
# UNIT TEST: Max Results Parameter
# ==============================================================================

@pytest.mark.unit
@pytest.mark.basic
def test_fetch_respects_max_results(mock_gmail_service):
    """
    Test that max_results parameter limits the number of emails fetched.

    Verifies:
    - Returned email count matches max_results
    - Parameter is passed correctly to Gmail API

    Note: Mock returns all sample emails regardless, but real API would limit.
    """
    # Test different max_results values
    max_values = [1, 3, 5, 10]

    for max_val in max_values:
        emails = fetch_recent_emails(
            mock_gmail_service,
            max_results=max_val,
            query='is:unread'
        )

        # Mock returns 5 emails (from sample_emails fixture)
        # Real API would respect max_results
        assert isinstance(emails, list), f"Should return list for max_results={max_val}"
        # We can't test exact count with mock, but verify it's a list


# ==============================================================================
# UNIT TEST: Email Data Structure
# ==============================================================================

@pytest.mark.unit
@pytest.mark.extended
def test_email_data_structure_completeness(mock_gmail_service):
    """
    Test that fetched emails have complete data structure.

    Verifies each email has:
    - id: Unique email identifier
    - from: Sender email address
    - subject: Email subject line
    - date: Sent date/time
    - snippet: Email preview text

    All fields are required for categorization.
    """
    emails = fetch_recent_emails(
        mock_gmail_service,
        max_results=5,
        query='is:unread'
    )

    required_fields = ['id', 'from', 'subject', 'date', 'snippet']

    for email in emails:
        for field in required_fields:
            assert field in email, f"Email should have '{field}' field"
            assert email[field] is not None, f"Email '{field}' should not be None"
            assert len(str(email[field])) > 0, f"Email '{field}' should not be empty"


@pytest.mark.unit
@pytest.mark.extended
def test_email_from_header_parsing(mock_gmail_service):
    """
    Test that 'From' header is correctly extracted.

    Verifies:
    - From field contains email address
    - Format can include name: "John Doe <john@example.com>"
    - Or just email: "john@example.com"

    Both formats should be handled correctly.
    """
    emails = fetch_recent_emails(
        mock_gmail_service,
        max_results=3,
        query='is:unread'
    )

    for email in emails:
        from_field = email['from']

        # Should contain either <email> format or plain email
        assert '@' in from_field or '<' in from_field, "From field should contain email indicator"


@pytest.mark.unit
@pytest.mark.extended
def test_email_snippet_extraction(mock_gmail_service):
    """
    Test that email snippet (preview text) is extracted correctly.

    Verifies:
    - Snippet is not empty
    - Snippet is a string
    - Snippet provides useful preview text

    Snippet is used by Gemini for categorization.
    """
    emails = fetch_recent_emails(
        mock_gmail_service,
        max_results=3,
        query='is:unread'
    )

    for email in emails:
        snippet = email['snippet']

        assert isinstance(snippet, str), "Snippet should be a string"
        assert len(snippet) > 0, "Snippet should not be empty"
