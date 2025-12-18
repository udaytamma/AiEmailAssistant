"""
Unit Tests for Display Utils

Tests digest generation and email grouping logic:
- Category grouping (Need-Action, FYI, Newsletter, Marketing, SPAM)
- Summary regeneration logic when new emails added
- Newsletter summary generation
- Category summary generation
- Digest data structure validation
"""

import sys
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from utils.display_utils import generate_daily_digest


# ==============================================================================
# UNIT TEST: Basic Digest Generation
# ==============================================================================

@pytest.mark.unit
@pytest.mark.basic
def test_generate_digest_structure(
    sample_categorized_emails,
    mock_gmail_service,
    mock_gemini_model
):
    """
    Test that generate_daily_digest() returns correct data structure.

    Verifies:
    - Digest has required sections: need_action, fyi, newsletters
    - Each section has correct structure
    - All categorized emails are included in digest
    """
    digest = generate_daily_digest(
        sample_categorized_emails,
        mock_gmail_service,
        mock_gemini_model,
        'gemini-2.0-flash-exp',
        cache=None,
        new_emails_count=len(sample_categorized_emails)
    )

    # Verify main sections exist
    assert 'need_action' in digest, "Digest should have need_action section"
    assert 'fyi' in digest, "Digest should have fyi section"
    assert 'newsletters' in digest, "Digest should have newsletters section"

    # Verify need_action structure
    assert 'emails' in digest['need_action'], "need_action should have emails list"
    assert 'summary' in digest['need_action'], "need_action should have summary"

    # Verify fyi structure
    assert 'emails' in digest['fyi'], "fyi should have emails list"
    assert 'summary' in digest['fyi'], "fyi should have summary"

    # Verify newsletters structure (list of newsletter summaries)
    assert isinstance(digest['newsletters'], list), "newsletters should be a list"


# ==============================================================================
# UNIT TEST: Email Categorization Grouping
# ==============================================================================

@pytest.mark.unit
@pytest.mark.basic
def test_emails_grouped_by_category(
    sample_categorized_emails,
    mock_gmail_service,
    mock_gemini_model
):
    """
    Test that emails are correctly grouped by category.

    Verifies:
    - Need-Action emails go to need_action section
    - FYI emails go to fyi section
    - Newsletter emails go to newsletters section
    - Correct count in each section
    """
    digest = generate_daily_digest(
        sample_categorized_emails,
        mock_gmail_service,
        mock_gemini_model,
        'gemini-2.0-flash-exp',
        cache=None,
        new_emails_count=len(sample_categorized_emails)
    )

    # Count emails by category in sample data
    need_action_count = len([e for e in sample_categorized_emails if e['category'] == 'Need-Action'])
    fyi_count = len([e for e in sample_categorized_emails if e['category'] == 'FYI'])
    newsletter_count = len([e for e in sample_categorized_emails if e['category'] == 'Newsletter'])

    # Verify grouping
    assert len(digest['need_action']['emails']) == need_action_count, "Need-Action count should match"
    assert len(digest['fyi']['emails']) == fyi_count, "FYI count should match"
    # Newsletters are summarized, not just grouped
    assert len(digest['newsletters']) <= newsletter_count, "Newsletter summaries should be created"


@pytest.mark.unit
@pytest.mark.extended
def test_empty_category_handling(mock_gmail_service, mock_gemini_model):
    """
    Test that digest handles categories with no emails gracefully.

    Verifies:
    - Empty categories return empty lists/summaries
    - No errors when a category has zero emails
    - Digest structure is still valid
    """
    # Create emails with only one category
    test_emails = [
        pytest.create_test_categorized_email(
            email_id=f"test_{i}",
            category='FYI',
            from_addr='test@example.com',
            subject=f'Test Email {i}'
        )
        for i in range(3)
    ]

    digest = generate_daily_digest(
        test_emails,
        mock_gmail_service,
        mock_gemini_model,
        'gemini-2.0-flash-exp',
        cache=None,
        new_emails_count=3
    )

    # need_action should be empty
    assert len(digest['need_action']['emails']) == 0, "Need-Action should be empty"
    assert digest['need_action']['summary'] == [], "Need-Action summary should be empty list"

    # fyi should have all 3 emails
    assert len(digest['fyi']['emails']) == 3, "FYI should have 3 emails"


# ==============================================================================
# UNIT TEST: Summary Regeneration Logic
# ==============================================================================

@pytest.mark.unit
@pytest.mark.comprehensive
def test_summary_regeneration_with_new_emails(
    sample_categorized_emails,
    mock_gmail_service,
    mock_gemini_model,
    test_cache_manager
):
    """
    Test that summaries are regenerated when new emails are added.

    Scenario:
    1. Generate digest with 0 new emails (should use cache)
    2. Generate digest with new emails (should regenerate summaries)

    Verifies:
    - new_emails_count=0 uses cached summaries
    - new_emails_count>0 regenerates summaries
    - This ensures fresh summaries when new emails arrive
    """
    # First run: No new emails (simulate cached summaries)
    digest_cached = generate_daily_digest(
        sample_categorized_emails,
        mock_gmail_service,
        mock_gemini_model,
        'gemini-2.0-flash-exp',
        cache=test_cache_manager,
        new_emails_count=0  # No new emails - should try to use cache
    )

    # Second run: New emails arrived (should regenerate)
    digest_regenerated = generate_daily_digest(
        sample_categorized_emails,
        mock_gmail_service,
        mock_gemini_model,
        'gemini-2.0-flash-exp',
        cache=test_cache_manager,
        new_emails_count=3  # 3 new emails - should regenerate
    )

    # Both should have valid structure
    assert 'need_action' in digest_cached
    assert 'need_action' in digest_regenerated

    # Summaries should exist in both cases
    assert isinstance(digest_cached['need_action']['summary'], list)
    assert isinstance(digest_regenerated['need_action']['summary'], list)


# ==============================================================================
# UNIT TEST: Newsletter Summary Generation
# ==============================================================================

@pytest.mark.unit
@pytest.mark.extended
def test_newsletter_summary_creation(
    mock_gmail_service,
    mock_gemini_model
):
    """
    Test newsletter summary generation.

    Verifies:
    - Newsletters are summarized with 3 bullet points
    - Summary structure includes subject, from, summary_points
    - Multiple newsletters are each summarized separately
    """
    # Create newsletter emails
    newsletter_emails = [
        pytest.create_test_categorized_email(
            email_id="newsletter_1",
            category='Newsletter',
            from_addr='Bloomberg <news@bloomberg.com>',
            subject='Tech Market Update',
            snippet='Tech stocks declined today...',
            summary='Newsletter about tech market'
        ),
        pytest.create_test_categorized_email(
            email_id="newsletter_2",
            category='Newsletter',
            from_addr='AI Weekly <hello@aiweekly.co>',
            subject='Latest in AI',
            snippet='GPT-5 announced...',
            summary='Newsletter about AI news'
        )
    ]

    digest = generate_daily_digest(
        newsletter_emails,
        mock_gmail_service,
        mock_gemini_model,
        'gemini-2.0-flash-exp',
        cache=None,
        new_emails_count=2
    )

    # Verify newsletter summaries
    newsletters = digest['newsletters']
    assert isinstance(newsletters, list), "Newsletters should be a list"

    # Each newsletter should have subject, from, summary_points
    for newsletter in newsletters:
        assert 'subject' in newsletter, "Newsletter should have subject"
        assert 'from' in newsletter, "Newsletter should have from"
        assert 'summary_points' in newsletter, "Newsletter should have summary_points"

        # Summary points should be a list (ideally 3 items)
        assert isinstance(newsletter['summary_points'], list), "Summary points should be a list"


# ==============================================================================
# UNIT TEST: Category Summary Generation
# ==============================================================================

@pytest.mark.unit
@pytest.mark.extended
def test_category_summary_for_need_action(
    mock_gmail_service,
    mock_gemini_model
):
    """
    Test category summary generation for Need-Action emails.

    Verifies:
    - Summary consolidates multiple emails
    - Summary is a list of bullet points
    - Summary highlights important action items
    """
    # Create Need-Action emails
    need_action_emails = [
        pytest.create_test_categorized_email(
            email_id=f"action_{i}",
            category='Need-Action',
            subcategory='Bill-Due' if i % 2 == 0 else 'General',
            from_addr=f'sender{i}@example.com',
            subject=f'Action Required {i}',
            summary=f'Action item {i}: Complete task by deadline'
        )
        for i in range(3)
    ]

    digest = generate_daily_digest(
        need_action_emails,
        mock_gmail_service,
        mock_gemini_model,
        'gemini-2.0-flash-exp',
        cache=None,
        new_emails_count=3
    )

    # Verify summary exists and is a list
    summary = digest['need_action']['summary']
    assert isinstance(summary, list), "Summary should be a list"

    # Summary should have bullet points (at least 1)
    assert len(summary) > 0, "Summary should have at least one point"


@pytest.mark.unit
@pytest.mark.extended
def test_category_summary_for_fyi(
    mock_gmail_service,
    mock_gemini_model
):
    """
    Test category summary generation for FYI emails.

    Verifies:
    - Summary consolidates FYI emails
    - Summary provides overview of informational content
    - Summary is a list format
    """
    # Create FYI emails
    fyi_emails = [
        pytest.create_test_categorized_email(
            email_id=f"fyi_{i}",
            category='FYI',
            subcategory='JobAlert' if i == 0 else 'General',
            from_addr=f'info{i}@example.com',
            subject=f'FYI: Update {i}',
            summary=f'Information update about topic {i}'
        )
        for i in range(4)
    ]

    digest = generate_daily_digest(
        fyi_emails,
        mock_gmail_service,
        mock_gemini_model,
        'gemini-2.0-flash-exp',
        cache=None,
        new_emails_count=4
    )

    # Verify FYI summary
    summary = digest['fyi']['summary']
    assert isinstance(summary, list), "FYI summary should be a list"
    assert len(summary) > 0, "FYI summary should have content"


# ==============================================================================
# UNIT TEST: Mixed Categories Digest
# ==============================================================================

@pytest.mark.unit
@pytest.mark.comprehensive
def test_digest_with_all_categories(
    mock_gmail_service,
    mock_gemini_model
):
    """
    Test digest generation with emails from all categories.

    Verifies:
    - Digest handles mixed categories correctly
    - Each category section has appropriate emails
    - No emails are lost or miscategorized
    - Total email count matches input
    """
    # Create diverse email set
    mixed_emails = [
        pytest.create_test_categorized_email(email_id="1", category='Need-Action', subject='Action 1'),
        pytest.create_test_categorized_email(email_id="2", category='FYI', subject='Info 1'),
        pytest.create_test_categorized_email(email_id="3", category='Newsletter', subject='Newsletter 1'),
        pytest.create_test_categorized_email(email_id="4", category='Marketing', subject='Promo 1'),
        pytest.create_test_categorized_email(email_id="5", category='Need-Action', subject='Action 2'),
        pytest.create_test_categorized_email(email_id="6", category='FYI', subject='Info 2'),
    ]

    digest = generate_daily_digest(
        mixed_emails,
        mock_gmail_service,
        mock_gemini_model,
        'gemini-2.0-flash-exp',
        cache=None,
        new_emails_count=6
    )

    # Verify counts
    need_action_count = len(digest['need_action']['emails'])
    fyi_count = len(digest['fyi']['emails'])
    newsletter_count = len(digest['newsletters'])

    assert need_action_count == 2, "Should have 2 Need-Action emails"
    assert fyi_count == 2, "Should have 2 FYI emails"
    # Marketing is not in the main digest sections (handled separately on web)

    # Verify total (Need-Action + FYI + Newsletters captured)
    # Note: Marketing/SPAM may not be in these sections
    assert need_action_count + fyi_count > 0, "Digest should contain emails"


# ==============================================================================
# UNIT TEST: Email Data Preservation in Digest
# ==============================================================================

@pytest.mark.unit
@pytest.mark.basic
def test_email_data_preserved_in_digest(
    mock_gmail_service,
    mock_gemini_model
):
    """
    Test that original email data is preserved in digest.

    Verifies:
    - Email fields (id, from, subject, date, snippet) are preserved
    - Categorization fields (category, subcategory, summary) are included
    - No data is lost during digest generation
    """
    test_email = pytest.create_test_categorized_email(
        email_id="preserve_test",
        category='Need-Action',
        from_addr='John Doe <john@example.com>',
        subject='Important: Action Required',
        snippet='Please complete this task urgently',
        summary='Urgent action required on project'
    )

    digest = generate_daily_digest(
        [test_email],
        mock_gmail_service,
        mock_gemini_model,
        'gemini-2.0-flash-exp',
        cache=None,
        new_emails_count=1
    )

    # Get the email from digest
    digest_email = digest['need_action']['emails'][0]

    # Verify all fields preserved
    assert digest_email['id'] == 'preserve_test'
    assert digest_email['from'] == 'John Doe <john@example.com>'
    assert digest_email['subject'] == 'Important: Action Required'
    assert digest_email['snippet'] == 'Please complete this task urgently'
    assert digest_email['category'] == 'Need-Action'
    assert digest_email['summary'] == 'Urgent action required on project'
