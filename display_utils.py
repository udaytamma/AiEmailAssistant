"""
Display Utility Functions
Handles displaying categorized emails and generating/displaying daily digests
"""

import time
from collections import defaultdict
from email_utils import extract_email_body
from gemini_utils import generate_newsletter_summary, generate_category_summary


def display_categorized_summary(categorized_emails):
    """
    Display categorized emails organized by category.

    Shows all emails grouped by their assigned category (Need-Action, FYI,
    Newsletter, Marketing, SPAM) with subject, sender, action, and summary.

    Args:
        categorized_emails: List of categorized email dictionaries

    Output:
        Prints formatted summary to console with:
        - Email count per category
        - Email details (subject, sender, action, summary)
        - Visual separators for readability
    """
    # Group emails by category using defaultdict
    categories = defaultdict(list)

    for email in categorized_emails:
        categories[email['category']].append(email)

    print("\n" + "=" * 80)
    print("EMAIL CATEGORIZATION SUMMARY")
    print("=" * 80 + "\n")

    # Display each category
    for category, emails in categories.items():
        print(f"\n### {category.upper()} ({len(emails)} emails)")
        print("-" * 80)
        for email in emails:
            print(f"  • {email['subject']}")
            print(f"    From: {email['from']}")
            print(f"    Action: {email['action_item']}")
            print(f"    Summary: {email['summary']}")
            print()

    print("=" * 80)


def generate_daily_digest(categorized_emails, service, model, cache=None):
    """
    Generate comprehensive Daily Digest with AI-powered summaries.

    Creates detailed digest with:
    1. Need-Action category summary (consolidated bullet points)
    2. FYI category summary (consolidated bullet points)
    3. Newsletter summaries (3 bullets each)

    All summaries are cached to reduce API calls on subsequent runs.

    Args:
        categorized_emails: List of categorized email dictionaries
        service: Authenticated Gmail API service instance
        model: Initialized Gemini model instance
        cache: CacheManager instance for caching summaries (optional)

    Returns:
        dict: Daily digest with structure:
            - need_action: {emails: [...], summary: [...]}
            - fyi: {emails: [...], summary: [...]}
            - newsletters: [{subject, from, summary_points}, ...]

    Note:
        - Checks cache before generating summaries
        - Creates cache keys based on email IDs for category summaries
        - Rate-limits API calls to avoid quota errors
        - Saves cache after generating new summaries
    """
    print("\n" + "=" * 80)
    print("GENERATING DAILY DIGEST")
    print("=" * 80 + "\n")

    # Group emails by category
    categories = defaultdict(list)
    for email in categorized_emails:
        categories[email['category']].append(email)

    # Initialize digest structure
    digest = {
        'need_action': {'emails': categories.get('Need-Action', []), 'summary': []},
        'fyi': {'emails': categories.get('FYI', []), 'summary': []},
        'newsletters': []
    }

    # Rate limiting configuration
    requests_per_minute = 10
    delay_between_requests = 60 / requests_per_minute + 1

    # === Generate Need-Action Summary ===
    if digest['need_action']['emails']:
        print(f"📋 Generating summary for {len(digest['need_action']['emails'])} Need-Action emails...")

        # Create cache key based on sorted email IDs in category
        need_action_cache_key = 'category_summary_need_action_' + '_'.join(
            sorted([e['id'] for e in digest['need_action']['emails']])
        )

        # Check cache first
        if cache and cache.has(need_action_cache_key):
            cached_data = cache.get(need_action_cache_key)
            digest['need_action']['summary'] = cached_data.get('summary', [])
            print(f"  ✓ Using cached Need-Action category summary")
        else:
            # Generate new summary via Gemini
            digest['need_action']['summary'] = generate_category_summary(
                digest['need_action']['emails'],
                'Need-Action',
                model
            )

            # Cache the result
            if cache:
                cache.set(need_action_cache_key, {'summary': digest['need_action']['summary']})

            time.sleep(delay_between_requests)

    # === Generate FYI Summary ===
    if digest['fyi']['emails']:
        print(f"📋 Generating summary for {len(digest['fyi']['emails'])} FYI emails...")

        # Create cache key based on sorted email IDs
        fyi_cache_key = 'category_summary_fyi_' + '_'.join(
            sorted([e['id'] for e in digest['fyi']['emails']])
        )

        # Check cache first
        if cache and cache.has(fyi_cache_key):
            cached_data = cache.get(fyi_cache_key)
            digest['fyi']['summary'] = cached_data.get('summary', [])
            print(f"  ✓ Using cached FYI category summary")
        else:
            # Generate new summary via Gemini
            digest['fyi']['summary'] = generate_category_summary(
                digest['fyi']['emails'],
                'FYI',
                model
            )

            # Cache the result
            if cache:
                cache.set(fyi_cache_key, {'summary': digest['fyi']['summary']})

            time.sleep(delay_between_requests)

    # === Generate Newsletter Summaries ===
    newsletter_emails = categories.get('Newsletter', [])
    if newsletter_emails:
        print(f"📰 Generating detailed summaries for {len(newsletter_emails)} Newsletters...\n")

        for idx, email in enumerate(newsletter_emails, 1):
            print(f"  Processing Newsletter {idx}/{len(newsletter_emails)}: {email['subject'][:50]}...")

            # Check cache for newsletter summary
            summary_points = None
            if cache and cache.has(email['id']):
                cached_data = cache.get(email['id'])
                if 'newsletter_summary' in cached_data:
                    summary_points = cached_data['newsletter_summary']
                    print(f"  ✓ Using cached newsletter summary")

            # Generate summary if not cached
            if not summary_points:
                # Extract full email body
                email_body = extract_email_body(service, email['id'])

                # Generate 3-bullet summary via Gemini
                summary_points = generate_newsletter_summary(email_body, email['subject'], model)

                # Cache the newsletter summary
                if cache:
                    cached_data = cache.get(email['id']) or {}
                    cached_data['newsletter_summary'] = summary_points
                    cache.set(email['id'], cached_data)

                # Rate limit only when making new API calls
                if idx < len(newsletter_emails):
                    print(f"  ⏳ Waiting {delay_between_requests:.0f} seconds...")
                    time.sleep(delay_between_requests)

            # Add newsletter to digest
            digest['newsletters'].append({
                'subject': email['subject'],
                'from': email['from'],
                'summary_points': summary_points
            })

    print("\n✅ Daily Digest generation complete!\n")
    return digest


def display_daily_digest(digest):
    """
    Display Daily Digest in beautiful formatted output.

    Shows three organized sections:
    1. Need Action (urgent items requiring response)
    2. FYI (informational items)
    3. Newsletters & Updates (detailed summaries)

    Args:
        digest: Digest dictionary from generate_daily_digest()

    Output:
        Prints formatted digest to console with:
        - Unicode box drawing characters for header
        - Section headers with email counts
        - Bullet points for summaries
        - Total email count footer
    """
    # Header with box drawing
    print("\n" + "╔" + "=" * 78 + "╗")
    print("║" + " " * 25 + "📧 DAILY EMAIL DIGEST 📧" + " " * 28 + "║")
    print("╚" + "=" * 78 + "╝\n")

    # Need-Action Section
    if digest['need_action']['emails']:
        print("🔴 NEED ACTION" + " " * 20 + f"({len(digest['need_action']['emails'])} emails)")
        print("─" * 80)
        if digest['need_action']['summary']:
            for point in digest['need_action']['summary']:
                print(f"  • {point}")
        else:
            # Fallback: show email subjects if summary failed
            for email in digest['need_action']['emails']:
                print(f"  • {email['subject']}")
        print()

    # FYI Section
    if digest['fyi']['emails']:
        print("ℹ️  FYI - FOR YOUR INFORMATION" + " " * 5 + f"({len(digest['fyi']['emails'])} emails)")
        print("─" * 80)
        if digest['fyi']['summary']:
            for point in digest['fyi']['summary']:
                print(f"  • {point}")
        else:
            # Fallback: show email subjects if summary failed
            for email in digest['fyi']['emails']:
                print(f"  • {email['subject']}")
        print()

    # Newsletter Section
    if digest['newsletters']:
        print("📰 NEWSLETTERS & UPDATES" + " " * 12 + f"({len(digest['newsletters'])} newsletters)")
        print("─" * 80)

        for idx, newsletter in enumerate(digest['newsletters'], 1):
            print(f"\n  [{idx}] {newsletter['subject']}")
            print(f"      From: {newsletter['from']}")
            print("      Summary:")
            for point in newsletter['summary_points']:
                print(f"        • {point}")
            print()

    # Footer
    print("─" * 80)
    total_emails = (len(digest['need_action']['emails']) +
                   len(digest['fyi']['emails']) +
                   len(digest['newsletters']))
    print(f"Total emails processed: {total_emails}")
    print("=" * 80 + "\n")
