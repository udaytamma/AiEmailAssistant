# Product Requirements Document
## Email Assistant v2.1

**Document Version:** 1.0
**Last Updated:** December 19, 2025
**Product Owner:** Engineering Team
**Status:** Active Development

---

## 1. Executive Summary

Email Assistant is an intelligent email management system that leverages Google Gemini AI to automatically categorize, summarize, and triage Gmail emails. The application provides a web-based interface for reviewing AI-categorized emails and enables one-click actions for common email workflows (delete, mark as read, add to calendar, create tasks, unsubscribe).

**Core Value Proposition:**
- Reduce email processing time by 70% through AI-powered categorization
- Eliminate decision fatigue with intelligent email triaging
- Automate repetitive email actions with single-click workflows

---

## 2. Product Overview

### 2.1 Target Users
- Professionals managing 50+ emails daily
- Knowledge workers requiring email organization
- Users seeking inbox zero methodology

### 2.2 Key Features
1. **AI-Powered Email Categorization** - Gemini AI categorizes emails into 6 categories
2. **Interactive Email Review** - Web interface for reviewing and acting on categorized emails
3. **One-Click Actions** - Quick actions based on email category
4. **Comprehensive Logging** - Full audit trail of AI interactions and API calls
5. **Smart Summaries** - AI-generated one-sentence summaries for each email

---

## 3. Functional Requirements

### 3.1 Email Categorization

**FR-1.1: Category Classification**
- **Requirement:** System shall categorize emails into 6 categories using Gemini AI
- **Categories:**
  - **Need-Action** - Requires user response (bills, important tasks)
  - **FYI** - Information only (receipts, confirmations, package delivery)
  - **Newsletter** - Regular newsletters and digests
  - **Marketing** - Promotional content, sales, offers
  - **SPAM** - Unwanted or suspicious content
  - **Other** - Uncategorized emails

**FR-1.2: Subcategory Classification**
- **Requirement:** System shall assign subcategories for granular organization
- **Subcategories:** Bill-Due, Credit-Card-Payment, Service-Change, Package-Tracker, JobAlert, General

**FR-1.3: Email Summary Generation**
- **Requirement:** System shall generate one-sentence AI summary for each email
- **Success Criteria:** Summary accurately captures email intent in ≤15 words

**FR-1.4: Action Item Suggestion**
- **Requirement:** System shall suggest action items
- **Actions:** AddToCalendar, AddToNotes, Unsubscribe, Delete, None

**FR-1.5: SPAM Unsubscribe Extraction**
- **Requirement:** For SPAM emails, extract unsubscribe email address from message body
- **Success Criteria:** Identify and extract unsubscribe@domain.com format addresses

### 3.2 Web Interface

**FR-2.1: Gemini Email Review Page**
- **Requirement:** Display categorized emails in sortable table
- **Columns:** Sender, Subject Line, Summary, Category, Sub Category, Action Suggested, Action Taken
- **Pagination:** 10 emails per page
- **Refresh:** "Get Latest View" button to fetch and categorize fresh emails

**FR-2.2: Category-Based Actions**
- **Requirement:** Display action controls based on email category

| Category | Action Control | Behavior |
|----------|---------------|----------|
| FYI, Newsletter, Marketing | Delete Button | Moves email to Gmail trash |
| Need-Action | Dropdown Menu | 4 options: Add to Calendar, Add Task, Mark as Read, Delete |
| SPAM | Unsubscribe Link | Sends unsubscribe email to extracted address |

**FR-2.3: Action Execution**
- **Requirement:** Execute actions without confirmation dialogs
- **Post-Action Behavior:**
  - Email remains in table (no page refresh)
  - Action column updates to "Completed"
  - Errors display inline in Action column

**FR-2.4: Gemini Interaction Logs**
- **Requirement:** Display all Gemini AI interactions and API calls
- **Features:**
  - Date selector for historical logs
  - Search functionality across all log content
  - Operation filters (categorize, summary, API calls, errors)
  - Collapsible request/response sections
  - Statistics dashboard (total logs, avg latency, operation counts)
  - Latest logs displayed first

### 3.3 API Integration

**FR-3.1: Gmail API Operations**
- Delete email (messages.trash)
- Mark email as read (messages.modify)
- Send unsubscribe email (messages.send)

**FR-3.2: Google Calendar API**
- Create calendar events from emails (events.insert)

**FR-3.3: Google Tasks API**
- Create tasks from emails (tasks.insert)

### 3.4 Logging & Observability

**FR-4.1: Gemini Interaction Logging**
- **Requirement:** Log all Gemini AI interactions to daily-rotated log files
- **Data Captured:**
  - Timestamp (millisecond precision)
  - Operation type (categorize_email, generate_summary, etc.)
  - Full request prompt
  - Formatted response (parsed JSON)
  - Metadata (model name, latency, token count, category assigned)

**FR-4.2: API Call Logging**
- **Requirement:** Log all Gmail/Calendar/Tasks API modifications
- **Data Captured:**
  - API call syntax (formatted Python code)
  - Request data (JSON)
  - Response data (JSON)
  - Metadata (API name, method, latency, result IDs)

**FR-4.3: Log Rotation**
- **Requirement:** Create new log file daily at midnight
- **Naming Convention:** `gemini_interactions_YYYY-MM-DD.log`
- **Storage Location:** `logs/gemini/`

---

## 4. Non-Functional Requirements

### 4.1 Performance

**NFR-1.1: Email Processing**
- Categorize single email in ≤2 seconds (p95)
- Process 30 emails in ≤60 seconds (p95)

**NFR-1.2: Web Interface**
- Page load time ≤2 seconds
- Action execution response ≤1 second

**NFR-1.3: API Rate Limits**
- Gemini API: 30 requests/minute
- Gmail API: Respect Google API quotas

### 4.2 Reliability

**NFR-2.1: Error Handling**
- Graceful degradation on API failures
- Fallback categorization on Gemini errors
- Error logging for all exceptions

**NFR-2.2: Data Integrity**
- No email loss during processing
- Atomic API operations
- Transaction logging for audit trail

### 4.3 Security

**NFR-3.1: Authentication**
- OAuth 2.0 for Google API access
- Token refresh handling
- Credential encryption at rest

**NFR-3.2: Data Privacy**
- Email content not stored permanently
- Logs contain email metadata only (no full content)
- Local execution (no third-party data sharing)

### 4.4 Usability

**NFR-4.1: User Interface**
- Mobile-responsive design
- Intuitive navigation
- Clear visual feedback for all actions

**NFR-4.2: Documentation**
- Inline help for all features
- Error messages must be actionable

---

## 5. Technical Architecture

### 5.1 Technology Stack

**Backend:**
- Python 3.14
- Flask web framework
- Google AI Python SDK (Gemini)
- Google API Client Libraries (Gmail, Calendar, Tasks)

**Frontend:**
- HTML5, CSS3, JavaScript (Vanilla)
- Server-side rendering with Jinja2 templates

**Storage:**
- JSON files for digest data
- Text log files for audit trail
- SQLite for context memory (optional)

**APIs:**
- Google Gemini AI (gemini-2.5-flash-lite)
- Gmail API v1
- Google Calendar API v3
- Google Tasks API v1

### 5.2 System Components

```
┌─────────────────────────────────────────────────────────────┐
│                      Web Browser                             │
│  (Gemini Review UI, Gemini Logs UI, Dashboard)              │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/JSON
┌──────────────────────▼──────────────────────────────────────┐
│                  Flask Web Server                            │
│  Routes: /gemini-review, /gemini-logs, /api/*               │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼─────┐ ┌──────▼──────┐ ┌────▼─────────┐
│ Gemini AI   │ │ Gmail API   │ │ Calendar/    │
│ Service     │ │ Service     │ │ Tasks APIs   │
└─────────────┘ └─────────────┘ └──────────────┘
        │              │              │
        └──────────────┼──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │   Gemini Logger              │
        │   (Daily Rotation)           │
        └──────────────────────────────┘
```

---

## 6. Data Models

### 6.1 Categorized Email Object

```json
{
  "id": "19b2dc0dc7e9e1af",
  "from": "sender@example.com",
  "subject": "Email subject line",
  "date": "Wed, 17 Dec 2025 19:19:26 +0000",
  "snippet": "Email preview text...",
  "category": "Need-Action",
  "subcategory": "Bill-Due",
  "summary": "One-sentence AI-generated summary",
  "action_item": "AddToCalendar",
  "date_due": "2026-01-14",
  "unsubscribe_email": "unsubscribe@example.com"
}
```

### 6.2 Log Entry Object

```json
{
  "timestamp": "2025-12-18 16:52:45.123",
  "operation": "categorize_email",
  "metadata": {
    "model_name": "gemini-2.5-flash-lite",
    "latency_seconds": "0.847",
    "email_subject": "Your credit card statement...",
    "category": "Need-Action"
  },
  "request": "Analyze the following email...",
  "response": {
    "category": "Need-Action",
    "subcategory": "Credit-Card-Payment",
    "summary": "Statement available...",
    "action_item": "None",
    "date_due": "2026-01-14"
  }
}
```

---

## 7. User Workflows

### 7.1 Primary Workflow: Email Review

1. User opens Gemini Email Review page (`/gemini-review`)
2. User clicks "Get Latest View" button
3. System fetches 30 unread emails from Gmail
4. System sends each email to Gemini AI for categorization
5. System displays categorized emails in table with action controls
6. User clicks action button/dropdown for an email
7. System executes action (delete, mark read, add to calendar, etc.)
8. System updates Action column to "Completed" (no page refresh)
9. User continues processing emails

### 7.2 Secondary Workflow: Log Review

1. User opens Gemini Logs page (`/gemini-logs`)
2. User selects date from dropdown (default: today)
3. System loads logs for selected date
4. User filters by operation type or searches keywords
5. User clicks to expand/collapse request/response details
6. User reviews AI interactions and API calls for debugging/audit

---

## 8. API Endpoints

### 8.1 Web Pages

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard (main page) |
| `/gemini-review` | GET | Email review interface |
| `/gemini-logs` | GET | Gemini interaction logs |

### 8.2 API Routes

| Endpoint | Method | Description | Request | Response |
|----------|--------|-------------|---------|----------|
| `/api/gemini-review` | GET | Fetch and categorize emails | - | `{emails: [], timestamp, total}` |
| `/api/gemini-logs` | GET | Get log entries | `?date=YYYY-MM-DD` | `{entries: [], available_dates: []}` |
| `/api/email/delete` | POST | Delete email | `{email_id}` | `{success, message}` |
| `/api/email/mark-read` | POST | Mark email as read | `{email_id}` | `{success, message}` |
| `/api/email/add-calendar` | POST | Create calendar event | `{email_id, subject}` | `{success, message}` |
| `/api/email/add-task` | POST | Create task | `{email_id, subject}` | `{success, message}` |
| `/api/email/unsubscribe` | POST | Send unsubscribe email | `{email_id, unsubscribe_email}` | `{success, message}` |

---

## 9. Success Metrics

### 9.1 Product Metrics

- **Email Processing Time:** Average time to process inbox reduced by 70%
- **Categorization Accuracy:** ≥90% emails correctly categorized
- **User Actions:** Average 50+ email actions per session
- **Error Rate:** <2% API failures

### 9.2 Technical Metrics

- **Gemini API Latency:** p95 ≤2 seconds per email
- **Web Page Load Time:** p95 ≤2 seconds
- **Uptime:** 99% availability
- **Log Coverage:** 100% AI interactions logged

---

## 10. Future Enhancements

### 10.1 Planned Features (Roadmap)

**Phase 2 (Q1 2026):**
- Smart scheduling for calendar events (extract date/time from email)
- Bulk actions (select multiple emails)
- Custom category creation
- Email threading support

**Phase 3 (Q2 2026):**
- Natural language queries ("Show all bills due this month")
- Automation rules engine
- Mobile app (iOS/Android)
- Email analytics dashboard

**Phase 4 (Q3 2026):**
- Multi-account support
- Team collaboration features
- Email templates and canned responses
- Advanced filters and saved views

### 10.2 Technical Debt

- Migrate from JSON file storage to proper database
- Implement Redis caching for performance
- Add comprehensive unit test coverage (target: 80%)
- Containerize with Docker for easier deployment

---

## 11. Constraints & Assumptions

### 11.1 Constraints

- **API Quotas:** Limited by Google API quotas (Gmail, Calendar, Tasks)
- **Gemini Rate Limits:** 30 requests/minute for free tier
- **Local Execution:** Requires local Python environment
- **OAuth Setup:** Users must configure Google Cloud credentials

### 11.2 Assumptions

- Users have Gmail account with unread emails
- Users have Google Cloud project with enabled APIs
- Users run application on personal computer (not production server)
- Email content is in English (Gemini categorization optimized for English)

---

## 12. Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Gemini API quota exceeded | High | Medium | Implement rate limiting, batch processing |
| Gmail API authentication failure | High | Low | Token refresh logic, clear error messages |
| Incorrect email categorization | Medium | Medium | Fallback categories, user feedback loop |
| Performance degradation with 100+ emails | Medium | High | Pagination, parallel processing |
| Log file storage growth | Low | High | Implement log rotation, cleanup old logs |

---

## 13. Acceptance Criteria

### 13.1 Release Criteria

**Email Categorization:**
- ✅ Successfully categorizes emails into 6 categories
- ✅ Generates accurate one-sentence summaries
- ✅ Extracts unsubscribe emails from SPAM

**Web Interface:**
- ✅ Gemini Review page displays categorized emails
- ✅ Action controls render based on category
- ✅ Actions execute without confirmation
- ✅ Action column updates to "Completed" post-execution
- ✅ Errors display inline

**Logging:**
- ✅ All Gemini interactions logged
- ✅ All API calls logged with formatted syntax
- ✅ Logs rotate daily
- ✅ Gemini Logs page displays all logs
- ✅ Search and filter functionality works
- ✅ Latest logs appear first

**Integration:**
- ✅ Gmail API integration (delete, mark read, send)
- ✅ Calendar API integration (create events)
- ✅ Tasks API integration (create tasks)

---

## 14. Appendices

### 14.1 Glossary

- **Gemini AI:** Google's large language model for text generation and analysis
- **OAuth 2.0:** Authorization framework for secure API access
- **SPAM:** Unsolicited or unwanted email messages
- **Unread Email:** Email message not marked as read in Gmail
- **Categorization:** Process of classifying emails into predefined categories

### 14.2 References

- [Google Gemini AI Documentation](https://ai.google.dev/docs)
- [Gmail API Reference](https://developers.google.com/gmail/api)
- [Google Calendar API Reference](https://developers.google.com/calendar/api)
- [Google Tasks API Reference](https://developers.google.com/tasks)

### 14.3 Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-19 | Engineering Team | Initial PRD creation |

---

**Document Status:** ✅ Approved
**Next Review Date:** 2026-01-19
