"""
pytest configuration and shared fixtures for Email Assistant tests

This file contains:
- Shared test fixtures used across multiple test files
- Mock objects for external APIs (Gmail, Gemini)
- Test data setup and teardown
- Common test utilities
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock

import pytest

# Add src directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.cache_manager import CacheManager
from core.config_manager import ConfigManager


# ==============================================================================
# FIXTURE: Temporary directories for test isolation
# ==============================================================================

@pytest.fixture
def temp_cache_dir(tmp_path):
    """
    Create a temporary cache directory for test isolation.
    Each test gets a fresh cache directory that's automatically cleaned up.

    Returns:
        Path: Temporary directory path
    """
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir


@pytest.fixture
def temp_data_dir(tmp_path):
    """
    Create a temporary data directory for test isolation.
    Used for storing test digest files and metrics.

    Returns:
        Path: Temporary directory path
    """
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


# ==============================================================================
# FIXTURE: Sample email data from actual digest
# ==============================================================================

@pytest.fixture
def sample_emails():
    """
    Load sample emails from fixtures directory.
    These are real emails from the digest (no PII risk).

    Returns:
        List[Dict]: List of email dictionaries with id, from, subject, snippet, date
    """
    fixtures_path = Path(__file__).parent / 'fixtures' / 'sample_emails.json'
    with open(fixtures_path, 'r') as f:
        return json.load(f)


@pytest.fixture
def sample_categorized_emails():
    """
    Load sample categorized emails (emails with AI categorization).

    Returns:
        List[Dict]: Emails with category, subcategory, summary, action_item fields
    """
    fixtures_path = Path(__file__).parent / 'fixtures' / 'categorized_emails.json'
    with open(fixtures_path, 'r') as f:
        return json.load(f)


# ==============================================================================
# FIXTURE: Mock Gemini AI responses
# ==============================================================================

@pytest.fixture
def mock_gemini_responses():
    """
    Load mock Gemini API responses for contract testing.

    Returns:
        Dict: Dictionary of mock responses for different scenarios
    """
    fixtures_path = Path(__file__).parent / 'fixtures' / 'gemini_responses.json'
    with open(fixtures_path, 'r') as f:
        return json.load(f)


@pytest.fixture
def mock_gemini_client(mock_gemini_responses):
    """
    Create a mock Gemini client for testing (google.genai.Client).
    Returns predefined responses instead of calling the actual API.

    Args:
        mock_gemini_responses: Fixture with mock response data

    Returns:
        MagicMock: Mock Gemini client object with models.generate_content method
    """
    client = MagicMock()

    # Mock the models.generate_content method (new google.genai API)
    def generate_content_side_effect(model, contents):
        response = MagicMock()
        # Return first mock categorization response
        response.text = json.dumps(mock_gemini_responses['categorization_success'])
        return response

    client.models.generate_content.side_effect = generate_content_side_effect
    return client


@pytest.fixture
def mock_gemini_model(mock_gemini_client):
    """
    Alias for backward compatibility. Use mock_gemini_client instead.

    Returns:
        MagicMock: Mock Gemini client object
    """
    return mock_gemini_client


# ==============================================================================
# FIXTURE: Mock Gmail API service
# ==============================================================================

@pytest.fixture
def mock_gmail_service(sample_emails):
    """
    Create a mock Gmail API service for testing.
    Simulates Gmail API responses without making actual API calls.

    Args:
        sample_emails: Fixture with sample email data

    Returns:
        MagicMock: Mock Gmail service object
    """
    service = MagicMock()

    # Mock the messages().list() method
    def list_side_effect(**kwargs):
        result = MagicMock()
        # Return message IDs
        result.execute.return_value = {
            'messages': [{'id': email['id']} for email in sample_emails[:5]]
        }
        return result

    # Mock the messages().get() method
    def get_side_effect(**kwargs):
        result = MagicMock()
        # Extract id from kwargs
        email_id = kwargs.get('id')
        # Find email by ID
        email = next((e for e in sample_emails if e['id'] == email_id), sample_emails[0])
        result.execute.return_value = {
            'id': email['id'],
            'payload': {
                'headers': [
                    {'name': 'From', 'value': email['from']},
                    {'name': 'Subject', 'value': email['subject']},
                    {'name': 'Date', 'value': email['date']}
                ]
            },
            'snippet': email['snippet']
        }
        return result

    service.users().messages().list.side_effect = list_side_effect
    service.users().messages().get.side_effect = get_side_effect

    return service


# ==============================================================================
# FIXTURE: Test cache manager
# ==============================================================================

@pytest.fixture
def test_cache_manager(temp_cache_dir):
    """
    Create a CacheManager instance for testing with temporary storage.

    Args:
        temp_cache_dir: Fixture providing temporary cache directory

    Returns:
        CacheManager: Cache manager with test configuration
    """
    cache_file = temp_cache_dir / 'test_cache.json'
    cache = CacheManager(
        cache_file=str(cache_file),
        max_size=10,  # Smaller size for testing
        expiry_hours=24
    )
    return cache


# ==============================================================================
# FIXTURE: Test configuration
# ==============================================================================

@pytest.fixture
def test_config(temp_data_dir):
    """
    Create a test configuration with temporary paths.

    Args:
        temp_data_dir: Fixture providing temporary data directory

    Returns:
        Dict: Test configuration dictionary
    """
    return {
        'gmail_settings': {
            'max_emails_to_fetch': 10,
            'search_query': 'is:unread newer_than:1d'
        },
        'api_settings': {
            'gemini_model': 'gemini-2.5-flash-lite',
            'rate_limit_requests_per_minute': 30
        },
        'cache_settings': {
            'enabled': True,
            'cache_file': str(temp_data_dir / 'cache' / 'test_cache.json'),
            'max_cached_emails': 10,
            'cache_expiry_hours': 24
        }
    }


# ==============================================================================
# FIXTURE: Environment variables
# ==============================================================================

@pytest.fixture
def mock_env_vars(monkeypatch):
    """
    Set up mock environment variables for testing.

    Args:
        monkeypatch: pytest's monkeypatch fixture for modifying environment
    """
    monkeypatch.setenv('GOOGLE_API_KEY', 'test_api_key_12345')
    monkeypatch.setenv('GEMINI_API_KEY', 'test_gemini_key_67890')


# ==============================================================================
# FIXTURE: Freeze time for timestamp testing
# ==============================================================================

@pytest.fixture
def frozen_time():
    """
    Freeze time for testing timestamp-dependent functionality.
    Uses freezegun to mock datetime.now()

    Returns:
        datetime: Frozen datetime object
    """
    from freezegun import freeze_time
    from datetime import datetime

    # Freeze time to a specific moment
    frozen_datetime = datetime(2025, 1, 15, 10, 30, 0)
    with freeze_time(frozen_datetime):
        yield frozen_datetime


# ==============================================================================
# UTILITY: Test data generators
# ==============================================================================

def create_test_email(
    email_id: str = "test_123",
    from_addr: str = "test@example.com",
    subject: str = "Test Email",
    snippet: str = "This is a test email",
    date: str = "2025-01-15T10:00:00"
) -> Dict[str, str]:
    """
    Create a test email dictionary with specified parameters.

    Args:
        email_id: Email ID
        from_addr: Sender email address
        subject: Email subject
        snippet: Email snippet/preview
        date: Email date in ISO format

    Returns:
        Dict: Email dictionary
    """
    return {
        'id': email_id,
        'from': from_addr,
        'subject': subject,
        'snippet': snippet,
        'date': date
    }


def create_test_categorized_email(
    email_id: str = "test_123",
    category: str = "FYI",
    subcategory: str = "General",
    summary: str = "Test summary",
    action_item: str = "None",
    **kwargs
) -> Dict[str, Any]:
    """
    Create a test categorized email with AI fields.

    Args:
        email_id: Email ID
        category: Category (Need-Action, FYI, Newsletter, Marketing, SPAM)
        subcategory: Subcategory
        summary: Email summary
        action_item: Action item
        **kwargs: Additional email fields

    Returns:
        Dict: Categorized email dictionary
    """
    base_email = create_test_email(email_id=email_id, **kwargs)
    base_email.update({
        'category': category,
        'subcategory': subcategory,
        'summary': summary,
        'action_item': action_item,
        'date_due': None
    })
    return base_email


# Make utility functions available to all tests
pytest.create_test_email = create_test_email
pytest.create_test_categorized_email = create_test_categorized_email
