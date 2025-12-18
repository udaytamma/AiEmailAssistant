"""
Email Utility Functions
Handles Gmail API authentication, email fetching, and email body extraction
with comprehensive error handling, logging, and metrics tracking.
"""

import os
import os.path
import base64
import re
import time
from typing import List, Dict, Any, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .logger_utils import setup_logger, log_exception, log_api_call, log_performance
from .metrics_utils import get_metrics_tracker

# Initialize logger
logger = setup_logger(__name__)

# Gmail API scopes - allows reading, modifying labels, and trashing emails
# If modifying these scopes, delete the file token.json
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']


class GmailConnectionError(Exception):
    """Raised when Gmail connection fails."""
    pass


class EmailFetchError(Exception):
    """Raised when email fetching fails."""
    pass


def connect_to_gmail() -> Any:
    """
    Authenticate and connect to Gmail API using OAuth 2.0.

    Uses credentials.json for initial authentication and stores tokens in token.json
    for subsequent runs. Automatically refreshes expired tokens.

    Returns:
        service: Authenticated Gmail API service instance

    Raises:
        GmailConnectionError: If authentication or connection fails
        FileNotFoundError: If credentials.json is missing
    """
    logger.info("Connecting to Gmail API...")
    start_time = time.time()
    metrics = get_metrics_tracker()

    try:
        creds = None

        # Load existing credentials from token.json if available
        if os.path.exists('token.json'):
            try:
                creds = Credentials.from_authorized_user_file('token.json', SCOPES)
                logger.debug("Loaded credentials from token.json")
            except Exception as e:
                logger.warning(f"Failed to load token.json, will re-authenticate: {e}")
                creds = None

        # If no valid credentials, initiate OAuth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    # Refresh expired token
                    logger.info("Refreshing expired token...")
                    creds.refresh(Request())
                    logger.info("Token refreshed successfully")
                except Exception as e:
                    logger.error(f"Token refresh failed: {e}")
                    raise GmailConnectionError(f"Failed to refresh token: {e}")
            else:
                # New authentication flow using credentials.json
                if not os.path.exists('credentials.json'):
                    error_msg = "credentials.json not found. Please download it from Google Cloud Console."
                    logger.error(error_msg)
                    metrics.record_error(__name__, "FileNotFoundError", error_msg)
                    raise FileNotFoundError(error_msg)

                try:
                    logger.info("Starting new OAuth flow...")
                    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                    creds = flow.run_local_server(port=0)
                    logger.info("OAuth flow completed successfully")
                except Exception as e:
                    error_msg = f"OAuth flow failed: {e}"
                    logger.error(error_msg)
                    metrics.record_error(__name__, "OAuthError", error_msg)
                    raise GmailConnectionError(error_msg)

            # Save credentials for next run
            try:
                with open('token.json', 'w') as token:
                    token.write(creds.to_json())
                logger.debug("Saved credentials to token.json")
            except Exception as e:
                logger.warning(f"Failed to save token.json: {e}")

        # Build and return Gmail API service
        try:
            service = build('gmail', 'v1', credentials=creds)
            elapsed = time.time() - start_time
            log_performance(logger, "Gmail Connection", elapsed)
            log_api_call(logger, "Gmail", True)
            metrics.record_api_call("Gmail", "connect", True, False, elapsed)
            logger.info("Successfully connected to Gmail API")
            return service
        except Exception as e:
            error_msg = f"Failed to build Gmail service: {e}"
            logger.error(error_msg)
            metrics.record_error(__name__, "ServiceBuildError", error_msg)
            raise GmailConnectionError(error_msg)

    except Exception as e:
        elapsed = time.time() - start_time
        log_exception(logger, e, "Gmail connection failed")
        log_api_call(logger, "Gmail", False)
        metrics.record_api_call("Gmail", "connect", False, False, elapsed)
        if not isinstance(e, (GmailConnectionError, FileNotFoundError)):
            metrics.record_error(__name__, type(e).__name__, str(e))
        raise


def fetch_recent_emails(
    service: Any,
    max_results: int = 30,
    query: str = 'is:unread newer_than:1d',
    after_timestamp: Optional[str] = None
) -> List[Dict[str, str]]:
    """
    Fetch recent unread emails from Gmail.

    Retrieves emails matching the search query and extracts metadata
    (sender, subject, date, snippet, ID) for each message.

    Args:
        service: Authenticated Gmail API service instance
        max_results: Maximum number of emails to fetch (default: 30)
        query: Gmail search query (default: unread emails from last 24 hours)
        after_timestamp: Fetch only emails after this timestamp (ISO format, optional)

    Returns:
        list: List of email dictionaries, each containing:
            - id: Email message ID
            - from: Sender email address
            - subject: Email subject line
            - date: Email date/time
            - snippet: Email preview text (first ~150 chars)

    Raises:
        EmailFetchError: If fetching emails fails

    Example:
        emails = fetch_recent_emails(service, max_results=5)
        for email in emails:
            print(f"From: {email['from']}, Subject: {email['subject']}")
    """
    # Add after filter to query if timestamp provided
    if after_timestamp:
        from datetime import datetime
        try:
            dt = datetime.fromisoformat(after_timestamp)
            epoch_seconds = int(dt.timestamp())
            query = f"{query} after:{epoch_seconds}"
            logger.info(f"Fetching emails after {after_timestamp} (epoch: {epoch_seconds})")
        except ValueError as e:
            logger.warning(f"Invalid timestamp format: {after_timestamp}, ignoring after filter")

    logger.info(f"Fetching emails with query: '{query}', max_results: {max_results}")
    start_time = time.time()
    metrics = get_metrics_tracker()

    try:
        # Execute Gmail API search query
        try:
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()

            elapsed = time.time() - start_time
            log_api_call(logger, "Gmail", True)
            metrics.record_api_call("Gmail", "list_messages", True, False, elapsed)

        except HttpError as e:
            error_msg = f"Gmail API error while listing messages: {e}"
            logger.error(error_msg)
            metrics.record_error(__name__, "HttpError", error_msg)
            raise EmailFetchError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error while listing messages: {e}"
            logger.error(error_msg)
            metrics.record_error(__name__, type(e).__name__, error_msg)
            raise EmailFetchError(error_msg)

        messages = results.get('messages', [])
        email_list = []

        if not messages:
            logger.info('No new messages found.')
            print('No new messages found.')
            return email_list

        logger.info(f"Found {len(messages)} emails. Fetching content...")
        print(f"Found {len(messages)} emails. Fetching content...\n")

        # Extract metadata from each message
        for idx, message in enumerate(messages, 1):
            try:
                msg_start_time = time.time()

                msg = service.users().messages().get(
                    userId='me',
                    id=message['id']
                ).execute()

                msg_elapsed = time.time() - msg_start_time
                metrics.record_api_call("Gmail", "get_message", True, False, msg_elapsed)

                # Parse email headers
                headers = msg.get('payload', {}).get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')

                # Get snippet (preview text)
                snippet = msg.get('snippet', '')

                # Create structured email dictionary
                email_dict = {
                    'id': message['id'],
                    'from': sender,
                    'subject': subject,
                    'date': date,
                    'snippet': snippet
                }

                email_list.append(email_dict)
                logger.debug(f"Fetched email {idx}/{len(messages)}: {subject[:50]}")

            except HttpError as e:
                logger.warning(f"Failed to fetch email {message['id']}: {e}")
                metrics.record_error(__name__, "HttpError", f"Failed to fetch email: {e}")
                continue
            except Exception as e:
                logger.warning(f"Unexpected error fetching email {message['id']}: {e}")
                metrics.record_error(__name__, type(e).__name__, f"Unexpected error: {e}")
                continue

        elapsed = time.time() - start_time
        log_performance(logger, f"Fetch {len(email_list)} emails", elapsed)
        logger.info(f"Successfully fetched {len(email_list)} emails in {elapsed:.2f}s")

        return email_list

    except Exception as e:
        elapsed = time.time() - start_time
        log_exception(logger, e, "Email fetching failed")
        log_api_call(logger, "Gmail", False)
        metrics.record_api_call("Gmail", "fetch_emails", False, False, elapsed)
        if not isinstance(e, EmailFetchError):
            metrics.record_error(__name__, type(e).__name__, str(e))
        raise


def extract_email_body(service: Any, email_id: str) -> str:
    """
    Extract full email body content from a specific email.

    Handles multipart MIME messages, preferring plain text over HTML.
    Decodes base64-encoded content and strips HTML tags when necessary.

    Args:
        service: Authenticated Gmail API service instance
        email_id: Gmail message ID

    Returns:
        str: Full email body as plain text. Returns empty string on error.

    Note:
        - Prefers text/plain over text/html
        - Handles nested multipart messages
        - Removes HTML tags from HTML content
        - Falls back to snippet if body extraction fails
    """
    logger.debug(f"Extracting body for email: {email_id}")
    start_time = time.time()
    metrics = get_metrics_tracker()

    try:
        # Fetch full email message
        try:
            msg = service.users().messages().get(
                userId='me',
                id=email_id,
                format='full'
            ).execute()

            elapsed = time.time() - start_time
            metrics.record_api_call("Gmail", "get_message_full", True, False, elapsed)

        except HttpError as e:
            logger.error(f"Gmail API error extracting body for {email_id}: {e}")
            metrics.record_error(__name__, "HttpError", f"Failed to extract email body: {e}")
            return ""
        except Exception as e:
            logger.error(f"Unexpected error extracting body for {email_id}: {e}")
            metrics.record_error(__name__, type(e).__name__, f"Unexpected error: {e}")
            return ""

        def decode_base64(data: str) -> str:
            """Decode base64-encoded email content."""
            try:
                return base64.urlsafe_b64decode(data).decode('utf-8')
            except Exception as e:
                logger.warning(f"Failed to decode base64 content: {e}")
                return ""

        payload = msg.get('payload', {})

        # Check if body is directly in payload (simple emails)
        if 'body' in payload and payload['body'].get('data'):
            body = decode_base64(payload['body']['data'])
            logger.debug(f"Extracted body (direct) for {email_id}: {len(body)} chars")
            return body

        # Handle multipart messages (emails with attachments or HTML)
        if 'parts' in payload:
            # First pass: look for plain text
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain' and part.get('body', {}).get('data'):
                    body = decode_base64(part['body']['data'])
                    logger.debug(f"Extracted body (text/plain) for {email_id}: {len(body)} chars")
                    return body

            # Second pass: fall back to HTML if plain text not found
            for part in payload['parts']:
                if part.get('mimeType') == 'text/html' and part.get('body', {}).get('data'):
                    html_content = decode_base64(part['body']['data'])
                    # Strip HTML tags using regex
                    text = re.sub('<[^<]+?>', '', html_content)
                    logger.debug(f"Extracted body (text/html) for {email_id}: {len(text)} chars")
                    return text

                # Check nested parts (e.g., multipart/alternative)
                if 'parts' in part:
                    for subpart in part['parts']:
                        if subpart.get('mimeType') == 'text/plain' and subpart.get('body', {}).get('data'):
                            body = decode_base64(subpart['body']['data'])
                            logger.debug(f"Extracted body (nested) for {email_id}: {len(body)} chars")
                            return body

        # Fallback: return snippet if body extraction failed
        snippet = msg.get('snippet', '')
        logger.warning(f"Could not extract full body for {email_id}, using snippet: {len(snippet)} chars")
        return snippet

    except Exception as e:
        log_exception(logger, e, f"Error extracting email body for {email_id}")
        metrics.record_error(__name__, type(e).__name__, f"Error extracting email body: {e}")
        return ""


def display_emails(email_list: List[Dict[str, str]]) -> None:
    """
    Display emails in a clean, formatted console output.

    Shows email metadata (ID, sender, subject, date, snippet) in a
    readable 80-character wide format.

    Args:
        email_list: List of email dictionaries from fetch_recent_emails()

    Output:
        Prints formatted email list to console with:
        - Email count header
        - Numbered list of emails
        - Truncated snippets (150 characters)
        - Visual separators
    """
    try:
        if not email_list:
            logger.info("No emails to display")
            print("No emails to display.")
            return

        logger.info(f"Displaying {len(email_list)} emails")
        print("\n" + "=" * 80)
        print(f"DISPLAYING {len(email_list)} EMAILS")
        print("=" * 80 + "\n")

        for idx, email in enumerate(email_list, 1):
            print(f"Email #{idx}")
            print(f"  ID: {email.get('id', 'N/A')}")
            print(f"  From: {email.get('from', 'Unknown')}")
            print(f"  Subject: {email.get('subject', 'No Subject')}")
            print(f"  Date: {email.get('date', 'Unknown Date')}")
            snippet = email.get('snippet', '')
            print(f"  Snippet: {snippet[:150]}...")  # First 150 chars
            print("-" * 80)

        print("\n")

    except Exception as e:
        logger.error(f"Error displaying emails: {e}")
        print(f"⚠️  Error displaying emails: {e}")
