# 📧 Email Digest Web Visualization

Beautiful web interface to view your daily email digest with real-time refresh capability.

## ✨ Features

- **Modern UI**: Professional, clean design with color-coded sections
- **Real-time Refresh**: Click "Get Latest View" to fetch and process latest emails
- **Metadata Display**: Shows last refresh time and execution duration
- **Expandable Newsletters**: Click to expand/collapse newsletter summaries
- **Responsive Design**: Works on desktop and mobile devices
- **Smart Caching**: Leverages existing cache system to minimize API calls
- **Single Instance Protection**: Prevents multiple simultaneous script executions

## 🚀 Quick Start

### 1. Start the Web Server

```bash
./start_server.sh
```

Or manually:

```bash
source .venv/bin/activate
export GOOGLE_API_KEY='your_api_key_here'
python digest_server.py
```

### 2. Access the Digest

Open your browser and navigate to:
```
http://localhost:8001
```

### 3. Refresh the Digest

Click the **"Get Latest View"** button to:
- Fetch latest emails from Gmail
- Categorize using Gemini AI
- Generate detailed summaries
- Update the display automatically

## 📁 Files Created

### Backend
- **`digest_server.py`** - Flask web server
  - Serves HTML page
  - Provides REST API endpoints
  - Manages script execution with lock files

### Frontend
- **`templates/digest.html`** - Main HTML template
- **`static/style.css`** - Professional styling
- **`static/script.js`** - Interactive functionality

### Data
- **`digest_data.json`** - Stores digest data with metadata

### Scripts
- **`start_server.sh`** - Convenient server startup script

## 🎨 UI Sections

### Header
- **Logo**: Email Digest branding
- **Last Refreshed**: Timestamp of last digest generation
- **Execution Time**: How long the script took to run
- **Get Latest View Button**: Triggers email processing

### Need Action Section (🔴 Red)
- Urgent emails requiring response
- Consolidated bullet-point summary
- Email count badge

### FYI Section (ℹ️ Blue)
- Informational emails
- Consolidated bullet-point summary
- Email count badge

### Newsletters Section (📰 Purple)
- Newsletter emails with detailed summaries
- Expandable cards (click to show/hide)
- 3 bullet points per newsletter
- Sender information

## 🔄 How It Works

### Data Flow

1. **EmailAssistant.py** runs and:
   - Fetches emails from Gmail
   - Categorizes with Gemini AI
   - Generates summaries
   - Saves to `digest_data.json` with metadata

2. **Web Page** loads and:
   - Fetches data from `/api/digest`
   - Renders sections dynamically
   - Displays metadata

3. **"Get Latest View" button** clicked:
   - Creates lock file (`script.lock`)
   - Runs EmailAssistant.py in background thread
   - Shows loading overlay
   - Polls `/api/status` every 2 seconds
   - Removes lock file when complete
   - Auto-refreshes page with new data

### API Endpoints

#### `GET /`
- Serves the main HTML page

#### `GET /api/digest`
- Returns current digest data as JSON
- Returns 404 if no data available

#### `POST /api/refresh`
- Triggers EmailAssistant.py execution
- Returns 409 if already running
- Returns 200 with "started" status

#### `GET /api/status`
- Checks if script is running
- Returns `{"running": true/false}`

## 🎯 Technical Details

### Lock File Mechanism
- **File**: `script.lock`
- **Purpose**: Prevent simultaneous executions
- **Created**: When refresh starts
- **Removed**: When execution completes or fails
- **Contains**: ISO timestamp of start time

### Execution Time Tracking
- Start time recorded at beginning of `main()`
- End time captured before JSON save
- Precision: 2 decimal places (e.g., "13.21s")

### Caching Integration
- Uses existing cache system from EmailAssistant.py
- Newsletter summaries cached by email ID
- Category summaries cached by email ID combination
- Typical second run: 0 API calls (100% cached)

## 🎨 Design System

### Colors
- **Primary**: Blue (`#3b82f6`) - Main actions, FYI section
- **Urgent**: Red (`#ef4444`) - Need-Action section
- **Newsletter**: Purple (`#8b5cf6`) - Newsletter section
- **Success**: Green (`#10b981`) - Success states
- **Background**: Light gray (`#f8fafc`)
- **Surface**: White (`#ffffff`)

### Typography
- **Font**: System fonts (San Francisco, Segoe UI, etc.)
- **Headings**: Bold, size hierarchy
- **Body**: Regular weight, 1.6 line-height

### Spacing
- Consistent 0.5rem increments
- Card padding: 1.5rem
- Section gaps: 2rem

## 🔧 Configuration

### Port Number
Default: `8001`

To change, edit `digest_server.py`:
```python
app.run(host='0.0.0.0', port=8001, debug=True)
```

### Polling Interval
Default: 2 seconds

To change, edit `static/script.js`:
```javascript
checkStatusInterval = setInterval(checkRefreshStatus, 2000);
```

### API Key
Set in environment or `digest_server.py`:
```python
env['GOOGLE_API_KEY'] = 'your_key_here'
```

## 🐛 Troubleshooting

### Server Won't Start
- Check if port 8001 is already in use:
  ```bash
  lsof -i :8001
  ```
- Kill existing process if needed:
  ```bash
  kill -9 <PID>
  ```

### "No digest data available" Error
- Run EmailAssistant.py first to generate initial data:
  ```bash
  source .venv/bin/activate
  export GOOGLE_API_KEY='your_key'
  python EmailAssistant.py
  ```

### Button Stuck on "Refreshing..."
- Check if lock file exists:
  ```bash
  ls script.lock
  ```
- Remove if stale:
  ```bash
  rm script.lock
  ```
- Refresh browser page

### Script Takes Too Long
- Check console logs in `digest_server.py` terminal
- Verify Gmail API and Gemini API are accessible
- Check cache statistics - may need to clear cache

## 📊 Performance

### Typical Execution Times
- **First run** (no cache): 13-20 seconds (10 emails)
- **Second run** (cached): 5-8 seconds (100% cached)
- **Page load**: < 1 second
- **Status polling**: 2 second intervals

### API Calls (per refresh)
- **First run**: 10-15 calls
  - 10 email categorizations
  - 2 category summaries
  - 3-7 newsletter summaries
- **Cached run**: 0-3 calls
  - Only new emails processed

## 🔮 Future Enhancements

Potential improvements:
- User authentication
- Multiple user support
- Email search and filtering
- Historical digest archive
- Email action buttons (archive, delete, reply)
- WebSocket for real-time updates
- Progressive Web App (PWA) support
- Dark mode toggle
- Export digest as PDF/email

## 📝 Notes

- Flask runs in debug mode for development
- For production, use a WSGI server like Gunicorn
- Consider adding HTTPS for production deployment
- Lock file mechanism is single-user; use Redis for multi-user

---

**Version**: 1.0
**Last Updated**: January 12, 2026
**Requires**: Flask, Python 3.11+, Virtual environment
