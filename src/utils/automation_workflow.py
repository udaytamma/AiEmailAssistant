"""
Automation Workflow
Orchestrates automated actions for categorized emails with user confirmation.
"""

import traceback
from typing import Dict, Any, List, Optional

from .automation_utils import (
    extract_event_details,
    check_autopay_scheduled,
    verify_spam_and_extract_unsubscribe,
    create_calendar_event,
    create_task,
    send_unsubscribe_request
)
from .logger_utils import setup_logger, log_exception
from .metrics_utils import get_metrics_tracker

# Initialize logger
logger = setup_logger(__name__)


def process_need_action_automations(
    emails: List[Dict[str, Any]],
    gmail_service: Any,
    calendar_service: Any,
    tasks_service: Any,
    gemini_client: Any,
    model_name: str
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Process Need-Action emails for automated calendar events and tasks.

    Args:
        emails: List of Need-Action categorized emails
        gmail_service: Authenticated Gmail API service
        calendar_service: Authenticated Google Calendar API service
        tasks_service: Authenticated Google Tasks API service
        gemini_client: Initialized Gemini client
        model_name: Gemini model name

    Returns:
        dict: Processing results with keys:
            - calendar_events: List of events to create (pending user confirmation)
            - tasks: List of tasks to create (pending user confirmation)
    """
    logger.info(f"Processing {len(emails)} Need-Action emails for automation")
    metrics = get_metrics_tracker()

    results = {
        'calendar_events': [],
        'tasks': []
    }

    try:
        for email in emails:
            # Check for calendar events (appointments, birthdays)
            logger.debug(f"Checking for calendar event: {email.get('subject')[:50]}")
            event_details = extract_event_details(email, gemini_client, model_name)

            if event_details and event_details.get('has_event') and event_details.get('date'):
                results['calendar_events'].append({
                    'email': email,
                    'event_details': event_details
                })
                logger.info(f"Found calendar event: {event_details.get('title')}")

            # Check for bill-due without autopay
            if 'bill' in email.get('subject', '').lower() or 'payment' in email.get('subject', '').lower():
                logger.debug(f"Checking for bill-due task: {email.get('subject')[:50]}")
                autopay_info = check_autopay_scheduled(email, gemini_client, model_name)

                if autopay_info and not autopay_info.get('has_autopay'):
                    results['tasks'].append({
                        'email': email,
                        'task_details': autopay_info
                    })
                    logger.info(f"Found bill-due task (no autopay): {email.get('subject')[:50]}")

        logger.info(f"Automation processing complete: {len(results['calendar_events'])} events, {len(results['tasks'])} tasks")
        return results

    except Exception as e:
        log_exception(logger, e, "Error processing Need-Action automations")
        metrics.record_error(__name__, type(e).__name__, str(e), traceback.format_exc())
        return results


def process_spam_automations(
    emails: List[Dict[str, Any]],
    gmail_service: Any,
    gemini_client: Any,
    model_name: str
) -> List[Dict[str, Any]]:
    """
    Process SPAM emails for unsubscribe verification.

    Args:
        emails: List of SPAM categorized emails
        gmail_service: Authenticated Gmail API service
        gemini_client: Initialized Gemini client
        model_name: Gemini model name

    Returns:
        list: Unsubscribe candidates (pending user confirmation)
    """
    logger.info(f"Processing {len(emails)} SPAM emails for unsubscribe automation")
    metrics = get_metrics_tracker()

    unsubscribe_candidates = []

    try:
        for email in emails:
            logger.debug(f"Verifying SPAM: {email.get('subject')[:50]}")
            spam_info = verify_spam_and_extract_unsubscribe(email, gemini_client, model_name)

            if spam_info and spam_info.get('is_spam') and spam_info.get('confidence') in ['high', 'medium']:
                if spam_info.get('unsubscribe_link') or spam_info.get('unsubscribe_email'):
                    unsubscribe_candidates.append({
                        'email': email,
                        'spam_info': spam_info
                    })
                    logger.info(f"Found unsubscribe candidate: {email.get('subject')[:50]}")

        logger.info(f"SPAM processing complete: {len(unsubscribe_candidates)} unsubscribe candidates")
        return unsubscribe_candidates

    except Exception as e:
        log_exception(logger, e, "Error processing SPAM automations")
        metrics.record_error(__name__, type(e).__name__, str(e), traceback.format_exc())
        return unsubscribe_candidates


def display_automation_summary(
    need_action_results: Dict[str, List[Dict[str, Any]]],
    spam_results: List[Dict[str, Any]]
) -> None:
    """
    Display automation summary to user for confirmation.

    Args:
        need_action_results: Results from process_need_action_automations()
        spam_results: Results from process_spam_automations()
    """
    print("\n" + "=" * 80)
    print("AUTOMATION SUMMARY - PENDING USER CONFIRMATION")
    print("=" * 80 + "\n")

    # Calendar events
    if need_action_results['calendar_events']:
        print(f"📅 CALENDAR EVENTS TO CREATE ({len(need_action_results['calendar_events'])}):")
        print("-" * 80)
        for idx, item in enumerate(need_action_results['calendar_events'], 1):
            event = item['event_details']
            email = item['email']
            print(f"  {idx}. {event.get('title')}")
            print(f"     Date: {event.get('date')}{' at ' + event.get('time') if event.get('time') else ' (all-day)'}")
            print(f"     From email: {email.get('subject')[:60]}")
            print(f"     Reminder: 1 day before")
            print()

    # Tasks
    if need_action_results['tasks']:
        print(f"\n✅ TASKS TO CREATE ({len(need_action_results['tasks'])}):")
        print("-" * 80)
        for idx, item in enumerate(need_action_results['tasks'], 1):
            task = item['task_details']
            email = item['email']
            print(f"  {idx}. {email.get('subject')[:60]}")
            print(f"     Due: {task.get('due_date', 'No due date')}")
            print(f"     Amount: {task.get('amount', 'N/A')}")
            print()

    # Unsubscribe candidates
    if spam_results:
        print(f"\n🚫 UNSUBSCRIBE REQUESTS TO SEND ({len(spam_results)}):")
        print("-" * 80)
        for idx, item in enumerate(spam_results, 1):
            spam_info = item['spam_info']
            email = item['email']
            print(f"  {idx}. {email.get('subject')[:60]}")
            print(f"     From: {email.get('from')[:50]}")
            print(f"     Confidence: {spam_info.get('confidence')}")
            print(f"     Reason: {spam_info.get('reason')[:70]}")
            if spam_info.get('unsubscribe_email'):
                print(f"     Unsubscribe email: {spam_info.get('unsubscribe_email')}")
            if spam_info.get('unsubscribe_link'):
                print(f"     Unsubscribe link: {spam_info.get('unsubscribe_link')[:60]}...")
            print()

    if not need_action_results['calendar_events'] and not need_action_results['tasks'] and not spam_results:
        print("No automation actions pending.")

    print("=" * 80)


def execute_automations_with_confirmation(
    need_action_results: Dict[str, List[Dict[str, Any]]],
    spam_results: List[Dict[str, Any]],
    gmail_service: Any,
    calendar_service: Any,
    tasks_service: Any
) -> Dict[str, int]:
    """
    Execute automations after user confirmation.

    Args:
        need_action_results: Results from process_need_action_automations()
        spam_results: Results from process_spam_automations()
        gmail_service: Authenticated Gmail API service
        calendar_service: Authenticated Google Calendar API service
        tasks_service: Authenticated Google Tasks API service

    Returns:
        dict: Execution stats with keys:
            - events_created: Number of calendar events created
            - tasks_created: Number of tasks created
            - unsubscribe_sent: Number of unsubscribe requests sent
    """
    logger.info("Executing automations with user confirmation")

    stats = {
        'events_created': 0,
        'tasks_created': 0,
        'unsubscribe_sent': 0
    }

    try:
        # Display summary
        display_automation_summary(need_action_results, spam_results)

        # Ask for confirmation
        total_actions = (
            len(need_action_results['calendar_events']) +
            len(need_action_results['tasks']) +
            len(spam_results)
        )

        if total_actions == 0:
            return stats

        print(f"\n⚠️  Total actions pending: {total_actions}")
        confirmation = input("\nDo you want to proceed with these automations? (yes/no): ").strip().lower()

        if confirmation not in ['yes', 'y']:
            logger.info("User declined automation execution")
            print("\n❌ Automation cancelled by user")
            return stats

        print("\n⚙️  Executing automations...\n")

        # Create calendar events
        for item in need_action_results['calendar_events']:
            success = create_calendar_event(
                calendar_service,
                item['event_details'],
                item['email']
            )
            if success:
                stats['events_created'] += 1
                print(f"  ✅ Created calendar event: {item['event_details'].get('title')}")

        # Create tasks
        for item in need_action_results['tasks']:
            success = create_task(
                tasks_service,
                item['task_details'],
                item['email']
            )
            if success:
                stats['tasks_created'] += 1
                print(f"  ✅ Created task: {item['email'].get('subject')[:50]}")

        # Send unsubscribe requests
        for item in spam_results:
            success = send_unsubscribe_request(
                gmail_service,
                item['spam_info'],
                item['email']
            )
            if success:
                stats['unsubscribe_sent'] += 1
                print(f"  ✅ Sent unsubscribe request: {item['email'].get('subject')[:50]}")

        print(f"\n✅ Automation complete: {stats['events_created']} events, {stats['tasks_created']} tasks, {stats['unsubscribe_sent']} unsubscribes")
        logger.info(f"Automation execution complete: {stats}")
        return stats

    except Exception as e:
        log_exception(logger, e, "Error executing automations")
        print(f"\n⚠️  Error during automation execution: {e}")
        return stats
