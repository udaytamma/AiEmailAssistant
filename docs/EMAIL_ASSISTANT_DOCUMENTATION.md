# Email Assistant - Project Documentation

**Version:** 1.0
**Date:** December 17, 2025
**Status:** Phase 1 Complete (Email Fetching & AI Categorization)

---

## Table of Contents

1. [Project Goal](#project-goal)
2. [Project Roadmap](#project-roadmap)
3. [Current Implementation Status](#current-implementation-status)
4. [Technical Architecture](#technical-architecture)
5. [Configuration & Setup](#configuration--setup)
6. [GenAI Prompts](#genai-prompts)
7. [API Reference](#api-reference)
8. [Rate Limits & Quotas](#rate-limits--quotas)
9. [Next Steps](#next-steps)

---

## Project Goal

Build an **AI-Powered Email Executive Assistant** that automatically:

- Fetches unread emails from Gmail
- Categorizes emails using Gemini AI (Google's LLM)
- Executes automated actions based on categories:
  - Add bills to Google Calendar
  - Create notes for service changes
  - Flag emails for unsubscribe
  - Delete spam automatically
- Sends a daily summary email with actionable insights

**End Result:** Instead of manually triaging your inbox, the assistant reads, categorizes, performs digital chores, and delivers a concise daily digest.

---

## Project Roadmap

### Phase 1: Email Fetching & AI Categorization ✅ COMPLETE

- [x] Connect to Gmail API
- [x] Fetch unread emails (last 24 hours, max 10)
- [x] Extract email metadata (from, subject, date, snippet)
- [x] Display emails in structured format
- [x] Integrate Gemini AI for categorization
- [x] Implement rate limiting for API quotas
- [x] Display categorized summary

### Phase 2: Automated Actions (PENDING)

- [ ] Google Calendar integration for bill due dates
- [ ] Google Keep/Notes integration for service changes
- [ ] Auto-flag emails for unsubscribe
- [ ] Auto-delete spam emails
- [ ] Track package delivery updates

### Phase 3: Summary Email Generation (PENDING)

- [ ] Generate HTML summary email
- [ ] Include action items and FYI sections
- [ ] Send summary via Gmail API
- [ ] Schedule automated runs (2x daily: 8 AM & 6 PM)

### Phase 4: Memory & Context (PENDING)

- [ ] Implement log.json for rolling context
- [ ] Track email threads and conversations
- [ ] Learn user preferences over time
- [ ] Handle "Re:" emails with historical context

### Phase 5: Deployment (PENDING)

- [ ] Deploy to Google Cloud Functions
- [ ] Set up Cloud Scheduler for automation
- [ ] Configure monitoring and alerts
- [ ] Production security hardening

---

## Current Implementation Status

### ✅ Completed Features

**1. Gmail Integration**
- OAuth 2.0 authentication with `credentials.json`
- Token management (`token.json`)
- Fetch unread emails from last 24 hours (max 10)
- Extract: from, subject, date, snippet, email ID

**2. Email Display**
- Clean console output with 80-character formatting
- Truncated snippets (150 characters)
- Numbered email list with metadata

**3. Gemini AI Categorization**
- Model: `gemini-2.5-flash-lite`
- Categories: Need-Action, FYI, Newsletter, Marketing, SPAM
- Subcategories: Bill-Due, Credit-Card-Payment, Service-Change, Package-Tracker, JobAlert, General
- Action Items: AddToCalendar, AddToNotes, Unsubscribe, Delete, None
- One-sentence summary generation

**4. Rate Limiting**
- Automatic handling of API quotas
- 10 requests/minute (gemini-2.5-flash-lite free tier)
- 7-second delay between requests

**5. Categorized Summary**
- Groups emails by category
- Displays subject, sender, action, and summary
- Easy-to-read console output

---

## Technical Architecture

### Tech Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Language | Python | 3.11+ |
| Gmail API | `google-api-python-client` | 2.187.0 |
| Authentication | `google-auth-oauthlib` | 1.2.3 |
| AI Model | Gemini 2.5 Flash Lite | Latest |
| AI SDK | `google-generativeai` | 0.8.6 |
| Environment | Virtual Environment (.venv) | - |

### System Architecture

```
┌─────────────────┐
│   Gmail API     │
│  (OAuth 2.0)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│  Email Fetch    │─────▶│  Email Display   │
│  (fetch_recent) │      │  (display_emails)│
└────────┬────────┘      └──────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│       Gemini AI Categorization      │
│  (categorize_emails + rate limit)   │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│      Categorized Summary Display    │
│    (display_categorized_summary)    │
└─────────────────────────────────────┘
```

### File Structure

```
emailAssistant/
├── .venv/                      # Virtual environment
├── EmailAssistant.py           # Main application
├── credentials.json            # Gmail API credentials
├── token.json                  # OAuth access/refresh tokens
├── fetch_email.py              # Legacy fetch script
└── fetch_emails.py             # Legacy IMAP script
```

### Key Functions

| Function | Purpose | Location |
|----------|---------|----------|
| `connect_to_gmail()` | Authenticate with Gmail API | Line 100-126 |
| `fetch_recent_emails(service)` | Fetch & parse emails | Line 128-170 |
| `display_emails(email_list)` | Display email list | Line 172-193 |
| `categorize_email_with_gemini(email, model)` | Categorize single email | Line 195-255 |
| `categorize_emails(email_list, model)` | Categorize all with rate limiting | Line 257-301 |
| `display_categorized_summary(emails)` | Show grouped summary | Line 303-328 |

---

## Configuration & Setup

### Prerequisites

1. **Google Cloud Project** with Gmail API enabled
2. **OAuth 2.0 Credentials** (`credentials.json`)
3. **Gemini API Key** from [Google AI Studio](https://aistudio.google.com/app/apikey)
4. **Python 3.11+** with virtual environment

### Installation Steps

```bash
# 1. Create virtual environment
python3 -m venv .venv

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Install dependencies
pip install google-api-python-client google-auth-oauthlib google-generativeai

# 4. Set environment variable
export GOOGLE_API_KEY='your_gemini_api_key_here'

# 5. Run the script
python EmailAssistant.py
```

### Gmail API Scopes

```python
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
```

This scope allows:
- Reading emails
- Modifying labels
- Trashing emails
- Sending emails (for future summary feature)

### Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `GOOGLE_API_KEY` | Yes | Gemini API authentication |
| `GEMINI_API_KEY` | Alternative | Fallback for Gemini API |

---

## GenAI Prompts

### Email Categorization Prompt

**Location:** `EmailAssistant.py:202-224`

**Purpose:** Instruct Gemini AI to categorize emails and return structured JSON

**Full Prompt:**

```
Analyze the following email and respond ONLY with a valid JSON object (no markdown, no code blocks, just pure JSON):

From: {email_dict['from']}
Subject: {email_dict['subject']}
Content: {email_dict['snippet']}

Respond with this exact JSON structure:
{
  "category": "<one of: Need-Action, FYI, Newsletter, Marketing, SPAM>",
  "subcategory": "<one of: Bill-Due, Credit-Card-Payment, Service-Change, Package-Tracker, JobAlert, General>",
  "summary": "<one sentence summary>",
  "action_item": "<one of: AddToCalendar, AddToNotes, Unsubscribe, Delete, None>",
  "date_due": "<date if applicable, otherwise null>"
}

Classification Rules:
- Need-Action: Requires user response (bills, important tasks)
- FYI: Information only (receipts, updates, confirmations, package delivery updates, Online orders)
- Marketing: Promotional content
- Newsletters : Newsletters
- SPAM: Unwanted content, suspecious emails

Only return the JSON object, nothing else.
```

**Prompt Engineering Techniques Used:**

1. **Clear Output Format:** Explicitly requests JSON with no markdown
2. **Structured Schema:** Provides exact field names and allowed values
3. **Few-Shot Classification:** Defines each category with examples
4. **Constraint Enforcement:** "Only return the JSON object, nothing else"
5. **Dynamic Variable Injection:** Uses f-strings for email data

**Response Parsing:**

```python
# Strip markdown code blocks
if response_text.startswith('```json'):
    response_text = response_text[7:]
if response_text.startswith('```'):
    response_text = response_text[3:]
if response_text.endswith('```'):
    response_text = response_text[:-3]

# Parse JSON
categorization = json.loads(response_text)
```

### Category Definitions

| Category | Definition | Example |
|----------|------------|---------|
| **Need-Action** | Requires user response | Bill payment due, meeting RSVP |
| **FYI** | Informational only | Order confirmations, receipts, package updates |
| **Newsletter** | Subscribed content | Tech newsletters, digest emails |
| **Marketing** | Promotional content | Sales, product launches |
| **SPAM** | Unwanted/suspicious | Phishing, unsolicited ads |

### Subcategory Definitions

| Subcategory | Definition | Suggested Action |
|-------------|------------|------------------|
| **Bill-Due** | Payment required | AddToCalendar |
| **Credit-Card-Payment** | Payment confirmation | None |
| **Service-Change** | Service updates | AddToNotes |
| **Package-Tracker** | Delivery updates | None |
| **JobAlert** | Job postings | None |
| **General** | Other emails | None |

---

## API Reference

### Gmail API

**Endpoint:** `users().messages().list()`

**Query Parameters:**
```python
userId='me'                    # Current authenticated user
q='is:unread newer_than:1d'   # Search query
maxResults=10                  # Limit results
```

**Response Structure:**
```python
{
    'id': '19b28526e246922e',
    'from': 'sender@example.com',
    'subject': 'Email Subject',
    'date': 'Tue, 16 Dec 2025 18:00:47 +0000',
    'snippet': 'Email preview text...'
}
```

### Gemini API

**Model:** `gemini-2.5-flash-lite`

**Method:** `model.generate_content(prompt)`

**Configuration:**
```python
import google.generativeai as genai
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash-lite')
```

**Response:**
```python
response = model.generate_content(prompt)
response_text = response.text  # Extract text
```

---

## Rate Limits & Quotas

### Gemini API Free Tier Limits

| Model | Requests/Minute | Current Setting |
|-------|----------------|-----------------|
| gemini-2.5-flash-lite | 10 | 10 RPM |
| Delay Between Requests | - | 7 seconds |

**Rate Limiting Implementation:**

```python
requests_per_minute = 10
delay_between_requests = 60 / requests_per_minute + 1  # ~7 seconds

# Wait between requests
if idx < len(email_list):
    print(f"⏳ Waiting {delay_between_requests:.0f} seconds...")
    time.sleep(delay_between_requests)
```

**Handling Quota Errors:**

- Error caught in `try/except` block
- Returns fallback categorization: `{category: "Unknown"}`
- Logs error message to console

### Gmail API Quotas

| Quota | Free Tier Limit |
|-------|----------------|
| Queries per day | 1,000,000,000 |
| Queries per 100 seconds | 250 |

*Gmail quotas are generous and unlikely to be exceeded in normal usage.*

---

## Next Steps

### Immediate Next Phase: Automated Actions

**Priority 1: Google Calendar Integration**
- Function: `add_bill_to_calendar(email, date_due)`
- API: Google Calendar API v3
- Action: Create all-day event for bills

**Priority 2: Notes/Keep Integration**
- Function: `save_to_notes(email, content)`
- Storage: Google Keep or local JSON
- Action: Save service change notifications

**Priority 3: Email Actions**
- Function: `flag_for_unsubscribe(email_id)`
- Action: Apply Gmail label "To Unsubscribe"
- Function: `delete_spam(email_id)`
- Action: Move to trash via Gmail API

**Priority 4: Summary Email**
- Function: `generate_summary_email(categorized_emails)`
- Format: HTML with sections (Action Items, FYI, etc.)
- Delivery: Gmail API `users().messages().send()`

### Future Enhancements

1. **Memory System:** Track email threads in `log.json`
2. **Scheduling:** Google Cloud Functions + Cloud Scheduler (2x daily)
3. **Analytics:** Track categorization accuracy over time
4. **User Feedback Loop:** Allow manual recategorization to improve prompts
5. **Multi-Account Support:** Handle multiple Gmail accounts

---

## Appendix: Example Output

### Sample Categorization Results

```
### NEWSLETTER (4 emails)
--------------------------------------------------------------------------------
  • How to write the perfect prompt
    From: Lovable <noreply@lovable.dev>
    Action: None
    Summary: The email provides five tips on writing effective prompts.

### FYI (2 emails)
--------------------------------------------------------------------------------
  • University of Illinois Community CU - Transaction Notification
    From: University of Illinois Community CU
    Action: None
    Summary: Notification of a pending charge of $4.46 on your card.

### NEED-ACTION (1 email)
--------------------------------------------------------------------------------
  • Electric Bill Payment Due
    From: ComEd <billing@comed.com>
    Action: AddToCalendar
    Summary: Your electric bill of $127.45 is due on December 25, 2025.
```

---

**Document Version:** 1.0
**Last Updated:** December 17, 2025
**Project Status:** Phase 1 Complete - Ready for Phase 2 Implementation
