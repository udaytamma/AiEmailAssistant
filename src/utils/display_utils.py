"""
Display Utility Functions
Handles displaying categorized emails and generating/displaying daily digests
with comprehensive error handling, logging, and metrics tracking.
"""

import time
import traceback
from collections import defaultdict
from typing import List, Dict, Any, Optional

from .email_utils import extract_email_body
from .gemini_utils import generate_newsletter_summary, generate_category_summary
from .logger_utils import setup_logger, log_exception, log_performance
from .metrics_utils import get_metrics_tracker

# Initialize logger
logger = setup_logger(__name__)


def display_categorized_summary(categorized_emails: List[Dict[str, Any]]) -> None:
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
    logger.info(f"Displaying categorized summary for {len(categorized_emails)} emails")

    try:
        # Group emails by category using defaultdict
        categories = defaultdict(list)

        for email in categorized_emails:
            category = email.get('category', 'Unknown')
            categories[category].append(email)

        print("\n" + "=" * 80)
        print("EMAIL CATEGORIZATION SUMMARY")
        print("=" * 80 + "\n")

        # Display each category
        for category, emails in categories.items():
            print(f"\n### {category.upper()} ({len(emails)} emails)")
            print("-" * 80)
            for email in emails:
                print(f"  • {email.get('subject', 'No Subject')}")
                print(f"    From: {email.get('from', 'Unknown')}")
                print(f"    Action: {email.get('action_item', 'None')}")
                print(f"    Summary: {email.get('summary', 'No summary')}")
                print()

        print("=" * 80)
        logger.info(f"Successfully displayed {len(categories)} categories")

    except Exception as e:
        log_exception(logger, e, "Error displaying categorized summary")
        metrics = get_metrics_tracker()
        metrics.record_error(__name__, type(e).__name__, str(e), traceback.format_exc())
        print(f"⚠️  Error displaying categorized summary: {e}")


def generate_daily_digest(
    categorized_emails: List[Dict[str, Any]],
    service: Any,
    client: Any,
    model_name: str,
    cache: Optional[Any] = None,
    new_emails_count: int = 0
) -> Dict[str, Any]:
    """
    Generate comprehensive Daily Digest with AI-powered summaries.

    Creates detailed digest with:
    1. Need-Action category summary (consolidated bullet points)
    2. FYI category summary (consolidated bullet points)
    3. Newsletter summaries (3 bullets each)

    All summaries are cached to reduce API calls on subsequent runs.
    Regenerates category summaries when new emails are added.

    Args:
        categorized_emails: List of categorized email dictionaries
        service: Authenticated Gmail API service instance
        client: Initialized Gemini client instance (google.genai.Client)
        model_name: Name of the Gemini model to use
        cache: CacheManager instance for caching summaries (optional)
        new_emails_count: Number of new emails processed (triggers summary regeneration)

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
    logger.info(f"Generating daily digest for {len(categorized_emails)} emails")
    start_time = time.time()
    metrics = get_metrics_tracker()

    print("\n" + "=" * 80)
    print("GENERATING DAILY DIGEST")
    print("=" * 80 + "\n")

    try:
        # Group emails by category
        categories = defaultdict(list)
        for email in categorized_emails:
            category = email.get('category', 'Unknown')
            categories[category].append(email)

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
            try:
                logger.info(f"Generating summary for {len(digest['need_action']['emails'])} Need-Action emails")
                print(f"📋 Generating summary for {len(digest['need_action']['emails'])} Need-Action emails...")

                # Create cache key based on sorted email IDs in category
                need_action_cache_key = 'category_summary_need_action_' + '_'.join(
                    sorted([e['id'] for e in digest['need_action']['emails']])
                )

                # Check cache first (skip if new emails added)
                should_regenerate = new_emails_count > 0
                if cache and cache.has(need_action_cache_key) and not should_regenerate:
                    cached_data = cache.get(need_action_cache_key)
                    digest['need_action']['summary'] = cached_data.get('summary', [])
                    logger.info("Using cached Need-Action category summary")
                    print(f"  ✓ Using cached Need-Action category summary")
                    metrics.record_cache_operation('GET', 'category_summary', True)
                else:
                    # Generate new summary via Gemini
                    if should_regenerate:
                        logger.info("Regenerating Need-Action summary due to new emails")
                        print(f"  🔄 Regenerating summary with new emails...")
                    metrics.record_cache_operation('GET', 'category_summary', False)
                    digest['need_action']['summary'] = generate_category_summary(
                        digest['need_action']['emails'],
                        'Need-Action',
                        client,
                        model_name
                    )

                    # Cache the result
                    if cache:
                        cache.set(need_action_cache_key, {'summary': digest['need_action']['summary']})
                        metrics.record_cache_operation('SET', 'category_summary', None)
                        logger.debug("Cached Need-Action summary")

                    time.sleep(delay_between_requests)

            except Exception as e:
                log_exception(logger, e, "Error generating Need-Action summary")
                metrics.record_error(__name__, type(e).__name__, f"Need-Action summary failed: {e}")
                digest['need_action']['summary'] = [
                    f"{email['subject']}" for email in digest['need_action']['emails'][:5]
                ]

        # === Generate FYI Summary ===
        if digest['fyi']['emails']:
            try:
                logger.info(f"Generating summary for {len(digest['fyi']['emails'])} FYI emails")
                print(f"📋 Generating summary for {len(digest['fyi']['emails'])} FYI emails...")

                # Create cache key based on sorted email IDs
                fyi_cache_key = 'category_summary_fyi_' + '_'.join(
                    sorted([e['id'] for e in digest['fyi']['emails']])
                )

                # Check cache first (skip if new emails added)
                should_regenerate = new_emails_count > 0
                if cache and cache.has(fyi_cache_key) and not should_regenerate:
                    cached_data = cache.get(fyi_cache_key)
                    digest['fyi']['summary'] = cached_data.get('summary', [])
                    logger.info("Using cached FYI category summary")
                    print(f"  ✓ Using cached FYI category summary")
                    metrics.record_cache_operation('GET', 'category_summary', True)
                else:
                    # Generate new summary via Gemini
                    if should_regenerate:
                        logger.info("Regenerating FYI summary due to new emails")
                        print(f"  🔄 Regenerating summary with new emails...")
                    metrics.record_cache_operation('GET', 'category_summary', False)
                    digest['fyi']['summary'] = generate_category_summary(
                        digest['fyi']['emails'],
                        'FYI',
                        client,
                        model_name
                    )

                    # Cache the result
                    if cache:
                        cache.set(fyi_cache_key, {'summary': digest['fyi']['summary']})
                        metrics.record_cache_operation('SET', 'category_summary', None)
                        logger.debug("Cached FYI summary")

                    time.sleep(delay_between_requests)

            except Exception as e:
                log_exception(logger, e, "Error generating FYI summary")
                metrics.record_error(__name__, type(e).__name__, f"FYI summary failed: {e}")
                digest['fyi']['summary'] = [
                    f"{email['subject']}" for email in digest['fyi']['emails'][:5]
                ]

        # === Generate Newsletter Summaries ===
        newsletter_emails = categories.get('Newsletter', [])
        if newsletter_emails:
            try:
                logger.info(f"Generating detailed summaries for {len(newsletter_emails)} Newsletters")
                print(f"📰 Generating detailed summaries for {len(newsletter_emails)} Newsletters...\n")

                for idx, email in enumerate(newsletter_emails, 1):
                    try:
                        print(f"  Processing Newsletter {idx}/{len(newsletter_emails)}: {email['subject'][:50]}...")

                        # Check cache for newsletter summary
                        summary_points = None
                        if cache and cache.has(email['id']):
                            cached_data = cache.get(email['id'])
                            if 'newsletter_summary' in cached_data:
                                summary_points = cached_data['newsletter_summary']
                                logger.debug(f"Using cached newsletter summary for {email['id']}")
                                print(f"  ✓ Using cached newsletter summary")
                                metrics.record_cache_operation('GET', 'newsletter_summary', True)

                        # Generate summary if not cached
                        if not summary_points:
                            metrics.record_cache_operation('GET', 'newsletter_summary', False)

                            # Extract full email body
                            email_body = extract_email_body(service, email['id'])

                            # Generate 3-bullet summary via Gemini
                            summary_points = generate_newsletter_summary(email_body, email['subject'], client, model_name)

                            # Cache the newsletter summary
                            if cache:
                                cached_data = cache.get(email['id']) or {}
                                cached_data['newsletter_summary'] = summary_points
                                cache.set(email['id'], cached_data)
                                metrics.record_cache_operation('SET', 'newsletter_summary', None)
                                logger.debug(f"Cached newsletter summary for {email['id']}")

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

                    except Exception as e:
                        log_exception(logger, e, f"Error processing newsletter {idx}")
                        metrics.record_error(__name__, type(e).__name__, f"Newsletter processing failed: {e}")
                        # Add fallback newsletter entry
                        digest['newsletters'].append({
                            'subject': email['subject'],
                            'from': email['from'],
                            'summary_points': [
                                "Failed to generate summary",
                                "Please check the original email",
                                "Error occurred during processing"
                            ]
                        })

            except Exception as e:
                log_exception(logger, e, "Error processing newsletters")
                metrics.record_error(__name__, type(e).__name__, f"Newsletter batch processing failed: {e}")

        elapsed = time.time() - start_time
        log_performance(logger, "Daily Digest Generation", elapsed)
        logger.info(f"Daily digest generation complete in {elapsed:.2f}s")

        print("\n✅ Daily Digest generation complete!\n")
        return digest

    except Exception as e:
        elapsed = time.time() - start_time
        log_exception(logger, e, "Daily digest generation failed")
        metrics.record_error(__name__, type(e).__name__, str(e), traceback.format_exc())
        print(f"⚠️  Error generating daily digest: {e}")

        # Return minimal digest structure
        return {
            'need_action': {'emails': [], 'summary': []},
            'fyi': {'emails': [], 'summary': []},
            'newsletters': []
        }


def display_daily_digest(digest: Dict[str, Any]) -> None:
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
    logger.info("Displaying daily digest")

    try:
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
                    print(f"  • {email.get('subject', 'No Subject')}")
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
                    print(f"  • {email.get('subject', 'No Subject')}")
            print()

        # Newsletter Section
        if digest['newsletters']:
            print("📰 NEWSLETTERS & UPDATES" + " " * 12 + f"({len(digest['newsletters'])} newsletters)")
            print("─" * 80)

            for idx, newsletter in enumerate(digest['newsletters'], 1):
                print(f"\n  [{idx}] {newsletter.get('subject', 'No Subject')}")
                print(f"      From: {newsletter.get('from', 'Unknown')}")
                print("      Summary:")
                for point in newsletter.get('summary_points', []):
                    print(f"        • {point}")
                print()

        # Footer
        print("─" * 80)
        total_emails = (len(digest['need_action']['emails']) +
                       len(digest['fyi']['emails']) +
                       len(digest['newsletters']))
        print(f"Total emails processed: {total_emails}")
        print()

        logger.info(f"Successfully displayed digest with {total_emails} total emails")

    except Exception as e:
        log_exception(logger, e, "Error displaying daily digest")
        metrics = get_metrics_tracker()
        metrics.record_error(__name__, type(e).__name__, str(e), traceback.format_exc())
        print(f"⚠️  Error displaying daily digest: {e}")
