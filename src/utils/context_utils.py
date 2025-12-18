"""
Context Compression and Summary Utilities
Generates compressed context and elaborate summaries using Gemini AI.
"""

import json
import time
import traceback
from typing import List, Dict, Any

from .logger_utils import setup_logger, log_exception, log_api_call
from .metrics_utils import get_metrics_tracker

# Initialize logger
logger = setup_logger(__name__)


def generate_compressed_context(
    emails: List[Dict[str, Any]],
    categories: List[str],
    client: Any,
    model_name: str
) -> str:
    """
    Generate token-efficient compressed context from emails.

    Creates a compressed representation that maintains key information
    while minimizing token usage for future AI queries.

    Args:
        emails: List of categorized emails
        categories: List of categories to include (e.g., ['Need-Action', 'FYI'])
        client: Initialized Gemini client instance (google.genai.Client)
        model_name: Name of the Gemini model to use

    Returns:
        str: Compressed context string (token-efficient)
    """
    logger.info(f"Generating compressed context for {len(emails)} emails")
    start_time = time.time()
    metrics = get_metrics_tracker()

    # Filter emails by categories
    filtered_emails = [e for e in emails if e.get('category') in categories]

    if not filtered_emails:
        logger.warning("No emails found for specified categories")
        return "{}"

    # Build email summaries
    email_summaries = []
    for email in filtered_emails[:20]:  # Limit to 20 emails to avoid token limits
        email_summaries.append({
            'subject': email.get('subject'),
            'from': email.get('from'),
            'category': email.get('category'),
            'subcategory': email.get('subcategory'),
            'summary': email.get('summary'),
            'date': email.get('date')
        })

    emails_json = json.dumps(email_summaries, indent=2)

    prompt = f"""Analyze the following emails and create a COMPRESSED context representation.

Emails:
{emails_json}

Create a token-efficient compressed context that:
1. Preserves key information (who, what, when, why)
2. Groups similar emails together
3. Uses abbreviations and compact format
4. Can be used to reconstruct important details later

Respond with a JSON object containing the compressed context:
{{
  "key_topics": ["<topic 1>", "<topic 2>", ...],
  "action_items": ["<item 1>", "<item 2>", ...],
  "people": ["<person 1>", "<person 2>", ...],
  "dates": ["<date 1>", "<date 2>", ...],
  "compressed_summary": "<very brief 2-3 sentence summary of all emails>"
}}

Focus on compression and efficiency. Only return the JSON object."""

    try:
        # Generate response from Gemini
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            elapsed = time.time() - start_time

            log_api_call(logger, "Gemini", True)
            metrics.record_api_call("Gemini", "compress_context", True, False, elapsed)

        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = f"Gemini API call failed for context compression: {e}"
            logger.error(error_msg)
            log_api_call(logger, "Gemini", False)
            metrics.record_api_call("Gemini", "compress_context", False, False, elapsed)
            metrics.record_error(__name__, type(e).__name__, error_msg)
            return json.dumps({"error": "Compression failed"})

        response_text = response.text.strip()

        # Clean markdown code blocks
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.startswith('```'):
            response_text = response_text[3:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        # Validate JSON
        try:
            json.loads(response_text)  # Validate it's valid JSON
            logger.info("Compressed context generated successfully")
            return response_text

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in compressed context: {e}"
            logger.error(f"{error_msg}\nResponse text: {response_text[:200]}")
            metrics.record_error(__name__, "JSONDecodeError", error_msg)
            return json.dumps({"error": "Invalid JSON response"})

    except Exception as e:
        log_exception(logger, e, "Error generating compressed context")
        metrics.record_error(__name__, type(e).__name__, str(e), traceback.format_exc())
        return json.dumps({"error": str(e)})


def generate_elaborate_summary(
    emails: List[Dict[str, Any]],
    categories: List[str],
    client: Any,
    model_name: str,
    max_bullets: int = 10
) -> List[str]:
    """
    Generate human-readable elaborate summary (max 10 bullets).

    Creates detailed bullet points highlighting important information
    from Need-Action and FYI emails.

    Args:
        emails: List of categorized emails
        categories: List of categories to include (e.g., ['Need-Action', 'FYI'])
        client: Initialized Gemini client instance (google.genai.Client)
        model_name: Name of the Gemini model to use
        max_bullets: Maximum number of bullet points (default: 10)

    Returns:
        list: List of bullet point strings (max 10)
    """
    logger.info(f"Generating elaborate summary for {len(emails)} emails")
    start_time = time.time()
    metrics = get_metrics_tracker()

    # Filter emails by categories
    filtered_emails = [e for e in emails if e.get('category') in categories]

    if not filtered_emails:
        logger.warning("No emails found for specified categories")
        return ["No emails to summarize"]

    # Build email summaries
    email_summaries = []
    for email in filtered_emails[:20]:  # Limit to 20 emails to avoid token limits
        email_summaries.append(
            f"- {email.get('subject')} (from {email.get('from')}): {email.get('summary')}"
        )

    combined_text = "\n".join(email_summaries)

    prompt = f"""Analyze the following emails and create an elaborate summary with up to {max_bullets} bullet points.

Emails:
{combined_text}

Create a comprehensive summary that:
1. Highlights the most important or urgent items
2. Groups related emails together
3. Provides actionable insights
4. Is clear and easy to understand

Respond with a JSON object containing bullet points:
{{
  "summary_points": [
    "<bullet point 1>",
    "<bullet point 2>",
    ...
  ]
}}

Maximum {max_bullets} bullet points. Each should be 1-2 sentences.
Only return the JSON object."""

    try:
        # Generate response from Gemini
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            elapsed = time.time() - start_time

            log_api_call(logger, "Gemini", True)
            metrics.record_api_call("Gemini", "elaborate_summary", True, False, elapsed)

        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = f"Gemini API call failed for elaborate summary: {e}"
            logger.error(error_msg)
            log_api_call(logger, "Gemini", False)
            metrics.record_api_call("Gemini", "elaborate_summary", False, False, elapsed)
            metrics.record_error(__name__, type(e).__name__, error_msg)
            return [f"Failed to generate summary: {e}"]

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
            summary_data = json.loads(response_text)
            summary_points = summary_data.get('summary_points', [])

            # Limit to max_bullets
            summary_points = summary_points[:max_bullets]

            logger.info(f"Elaborate summary generated successfully: {len(summary_points)} bullets")
            return summary_points

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in elaborate summary: {e}"
            logger.error(f"{error_msg}\nResponse text: {response_text[:200]}")
            metrics.record_error(__name__, "JSONDecodeError", error_msg)
            return ["Failed to parse summary response"]

    except Exception as e:
        log_exception(logger, e, "Error generating elaborate summary")
        metrics.record_error(__name__, type(e).__name__, str(e), traceback.format_exc())
        return [f"Error generating summary: {e}"]
