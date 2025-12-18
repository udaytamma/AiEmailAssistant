"""
Email Utility Functions
Handles Gmail API authentication, email fetching, and email body extraction
"""

import os
import os.path
import base64
import re
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Gmail API scopes - allows reading, modifying labels, and trashing emails
# If modifying these scopes, delete the file token.json
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']


def connect_to_gmail():
    """
    Authenticate and connect to Gmail API using OAuth 2.0.

    Uses credentials.json for initial authentication and stores tokens in token.json
    for subsequent runs. Automatically refreshes expired tokens.

    Returns:
        service: Authenticated Gmail API service instance

    Raises:
        FileNotFoundError: If credentials.json is missing
    """
    creds = None

    # Load existing credentials from token.json if available
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # If no valid credentials, initiate OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Refresh expired token
            creds.refresh(Request())
        else:
            # New authentication flow using credentials.json
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # Save credentials for next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    # Build and return Gmail API service
    service = build('gmail', 'v1', credentials=creds)
    return service


def fetch_recent_emails(service, max_results=10, query='is:unread newer_than:1d'):
    """
    Fetch recent unread emails from Gmail.

    Retrieves emails matching the search query and extracts metadata
    (sender, subject, date, snippet, ID) for each message.

    Args:
        service: Authenticated Gmail API service instance
        max_results: Maximum number of emails to fetch (default: 10)
        query: Gmail search query (default: unread emails from last 24 hours)

    Returns:
        list: List of email dictionaries, each containing:
            - id: Email message ID
            - from: Sender email address
            - subject: Email subject line
            - date: Email date/time
            - snippet: Email preview text (first ~150 chars)

    Example:
        emails = fetch_recent_emails(service, max_results=5)
        for email in emails:
            print(f"From: {email['from']}, Subject: {email['subject']}")
    """
    # Execute Gmail API search query
    results = service.users().messages().list(
        userId='me',
        q=query,
        maxResults=max_results
    ).execute()

    messages = results.get('messages', [])
    email_list = []

    if not messages:
        print('No new messages found.')
        return email_list

    print(f"Found {len(messages)} emails. Fetching content...\n")

    # Extract metadata from each message
    for message in messages:
        msg = service.users().messages().get(
            userId='me',
            id=message['id']
        ).execute()

        # Parse email headers
        headers = msg['payload']['headers']
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

    return email_list


def extract_email_body(service, email_id):
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
    try:
        # Fetch full email message
        msg = service.users().messages().get(
            userId='me',
            id=email_id,
            format='full'
        ).execute()

        def decode_base64(data):
            """Decode base64-encoded email content."""
            try:
                return base64.urlsafe_b64decode(data).decode('utf-8')
            except Exception:
                return ""

        payload = msg.get('payload', {})

        # Check if body is directly in payload (simple emails)
        if 'body' in payload and payload['body'].get('data'):
            return decode_base64(payload['body']['data'])

        # Handle multipart messages (emails with attachments or HTML)
        if 'parts' in payload:
            # First pass: look for plain text
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain' and part.get('body', {}).get('data'):
                    return decode_base64(part['body']['data'])

            # Second pass: fall back to HTML if plain text not found
            for part in payload['parts']:
                if part.get('mimeType') == 'text/html' and part.get('body', {}).get('data'):
                    html_content = decode_base64(part['body']['data'])
                    # Strip HTML tags using regex
                    text = re.sub('<[^<]+?>', '', html_content)
                    return text

                # Check nested parts (e.g., multipart/alternative)
                if 'parts' in part:
                    for subpart in part['parts']:
                        if subpart.get('mimeType') == 'text/plain' and subpart.get('body', {}).get('data'):
                            return decode_base64(subpart['body']['data'])

        # Fallback: return snippet if body extraction failed
        return msg.get('snippet', '')

    except Exception as e:
        print(f"⚠️  Error extracting email body: {e}")
        return ""


def display_emails(email_list):
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
    if not email_list:
        print("No emails to display.")
        return

    print("\n" + "=" * 80)
    print(f"DISPLAYING {len(email_list)} EMAILS")
    print("=" * 80 + "\n")

    for idx, email in enumerate(email_list, 1):
        print(f"Email #{idx}")
        print(f"  ID: {email['id']}")
        print(f"  From: {email['from']}")
        print(f"  Subject: {email['subject']}")
        print(f"  Date: {email['date']}")
        print(f"  Snippet: {email['snippet'][:150]}...")  # First 150 chars
        print("-" * 80)

    print("\n")
