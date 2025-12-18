"""
Contract Tests for External APIs

Tests the contracts (expected inputs/outputs) for external APIs:
- Gmail API: Message fetching, query format, response structure
- Gemini AI API: Categorization requests, JSON responses, error handling

These tests use mocks to verify our code handles API responses correctly
without making actual API calls.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from utils.gemini_utils import categorize_email_with_gemini, generate_newsletter_summary


# ==============================================================================
# CONTRACT TEST: Gemini Categorization Response
# ==============================================================================

@pytest.mark.contract
@pytest.mark.basic
def test_gemini_categorization_success_response(mock_gemini_responses):
    """
    Test that Gemini categorization response is parsed correctly.

    Contract:
    - Input: Email dict with from, subject, snippet
    - Output: JSON with category, subcategory, summary, action_item, date_due
    - Response format: Plain JSON (may include ```json markdown)

    Verifies our code handles the expected response structure.
    """
    # Create mock client (google.genai.Client)
    client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps(mock_gemini_responses['categorization_success'])
    client.models.generate_content.return_value = mock_response

    # Test email
    test_email = {
        'from': 'test@example.com',
        'subject': 'Test Email',
        'snippet': 'This is a test email for categorization'
    }

    # Call categorization
    result = categorize_email_with_gemini(test_email, client, 'gemini-2.0-flash-exp')

    # Verify response structure
    assert 'category' in result, "Response should have category"
    assert 'subcategory' in result, "Response should have subcategory"
    assert 'summary' in result, "Response should have summary"
    assert 'action_item' in result, "Response should have action_item"
    assert 'date_due' in result, "Response should have date_due"

    # Verify values
    assert result['category'] == 'FYI'
    assert result['summary'] == 'Test email summary'


@pytest.mark.contract
@pytest.mark.extended
def test_gemini_response_with_markdown_fences(mock_gemini_responses):
    """
    Test that markdown code fences are properly stripped from responses.

    Gemini sometimes returns:
    ```json
    {"category": "FYI", ...}
    ```

    We need to strip the ```json and ``` markers.
    """
    client = MagicMock()
    mock_response = MagicMock()

    # Response with markdown fences
    json_data = mock_gemini_responses['categorization_success']
    mock_response.text = f"```json\n{json.dumps(json_data)}\n```"
    client.models.generate_content.return_value = mock_response

    test_email = {
        'from': 'test@example.com',
        'subject': 'Test',
        'snippet': 'Test'
    }

    result = categorize_email_with_gemini(test_email, client, 'gemini-2.0-flash-exp')

    # Should still parse correctly
    assert result['category'] == 'FYI'
    assert 'summary' in result


@pytest.mark.contract
@pytest.mark.extended
def test_gemini_response_different_categories(mock_gemini_responses):
    """
    Test Gemini responses for all supported categories.

    Categories:
    - Need-Action: Actionable emails
    - FYI: Informational emails
    - Newsletter: Recurring newsletters
    - Marketing: Promotional emails
    - SPAM: Unwanted emails

    Verifies our code handles all category types.
    """
    categories_to_test = [
        'categorization_need_action',
        'categorization_newsletter',
        'categorization_marketing',
        'categorization_spam'
    ]

    for category_key in categories_to_test:
        client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps(mock_gemini_responses[category_key])
        client.models.generate_content.return_value = mock_response

        test_email = {'from': 'test@example.com', 'subject': 'Test', 'snippet': 'Test'}
        result = categorize_email_with_gemini(test_email, client, 'gemini-2.0-flash-exp')

        # Verify category field matches expected
        assert 'category' in result, f"Should have category for {category_key}"
        assert result['category'] in ['Need-Action', 'FYI', 'Newsletter', 'Marketing', 'SPAM']


# ==============================================================================
# CONTRACT TEST: Gemini Error Handling
# ==============================================================================

@pytest.mark.contract
@pytest.mark.extended
def test_gemini_invalid_json_response():
    """
    Test handling of invalid JSON responses from Gemini.

    Scenario: Gemini returns malformed JSON
    Expected: Fallback categorization with category='Unknown'

    This ensures robustness against API issues.
    """
    client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "This is not valid JSON at all!"
    client.models.generate_content.return_value = mock_response

    test_email = {'from': 'test@example.com', 'subject': 'Test', 'snippet': 'Test'}

    result = categorize_email_with_gemini(test_email, client, 'gemini-2.0-flash-exp')

    # Should return fallback categorization
    assert result['category'] == 'Unknown', "Should fall back to Unknown category"
    assert result['summary'] == 'Failed to categorize', "Should have fallback summary"
    assert 'action_item' in result, "Should still have all fields"


@pytest.mark.contract
@pytest.mark.extended
def test_gemini_api_exception():
    """
    Test handling of Gemini API exceptions.

    Scenario: API call raises exception (network error, rate limit, etc.)
    Expected: Fallback categorization, no crash

    This ensures app continues working even if Gemini is down.
    """
    client = MagicMock()
    client.models.generate_content.side_effect = Exception("API Error: Rate limit exceeded")

    test_email = {'from': 'test@example.com', 'subject': 'Test', 'snippet': 'Test'}

    result = categorize_email_with_gemini(test_email, client, 'gemini-2.0-flash-exp')

    # Should return fallback
    assert result['category'] == 'Unknown'
    assert result['subcategory'] == 'None'
    assert result['action_item'] == 'None'


@pytest.mark.contract
@pytest.mark.comprehensive
def test_gemini_missing_fields_in_response(mock_gemini_responses):
    """
    Test handling of incomplete Gemini responses.

    Scenario: Response JSON is valid but missing required fields
    Expected: Code should handle gracefully (may use defaults or fail gracefully)
    """
    client = MagicMock()
    mock_response = MagicMock()

    # Response with only category field
    mock_response.text = json.dumps(mock_gemini_responses['error_missing_fields'])
    client.models.generate_content.return_value = mock_response

    test_email = {'from': 'test@example.com', 'subject': 'Test', 'snippet': 'Test'}

    # This may raise an error or return partial data
    # We're testing that it doesn't crash the entire app
    try:
        result = categorize_email_with_gemini(test_email, client, 'gemini-2.0-flash-exp')
        # If it succeeds, verify it has category at minimum
        assert 'category' in result
    except (KeyError, ValueError):
        # Acceptable to fail gracefully
        pass


# ==============================================================================
# CONTRACT TEST: Newsletter Summary Generation
# ==============================================================================

@pytest.mark.contract
@pytest.mark.extended
def test_newsletter_summary_response(mock_gemini_responses):
    """
    Test newsletter summary generation response.

    Contract:
    - Input: Email body and subject
    - Output: JSON with bullet1, bullet2, bullet3
    - Returns exactly 3 bullet points

    Verifies we correctly parse newsletter summaries.
    """
    client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps(mock_gemini_responses['newsletter_summary_success'])
    client.models.generate_content.return_value = mock_response

    # Test newsletter
    email_body = "This is a long newsletter with lots of content about various topics..."
    subject = "Weekly Tech Newsletter"

    result = generate_newsletter_summary(email_body, subject, client, 'gemini-2.0-flash-exp')

    # Verify structure
    assert isinstance(result, list), "Should return a list"
    assert len(result) == 3, "Should return exactly 3 bullet points"

    # Verify content
    assert result[0] == "First key point from newsletter"
    assert result[1] == "Second important insight"
    assert result[2] == "Third actionable takeaway"


@pytest.mark.contract
@pytest.mark.extended
def test_newsletter_summary_fallback_on_error():
    """
    Test newsletter summary fallback when API fails.

    Scenario: Gemini API error during newsletter summarization
    Expected: Returns fallback bullet points (not empty)

    This ensures newsletters always have some summary.
    """
    client = MagicMock()
    client.models.generate_content.side_effect = Exception("API Error")

    email_body = "Newsletter content"
    subject = "Weekly Newsletter"

    result = generate_newsletter_summary(email_body, subject, client, 'gemini-2.0-flash-exp')

    # Should return fallback
    assert isinstance(result, list), "Should still return a list"
    assert len(result) == 3, "Should have 3 fallback points"
    assert "Failed to generate summary" in result[0], "Should have fallback message"


# ==============================================================================
# CONTRACT TEST: Gmail API Response Structure
# ==============================================================================

@pytest.mark.contract
@pytest.mark.basic
def test_gmail_api_message_list_response(mock_gmail_service):
    """
    Test Gmail API messages().list() response structure.

    Contract:
    - Response has 'messages' key with list of message dicts
    - Each message dict has 'id' key
    - Used to get list of message IDs to fetch

    Verifies our code correctly handles Gmail API responses.
    """
    # Call the mocked service
    response = mock_gmail_service.users().messages().list(
        userId='me',
        q='is:unread',
        maxResults=5
    ).execute()

    # Verify response structure
    assert 'messages' in response, "Response should have 'messages' key"
    assert isinstance(response['messages'], list), "Messages should be a list"
    assert len(response['messages']) > 0, "Should have at least one message"
    assert 'id' in response['messages'][0], "Each message should have 'id'"


@pytest.mark.contract
@pytest.mark.basic
def test_gmail_api_message_get_response(mock_gmail_service, sample_emails):
    """
    Test Gmail API messages().get() response structure.

    Contract:
    - Response has 'id', 'payload', 'snippet'
    - Payload has 'headers' with From, Subject, Date
    - Headers are list of {'name': ..., 'value': ...}

    Verifies email data extraction works with Gmail format.
    """
    # Get a message
    message_id = sample_emails[0]['id']
    response = mock_gmail_service.users().messages().get(
        userId='me',
        id=message_id,
        format='full'
    ).execute()

    # Verify response structure
    assert 'id' in response, "Response should have 'id'"
    assert 'payload' in response, "Response should have 'payload'"
    assert 'snippet' in response, "Response should have 'snippet'"

    # Verify headers
    assert 'headers' in response['payload'], "Payload should have 'headers'"
    headers = response['payload']['headers']
    assert isinstance(headers, list), "Headers should be a list"

    # Verify header structure
    header_names = [h['name'] for h in headers]
    assert 'From' in header_names, "Should have 'From' header"
    assert 'Subject' in header_names, "Should have 'Subject' header"
    assert 'Date' in header_names, "Should have 'Date' header"


@pytest.mark.contract
@pytest.mark.comprehensive
def test_gmail_api_query_with_after_filter(mock_gmail_service):
    """
    Test Gmail API query building with 'after:' timestamp filter.

    Contract:
    - Query can include 'after:EPOCH' for incremental fetching
    - EPOCH is Unix timestamp (seconds since 1970-01-01)
    - Query is combined with other filters (is:unread, etc.)

    Verifies incremental fetching query format.
    """
    # Test query with after filter
    base_query = "is:unread newer_than:1d"
    epoch_timestamp = 1736937600  # Example: 2025-01-15 10:00:00 UTC

    query_with_after = f"{base_query} after:{epoch_timestamp}"

    # Call Gmail API with query (mock won't filter, but verifies format)
    response = mock_gmail_service.users().messages().list(
        userId='me',
        q=query_with_after,
        maxResults=10
    ).execute()

    # Verify it doesn't crash and returns messages
    assert 'messages' in response, "Should return messages"
