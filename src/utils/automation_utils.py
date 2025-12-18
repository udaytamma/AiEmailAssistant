"""
Automation Utility Functions
Handles automated actions for categorized emails:
- Calendar event creation for Need-Action emails
- Task creation for bill-due emails
- Unsubscribe handling for SPAM emails
"""

import json
import time
import traceback
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from .logger_utils import setup_logger, log_exception, log_api_call
from .metrics_utils import get_metrics_tracker

# Initialize logger
logger = setup_logger(__name__)


class AutomationError(Exception):
    """Base exception for automation errors."""
    pass


def extract_event_details(
    email: Dict[str, Any],
    client: Any,
    model_name: str
) -> Optional[Dict[str, Any]]:
    """
    Extract event details (date, time, description) from email using Gemini.

    Uses Gemini AI to identify if email contains event information and extract
    structured data for calendar event creation.

    Args:
        email: Categorized email dictionary
        client: Initialized Gemini client instance (google.genai.Client)
        model_name: Name of the Gemini model to use

    Returns:
        dict: Event details with keys:
            - has_event: bool (True if email contains event info)
            - date: str (ISO format date, required)
            - time: str (HH:MM format, optional)
            - title: str (event title)
            - description: str (event description)
        None if extraction fails or no event found
    """
    logger.debug(f"Extracting event details from: {email.get('subject', 'No Subject')[:50]}")
    start_time = time.time()
    metrics = get_metrics_tracker()

    prompt = f"""Analyze the following email and determine if it contains event information (appointment, birthday invite, meeting, etc.).

From: {email.get('from', 'Unknown')}
Subject: {email.get('subject', 'No Subject')}
Content: {email.get('snippet', 'No content')}

Respond ONLY with a valid JSON object (no markdown, no code blocks):
{{
  "has_event": true/false,
  "date": "<YYYY-MM-DD format if event exists, otherwise null>",
  "time": "<HH:MM format if specified, otherwise null>",
  "title": "<event title if event exists, otherwise null>",
  "description": "<brief event description if event exists, otherwise null>"
}}

Rules:
- Set has_event to true ONLY if there's a clear date for an event
- Date is REQUIRED for has_event=true (must be parseable date)
- Time is OPTIONAL (set to null if not specified)
- Look for phrases like: "appointment on", "meet at", "birthday on", "event scheduled for"
- If no clear event date found, set has_event to false

Only return the JSON object, nothing else."""

    try:
        # Generate response from Gemini
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            elapsed = time.time() - start_time

            log_api_call(logger, "Gemini", True)
            metrics.record_api_call("Gemini", "extract_event_details", True, False, elapsed)

        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = f"Gemini API call failed for event extraction: {e}"
            logger.error(error_msg)
            log_api_call(logger, "Gemini", False)
            metrics.record_api_call("Gemini", "extract_event_details", False, False, elapsed)
            metrics.record_error(__name__, type(e).__name__, error_msg)
            raise AutomationError(error_msg)

        response_text = response.text.strip()

        # Clean markdown code blocks
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.startswith('```'):
            response_text = response_text[3:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        # Parse JSON response
        try:
            event_data = json.loads(response_text)
            logger.debug(f"Event extraction result: has_event={event_data.get('has_event')}")
            return event_data

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in event extraction: {e}"
            logger.error(f"{error_msg}\nResponse text: {response_text[:200]}")
            metrics.record_error(__name__, "JSONDecodeError", error_msg)
            return None

    except Exception as e:
        if not isinstance(e, AutomationError):
            log_exception(logger, e, "Error extracting event details")
            metrics.record_error(__name__, type(e).__name__, str(e), traceback.format_exc())
        return None


def check_autopay_scheduled(
    email: Dict[str, Any],
    client: Any,
    model_name: str
) -> Optional[Dict[str, Any]]:
    """
    Check if bill-due email has autopay scheduled using Gemini.

    Uses Gemini AI to determine if email mentions autopay is enabled/scheduled.

    Args:
        email: Categorized email dictionary
        client: Initialized Gemini client instance (google.genai.Client)
        model_name: Name of the Gemini model to use

    Returns:
        dict: Autopay check result with keys:
            - has_autopay: bool (True if autopay is scheduled)
            - due_date: str (ISO format date if found, otherwise null)
            - amount: str (bill amount if found, otherwise null)
        None if check fails
    """
    logger.debug(f"Checking autopay status for: {email.get('subject', 'No Subject')[:50]}")
    start_time = time.time()
    metrics = get_metrics_tracker()

    prompt = f"""Analyze the following email and determine if it mentions autopay being enabled or scheduled.

From: {email.get('from', 'Unknown')}
Subject: {email.get('subject', 'No Subject')}
Content: {email.get('snippet', 'No content')}

Respond ONLY with a valid JSON object (no markdown, no code blocks):
{{
  "has_autopay": true/false,
  "due_date": "<YYYY-MM-DD format if bill due date found, otherwise null>",
  "amount": "<bill amount if found, otherwise null>"
}}

Rules:
- Set has_autopay to true ONLY if email explicitly mentions:
  - "autopay enabled", "autopay scheduled", "automatic payment set up"
  - "will be automatically charged", "auto-debit enabled"
- Set has_autopay to false if:
  - No mention of autopay
  - Email says "autopay not enabled", "manual payment required"
  - Payment action required from user

Only return the JSON object, nothing else."""

    try:
        # Generate response from Gemini
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            elapsed = time.time() - start_time

            log_api_call(logger, "Gemini", True)
            metrics.record_api_call("Gemini", "check_autopay", True, False, elapsed)

        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = f"Gemini API call failed for autopay check: {e}"
            logger.error(error_msg)
            log_api_call(logger, "Gemini", False)
            metrics.record_api_call("Gemini", "check_autopay", False, False, elapsed)
            metrics.record_error(__name__, type(e).__name__, error_msg)
            raise AutomationError(error_msg)

        response_text = response.text.strip()

        # Clean markdown code blocks
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.startswith('```'):
            response_text = response_text[3:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        # Parse JSON response
        try:
            autopay_data = json.loads(response_text)
            logger.debug(f"Autopay check result: has_autopay={autopay_data.get('has_autopay')}")
            return autopay_data

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in autopay check: {e}"
            logger.error(f"{error_msg}\nResponse text: {response_text[:200]}")
            metrics.record_error(__name__, "JSONDecodeError", error_msg)
            return None

    except Exception as e:
        if not isinstance(e, AutomationError):
            log_exception(logger, e, "Error checking autopay status")
            metrics.record_error(__name__, type(e).__name__, str(e), traceback.format_exc())
        return None


def verify_spam_and_extract_unsubscribe(
    email: Dict[str, Any],
    client: Any,
    model_name: str
) -> Optional[Dict[str, Any]]:
    """
    Verify if email is SPAM and extract unsubscribe information using Gemini.

    Uses Gemini AI to confirm SPAM classification and find unsubscribe link/email.

    Args:
        email: Categorized email dictionary
        client: Initialized Gemini client instance (google.genai.Client)
        model_name: Name of the Gemini model to use

    Returns:
        dict: SPAM verification result with keys:
            - is_spam: bool (True if confirmed SPAM)
            - confidence: str (high/medium/low)
            - unsubscribe_link: str (URL if found, otherwise null)
            - unsubscribe_email: str (email address if found, otherwise null)
            - reason: str (why it's classified as SPAM)
        None if verification fails
    """
    logger.debug(f"Verifying SPAM status for: {email.get('subject', 'No Subject')[:50]}")
    start_time = time.time()
    metrics = get_metrics_tracker()

    prompt = f"""Analyze the following email and determine if it's truly SPAM (unwanted/promotional).

From: {email.get('from', 'Unknown')}
Subject: {email.get('subject', 'No Subject')}
Content: {email.get('snippet', 'No content')}

Respond ONLY with a valid JSON object (no markdown, no code blocks):
{{
  "is_spam": true/false,
  "confidence": "<high/medium/low>",
  "unsubscribe_link": "<full URL if found in content, otherwise null>",
  "unsubscribe_email": "<email address if found, otherwise null>",
  "reason": "<brief explanation of why it's SPAM or not>"
}}

Rules:
- Set is_spam to true if:
  - Unsolicited marketing/promotional content
  - Suspicious sender or phishing attempt
  - Unwanted newsletters or mass emails
- Set is_spam to false if:
  - Legitimate transactional email (receipts, confirmations)
  - Personal correspondence
  - Emails from known services the user likely subscribed to
- Look for unsubscribe links (usually at bottom): "unsubscribe", "opt-out", "manage preferences"
- Confidence: high (very certain), medium (likely), low (uncertain)

Only return the JSON object, nothing else."""

    try:
        # Generate response from Gemini
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            elapsed = time.time() - start_time

            log_api_call(logger, "Gemini", True)
            metrics.record_api_call("Gemini", "verify_spam", True, False, elapsed)

        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = f"Gemini API call failed for SPAM verification: {e}"
            logger.error(error_msg)
            log_api_call(logger, "Gemini", False)
            metrics.record_api_call("Gemini", "verify_spam", False, False, elapsed)
            metrics.record_error(__name__, type(e).__name__, error_msg)
            raise AutomationError(error_msg)

        response_text = response.text.strip()

        # Clean markdown code blocks
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.startswith('```'):
            response_text = response_text[3:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        # Parse JSON response
        try:
            spam_data = json.loads(response_text)
            logger.debug(f"SPAM verification result: is_spam={spam_data.get('is_spam')}, confidence={spam_data.get('confidence')}")
            return spam_data

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in SPAM verification: {e}"
            logger.error(f"{error_msg}\nResponse text: {response_text[:200]}")
            metrics.record_error(__name__, "JSONDecodeError", error_msg)
            return None

    except Exception as e:
        if not isinstance(e, AutomationError):
            log_exception(logger, e, "Error verifying SPAM status")
            metrics.record_error(__name__, type(e).__name__, str(e), traceback.format_exc())
        return None


def create_calendar_event(
    service: Any,
    event_details: Dict[str, Any],
    email: Dict[str, Any]
) -> bool:
    """
    Create Google Calendar event with 1-day advance reminder.

    Args:
        service: Authenticated Google API service instance
        event_details: Event details from extract_event_details()
        email: Original email dictionary

    Returns:
        bool: True if event created successfully, False otherwise
    """
    logger.info(f"Creating calendar event: {event_details.get('title')}")
    start_time = time.time()
    metrics = get_metrics_tracker()

    try:
        # Parse date and time
        event_date = event_details.get('date')
        event_time = event_details.get('time')

        if not event_date:
            logger.error("Cannot create calendar event: date is required")
            return False

        # Build event datetime
        if event_time:
            start_datetime = f"{event_date}T{event_time}:00"
            end_datetime = datetime.fromisoformat(start_datetime) + timedelta(hours=1)
            end_datetime = end_datetime.isoformat()
        else:
            # All-day event
            start_datetime = event_date
            end_datetime = (datetime.fromisoformat(event_date) + timedelta(days=1)).date().isoformat()

        # Build event object
        event = {
            'summary': event_details.get('title', email.get('subject')),
            'description': event_details.get('description', f"From email: {email.get('subject')}"),
            'start': {
                'dateTime' if event_time else 'date': start_datetime,
                'timeZone': 'America/Los_Angeles',
            },
            'end': {
                'dateTime' if event_time else 'date': end_datetime,
                'timeZone': 'America/Los_Angeles',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                    {'method': 'popup', 'minutes': 24 * 60},  # 1 day before
                ],
            },
        }

        # Create event via Calendar API
        created_event = service.events().insert(calendarId='primary', body=event).execute()

        elapsed = time.time() - start_time
        logger.info(f"Calendar event created successfully: {created_event.get('htmlLink')}")
        log_api_call(logger, "Google Calendar", True)
        metrics.record_api_call("Google Calendar", "create_event", True, False, elapsed)

        return True

    except Exception as e:
        elapsed = time.time() - start_time
        log_exception(logger, e, "Failed to create calendar event")
        log_api_call(logger, "Google Calendar", False)
        metrics.record_api_call("Google Calendar", "create_event", False, False, elapsed)
        metrics.record_error(__name__, type(e).__name__, str(e), traceback.format_exc())
        return False


def create_task(
    service: Any,
    task_details: Dict[str, Any],
    email: Dict[str, Any]
) -> bool:
    """
    Create Google Task without reminder.

    Args:
        service: Authenticated Google API service instance
        task_details: Task details (due_date, amount, etc.)
        email: Original email dictionary

    Returns:
        bool: True if task created successfully, False otherwise
    """
    logger.info(f"Creating task: {email.get('subject')[:50]}")
    start_time = time.time()
    metrics = get_metrics_tracker()

    try:
        # Build task object
        task = {
            'title': email.get('subject', 'Bill Payment'),
            'notes': f"From: {email.get('from')}\nAmount: {task_details.get('amount', 'N/A')}\n\n{email.get('snippet', '')}",
        }

        # Add due date if available
        if task_details.get('due_date'):
            task['due'] = f"{task_details['due_date']}T00:00:00.000Z"

        # Create task via Tasks API
        created_task = service.tasks().insert(tasklist='@default', body=task).execute()

        elapsed = time.time() - start_time
        logger.info(f"Task created successfully: {created_task.get('id')}")
        log_api_call(logger, "Google Tasks", True)
        metrics.record_api_call("Google Tasks", "create_task", True, False, elapsed)

        return True

    except Exception as e:
        elapsed = time.time() - start_time
        log_exception(logger, e, "Failed to create task")
        log_api_call(logger, "Google Tasks", False)
        metrics.record_api_call("Google Tasks", "create_task", False, False, elapsed)
        metrics.record_error(__name__, type(e).__name__, str(e), traceback.format_exc())
        return False


def send_unsubscribe_request(
    gmail_service: Any,
    unsubscribe_info: Dict[str, Any],
    email: Dict[str, Any]
) -> bool:
    """
    Send unsubscribe email request.

    Args:
        gmail_service: Authenticated Gmail API service instance
        unsubscribe_info: Unsubscribe details from verify_spam_and_extract_unsubscribe()
        email: Original email dictionary

    Returns:
        bool: True if unsubscribe request sent successfully, False otherwise
    """
    logger.info(f"Sending unsubscribe request for: {email.get('subject')[:50]}")
    start_time = time.time()
    metrics = get_metrics_tracker()

    try:
        unsubscribe_email = unsubscribe_info.get('unsubscribe_email')

        if not unsubscribe_email:
            logger.warning("No unsubscribe email found, cannot send request")
            return False

        # Build unsubscribe email
        from email.mime.text import MIMEText
        import base64

        message = MIMEText(f"Please unsubscribe me from this mailing list.\n\nOriginal Subject: {email.get('subject')}")
        message['to'] = unsubscribe_email
        message['subject'] = 'Unsubscribe Request'

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        # Send via Gmail API
        sent_message = gmail_service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()

        elapsed = time.time() - start_time
        logger.info(f"Unsubscribe request sent successfully: {sent_message.get('id')}")
        log_api_call(logger, "Gmail", True)
        metrics.record_api_call("Gmail", "send_unsubscribe", True, False, elapsed)

        return True

    except Exception as e:
        elapsed = time.time() - start_time
        log_exception(logger, e, "Failed to send unsubscribe request")
        log_api_call(logger, "Gmail", False)
        metrics.record_api_call("Gmail", "send_unsubscribe", False, False, elapsed)
        metrics.record_error(__name__, type(e).__name__, str(e), traceback.format_exc())
        return False
