"""
Gemini AI Utility Functions
Handles email categorization and summary generation using Google's Gemini AI
"""

import json
import time


def categorize_email_with_gemini(email_dict, model):
    """
    Categorize a single email using Gemini AI.

    Sends email metadata to Gemini and receives structured categorization
    including category, subcategory, summary, action item, and due date.

    Args:
        email_dict: Dictionary containing email data (from, subject, snippet)
        model: Initialized Gemini model instance

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
    # Construct structured prompt for Gemini
    prompt = f"""Analyze the following email and classify it into the requested categories.
Respond only with a single valid JSON object.
Do not include any explanation, markdown, or code fences.

Email:
From: {email_dict.get('from', 'Unknown')}
Subject: {email_dict.get('subject', 'No Subject')}
Content: {email_dict.get('snippet', '')}

Your task:
1. Understand the sender, subject, and content.
2. Decide the most appropriate single category and subcategory.
3. Determine if there is any clear action the user should take and whether there is a due date or deadline.

Output:
Return exactly this JSON schema (keys and allowed values must match exactly, no extra keys):
{{
    "category": "<one of: Need-Action, FYI, Newsletter, Marketing, SPAM>",
    "subcategory": "<one of: Bill-Due, Credit-Card-Payment, Service-Change, Package-Tracker, JobAlert, General>",
    "summary": "<one sentence summary>",
    "action_item": "<one of: AddToCalendar, AddToNotes, Unsubscribe, Delete, None>",
    "date_due": "<ISO 8601 date YYYY-MM-DD if the email clearly specifies a due date or deadline; otherwise null>"
}}

Classification rules:
• "Need-Action": Use this when the email requires the user to do something specific.
• "FYI": Use this when the email is informational only.
• "Newsletter": Recurring informational or editorial emails.
• "Marketing": Promotional emails (discounts, offers).
• "SPAM": Unwanted, misleading, or suspicious emails.

Subcategory rules (use the best fit; if none fits, use "General"):
• "Bill-Due": Bills, invoices, subscriptions with amount/due date.
• "Credit-Card-Payment": Credit card bill or statement.
• "Service-Change": Account changes, policy updates.
• "Package-Tracker": Shipment/delivery updates.
• "JobAlert": Job postings/career alerts.
• "General": Anything else.

Action item rules:
• "AddToCalendar": Time-bound event/deadline.
• "AddToNotes": Important info to keep (policies, account info).
• "Unsubscribe": Recurring newsletters/marketing.
• "Delete": SPAM or irrelevant.
• "None": No action needed.

Date handling:
• For "date_due", use format "YYYY-MM-DD" if explicit.
• If no date or ambiguous, set "date_due" to null.

Only return the JSON object, nothing else."""

    try:
        # Generate response from Gemini
        response = model.generate_content(prompt)
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
        categorization = json.loads(response_text)
        return categorization

    except Exception as e:
        print(f"⚠️  Error categorizing email: {e}")
        # Return fallback categorization on error
        return {
            "category": "Unknown",
            "subcategory": "None",
            "summary": "Failed to categorize",
            "action_item": "None",
            "date_due": None
        }


def categorize_emails(email_list, model, requests_per_minute=30):
    """
    Categorize multiple emails with rate limiting.

    Processes each email through Gemini AI categorization while respecting
    API rate limits to avoid quota errors.

    Args:
        email_list: List of email dictionaries from fetch_recent_emails()
        model: Initialized Gemini model instance
        requests_per_minute: API rate limit (default: 30 for gemini-2.5-flash-lite)

    Returns:
        list: Categorized emails with added fields (category, subcategory, etc.)

    Note:
        Automatically adds delays between requests based on rate limit.
        Displays progress and categorization results to console.
    """
    print("\n" + "=" * 80)
    print("CATEGORIZING EMAILS WITH GEMINI LLM")
    print("=" * 80 + "\n")

    categorized_emails = []
    # Calculate delay to stay within rate limit
    delay_between_requests = 1  # Conservative delay between requests

    for idx, email in enumerate(email_list, 1):
        print(f"Processing Email #{idx}/{len(email_list)}...")

        # Get categorization from Gemini
        categorization = categorize_email_with_gemini(email, model)

        # Merge original email data with categorization
        categorized_email = {
            **email,  # Original email fields
            **categorization  # Add categorization fields
        }

        categorized_emails.append(categorized_email)

        # Display categorization result
        print(f"  Subject: {email['subject'][:50]}...")
        print(f"  Category: {categorization['category']}")
        print(f"  Subcategory: {categorization['subcategory']}")
        print(f"  Action: {categorization['action_item']}")
        print(f"  Summary: {categorization['summary'][:80]}...")
        print("-" * 80)

        # Rate limiting: Wait between requests
        if idx < len(email_list):  # Skip wait after last email
            print(f"  ⏳ Waiting {delay_between_requests:.0f} seconds to respect rate limits...")
            time.sleep(delay_between_requests)

    print("\n✅ Categorization complete!\n")
    return categorized_emails


def generate_newsletter_summary(email_body, subject, model, max_chars=3000):
    """
    Generate a 3-bullet point summary for newsletter emails.

    Extracts key topics and insights from newsletter content using Gemini AI.

    Args:
        email_body: Full email body text
        subject: Email subject line
        model: Initialized Gemini model instance
        max_chars: Maximum characters to send to AI (default: 3000)

    Returns:
        list: Three-item list containing bullet point summaries
              Returns fallback text on error

    Note:
        Truncates long emails to max_chars to avoid token limits
    """
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
        response = model.generate_content(prompt)
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
        summary = json.loads(response_text)
        return [
            summary.get('bullet1', ''),
            summary.get('bullet2', ''),
            summary.get('bullet3', '')
        ]

    except Exception as e:
        print(f"⚠️  Error generating newsletter summary: {e}")
        return [
            "Failed to generate summary point 1",
            "Failed to generate summary point 2",
            "Failed to generate summary point 3"
        ]


def generate_category_summary(emails, category_name, model, max_emails=10):
    """
    Generate consolidated summary for Need-Action or FYI category emails.

    Creates bullet point summary highlighting important items and grouping
    similar emails together.

    Args:
        emails: List of categorized email dictionaries
        category_name: Category name (e.g., "Need-Action", "FYI")
        model: Initialized Gemini model instance
        max_emails: Maximum emails to include in summary (default: 10)

    Returns:
        list: Bullet point summaries (up to 5 points)
              Returns email subjects as fallback on error

    Note:
        Limits to max_emails to avoid token limits and improve summary quality
    """
    if not emails:
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
        response = model.generate_content(prompt)
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
        summary = json.loads(response_text)
        return summary.get('summary_points', [])

    except Exception as e:
        print(f"⚠️  Error generating category summary: {e}")
        # Fallback: return first 5 email subjects
        return [f"{email['subject']}" for email in emails[:5]]
