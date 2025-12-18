"""
Gemini AI Utility Functions
Handles email categorization and summary generation using Google's Gemini AI
with comprehensive error handling, logging, and metrics tracking.
"""

import json
import time
import traceback
from typing import List, Dict, Any, Optional

from .logger_utils import setup_logger, log_exception, log_api_call, log_performance
from .metrics_utils import get_metrics_tracker

# Initialize logger
logger = setup_logger(__name__)


class GeminiAPIError(Exception):
    """Raised when Gemini API call fails."""
    pass


class InvalidResponseError(Exception):
    """Raised when Gemini returns invalid JSON response."""
    pass


def categorize_email_with_gemini(email_dict: Dict[str, str], client: Any, model_name: str) -> Dict[str, Any]:
    """
    Categorize a single email using Gemini AI.

    Sends email metadata to Gemini and receives structured categorization
    including category, subcategory, summary, action item, and due date.

    Args:
        email_dict: Dictionary containing email data (from, subject, snippet)
        client: Initialized Gemini client instance (google.genai.Client)
        model_name: Name of the Gemini model to use

    Returns:
        dict: Categorization result with keys:
            - category: Main category (Need-Action, FYI, Newsletter, Marketing, SPAM)
            - subcategory: Sub-category (Bill-Due, Credit-Card-Payment, etc.)
            - summary: One-sentence email summary
            - action_item: Suggested action (AddToCalendar, AddToNotes, etc.)
            - date_due: Due date if applicable, otherwise None

    Note:
        Returns fallback categorization with "Unknown" category on error
    """
    logger.debug(f"Categorizing email: {email_dict.get('subject', 'No Subject')[:50]}")
    start_time = time.time()
    metrics = get_metrics_tracker()

    # Construct structured prompt for Gemini
    prompt = f"""Analyze the following email and respond ONLY with a valid JSON object (no markdown, no code blocks, just pure JSON):

From: {email_dict['from']}
Subject: {email_dict['subject']}
Content: {email_dict['snippet']}

Respond with this exact JSON structure:
{{
  "category": "<one of: Need-Action, FYI, Newsletter, Marketing, SPAM>",
  "subcategory": "<one of: Bill-Due, Credit-Card-Payment, Service-Change, Package-Tracker, JobAlert, General>",
  "summary": "<one sentence summary>",
  "action_item": "<one of: AddToCalendar, AddToNotes, Unsubscribe, Delete, None>",
  "date_due": "<date if applicable, otherwise null>"
}}

Classification Rules:
- Need-Action: Requires user response (bills, important tasks)
- FYI: Information only (receipts, updates, confirmations, package delivery updates, online orders)
- Marketing: Promotional content
- Newsletters: Newsletters
- SPAM: Unwanted content, suspicious emails

Only return the JSON object, nothing else."""

    try:
        # Generate response from Gemini
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            elapsed = time.time() - start_time

            log_api_call(logger, "Gemini", True)
            metrics.record_api_call("Gemini", "categorize_email", True, False, elapsed)

        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = f"Gemini API call failed: {e}"
            logger.error(error_msg)
            log_api_call(logger, "Gemini", False)
            metrics.record_api_call("Gemini", "categorize_email", False, False, elapsed)
            metrics.record_error(__name__, type(e).__name__, error_msg, traceback.format_exc())
            raise GeminiAPIError(error_msg)

        response_text = response.text.strip()

        # Clean markdown code blocks from response
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.startswith('```'):
            response_text = response_text[3:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        # Parse JSON response
        try:
            categorization = json.loads(response_text)
            logger.debug(f"Successfully categorized email as: {categorization.get('category')}")
            return categorization

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON response from Gemini: {e}"
            logger.error(f"{error_msg}\nResponse text: {response_text[:200]}")
            metrics.record_error(__name__, "JSONDecodeError", error_msg)
            raise InvalidResponseError(error_msg)

    except Exception as e:
        if not isinstance(e, (GeminiAPIError, InvalidResponseError)):
            log_exception(logger, e, "Error categorizing email")
            metrics.record_error(__name__, type(e).__name__, str(e), traceback.format_exc())

        # Return fallback categorization on error
        logger.warning("Returning fallback categorization due to error")
        print(f"⚠️  Error categorizing email: {e}")
        return {
            "category": "Unknown",
            "subcategory": "None",
            "summary": "Failed to categorize",
            "action_item": "None",
            "date_due": None
        }


def categorize_emails(
    email_list: List[Dict[str, str]],
    client: Any,
    model_name: str,
    requests_per_minute: int = 30
) -> List[Dict[str, Any]]:
    """
    Categorize multiple emails with rate limiting.

    Processes each email through Gemini AI categorization while respecting
    API rate limits to avoid quota errors.

    Args:
        email_list: List of email dictionaries from fetch_recent_emails()
        client: Initialized Gemini client instance (google.genai.Client)
        model_name: Name of the Gemini model to use
        requests_per_minute: API rate limit (default: 30 for gemini-2.5-flash-lite)

    Returns:
        list: Categorized emails with added fields (category, subcategory, etc.)

    Note:
        Automatically adds delays between requests based on rate limit.
        Displays progress and categorization results to console.
    """
    logger.info(f"Starting categorization of {len(email_list)} emails")
    start_time = time.time()
    metrics = get_metrics_tracker()

    print("\n" + "=" * 80)
    print("CATEGORIZING EMAILS WITH GEMINI LLM")
    print("=" * 80 + "\n")

    categorized_emails = []
    successful_count = 0
    failed_count = 0

    # Calculate delay to stay within rate limit
    delay_between_requests = 1  # Conservative delay between requests

    try:
        for idx, email in enumerate(email_list, 1):
            print(f"Processing Email #{idx}/{len(email_list)}...")
            email_start_time = time.time()

            try:
                # Get categorization from Gemini
                categorization = categorize_email_with_gemini(email, client, model_name)

                # Merge original email data with categorization
                categorized_email = {
                    **email,  # Original email fields
                    **categorization  # Add categorization fields
                }

                categorized_emails.append(categorized_email)

                # Track processing time
                email_elapsed = time.time() - email_start_time
                metrics.record_email_processing(
                    email.get('id', 'unknown'),
                    categorization.get('category', 'Unknown'),
                    email_elapsed
                )

                # Display categorization result
                print(f"  Subject: {email['subject'][:50]}...")
                print(f"  Category: {categorization['category']}")
                print(f"  Subcategory: {categorization['subcategory']}")
                print(f"  Action: {categorization['action_item']}")
                print(f"  Summary: {categorization['summary'][:80]}...")
                print("-" * 80)

                if categorization['category'] != 'Unknown':
                    successful_count += 1
                else:
                    failed_count += 1

            except Exception as e:
                logger.error(f"Failed to process email #{idx}: {e}")
                metrics.record_error(__name__, type(e).__name__, f"Failed to process email: {e}")
                failed_count += 1

                # Add email with fallback categorization
                categorized_emails.append({
                    **email,
                    "category": "Unknown",
                    "subcategory": "None",
                    "summary": "Processing failed",
                    "action_item": "None",
                    "date_due": None
                })

            # Rate limiting: Wait between requests
            if idx < len(email_list):  # Skip wait after last email
                print(f"  ⏳ Waiting {delay_between_requests:.0f} seconds to respect rate limits...")
                time.sleep(delay_between_requests)

        elapsed = time.time() - start_time
        log_performance(logger, f"Categorize {len(email_list)} emails", elapsed)
        logger.info(f"Categorization complete: {successful_count} successful, {failed_count} failed in {elapsed:.2f}s")

        print(f"\n✅ Categorization complete! ({successful_count} successful, {failed_count} failed)\n")
        return categorized_emails

    except Exception as e:
        elapsed = time.time() - start_time
        log_exception(logger, e, "Batch categorization failed")
        metrics.record_error(__name__, type(e).__name__, f"Batch categorization failed: {e}", traceback.format_exc())
        # Return whatever was categorized so far
        return categorized_emails


def generate_newsletter_summary(
    email_body: str,
    subject: str,
    client: Any,
    model_name: str,
    max_chars: int = 3000
) -> List[str]:
    """
    Generate a 3-bullet point summary for newsletter emails.

    Extracts key topics and insights from newsletter content using Gemini AI.

    Args:
        email_body: Full email body text
        subject: Email subject line
        client: Initialized Gemini client instance (google.genai.Client)
        model_name: Name of the Gemini model to use
        max_chars: Maximum characters to send to AI (default: 3000)

    Returns:
        list: Three-item list containing bullet point summaries
              Returns fallback text on error

    Note:
        Truncates long emails to max_chars to avoid token limits
    """
    logger.debug(f"Generating newsletter summary for: {subject[:50]}")
    start_time = time.time()
    metrics = get_metrics_tracker()

    # Truncate email body to avoid token limits
    truncated_body = email_body[:max_chars] if len(email_body) > max_chars else email_body

    prompt = f"""Analyze the following newsletter email and create a concise 3-bullet point summary.

Subject: {subject}

Email Content:
{truncated_body}

Respond ONLY with a JSON object containing exactly 3 bullet points:
{{
  "bullet1": "<first key point>",
  "bullet2": "<second key point>",
  "bullet3": "<third key point>"
}}

Each bullet point should be:
- One clear, informative sentence
- Capture the main topics or insights
- Be specific and actionable when possible

Only return the JSON object, nothing else."""

    try:
        # Generate response from Gemini
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            elapsed = time.time() - start_time

            log_api_call(logger, "Gemini", True)
            metrics.record_api_call("Gemini", "newsletter_summary", True, False, elapsed)

        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = f"Gemini API call failed for newsletter summary: {e}"
            logger.error(error_msg)
            log_api_call(logger, "Gemini", False)
            metrics.record_api_call("Gemini", "newsletter_summary", False, False, elapsed)
            metrics.record_error(__name__, type(e).__name__, error_msg)
            raise GeminiAPIError(error_msg)

        response_text = response.text.strip()

        # Clean markdown code blocks
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.startswith('```'):
            response_text = response_text[3:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        # Parse and extract bullet points
        try:
            summary = json.loads(response_text)
            bullet_points = [
                summary.get('bullet1', ''),
                summary.get('bullet2', ''),
                summary.get('bullet3', '')
            ]
            logger.debug(f"Successfully generated newsletter summary with {len(bullet_points)} points")
            return bullet_points

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in newsletter summary: {e}"
            logger.error(error_msg)
            metrics.record_error(__name__, "JSONDecodeError", error_msg)
            raise InvalidResponseError(error_msg)

    except Exception as e:
        if not isinstance(e, (GeminiAPIError, InvalidResponseError)):
            log_exception(logger, e, "Error generating newsletter summary")
            metrics.record_error(__name__, type(e).__name__, str(e), traceback.format_exc())

        logger.warning("Returning fallback newsletter summary")
        print(f"⚠️  Error generating newsletter summary: {e}")
        return [
            "Failed to generate summary point 1",
            "Failed to generate summary point 2",
            "Failed to generate summary point 3"
        ]


def generate_category_summary(
    emails: List[Dict[str, Any]],
    category_name: str,
    client: Any,
    model_name: str,
    max_emails: int = 10
) -> List[str]:
    """
    Generate consolidated summary for Need-Action or FYI category emails.

    Creates bullet point summary highlighting important items and grouping
    similar emails together.

    Args:
        emails: List of categorized email dictionaries
        category_name: Category name (e.g., "Need-Action", "FYI")
        client: Initialized Gemini client instance (google.genai.Client)
        model_name: Name of the Gemini model to use
        max_emails: Maximum emails to include in summary (default: 10)

    Returns:
        list: Bullet point summaries (up to 5 points)
              Returns email subjects as fallback on error

    Note:
        Limits to max_emails to avoid token limits and improve summary quality
    """
    logger.debug(f"Generating category summary for {category_name} with {len(emails)} emails")
    start_time = time.time()
    metrics = get_metrics_tracker()

    if not emails:
        logger.info(f"No emails to summarize for category: {category_name}")
        return []

    # Create summary of emails in this category
    email_summaries = []
    for email in emails:
        email_summaries.append(
            f"- {email['subject']} (from {email['from']}): {email.get('summary', 'No summary available')}"
        )

    # Limit to max_emails to avoid token limits
    combined_text = "\n".join(email_summaries[:max_emails])

    prompt = f"""Analyze the following {category_name} emails and create a consolidated bullet point summary.

Emails:
{combined_text}

Respond ONLY with a JSON object containing bullet points (up to 5 key points):
{{
  "summary_points": ["<point 1>", "<point 2>", "<point 3>", ...]
}}

Each bullet point should:
- Highlight the most important or urgent items
- Group similar items together when applicable
- Be clear and actionable

Only return the JSON object, nothing else."""

    try:
        # Generate response from Gemini
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            elapsed = time.time() - start_time

            log_api_call(logger, "Gemini", True)
            metrics.record_api_call("Gemini", "category_summary", True, False, elapsed)

        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = f"Gemini API call failed for category summary: {e}"
            logger.error(error_msg)
            log_api_call(logger, "Gemini", False)
            metrics.record_api_call("Gemini", "category_summary", False, False, elapsed)
            metrics.record_error(__name__, type(e).__name__, error_msg)
            raise GeminiAPIError(error_msg)

        response_text = response.text.strip()

        # Clean markdown code blocks
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.startswith('```'):
            response_text = response_text[3:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        # Parse summary points
        try:
            summary = json.loads(response_text)
            summary_points = summary.get('summary_points', [])
            logger.debug(f"Successfully generated category summary with {len(summary_points)} points")
            return summary_points

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in category summary: {e}"
            logger.error(error_msg)
            metrics.record_error(__name__, "JSONDecodeError", error_msg)
            raise InvalidResponseError(error_msg)

    except Exception as e:
        if not isinstance(e, (GeminiAPIError, InvalidResponseError)):
            log_exception(logger, e, "Error generating category summary")
            metrics.record_error(__name__, type(e).__name__, str(e), traceback.format_exc())

        logger.warning(f"Returning fallback category summary for {category_name}")
        print(f"⚠️  Error generating category summary: {e}")
        # Fallback: return first 5 email subjects
        return [f"{email['subject']}" for email in emails[:5]]
