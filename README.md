# 📧 AI-Powered Email Executive Assistant

Professional email management system with AI-powered categorization, daily digests, and comprehensive observability.

## ✨ Features

- **Gmail Integration**: OAuth 2.0 secure authentication
- **AI Categorization**: Gemini 2.5 Flash Lite for intelligent email sorting
- **Daily Digest**: Consolidated summaries with newsletter highlights
- **Web Interface**: Beautiful, responsive UI with real-time refresh
- **Caching System**: LRU cache (max 30 emails, 24h expiry)
- **Observability**: Comprehensive metrics tracking with SQLite
- **Error Handling**: Graceful degradation with detailed logging
- **Configuration**: JSON-based centralized settings

## 📊 Tracked Metrics

The system tracks **12+ comprehensive metrics** across 24h, 7d, and all-time:

1. **Total Emails Processed** - Total count by period
2. **Cache Hit Rate** - Percentage of cache hits vs misses
3. **API Calls Made** - Number of Gemini API calls
4. **Average Execution Time** - Script execution duration
5. **Emails by Category** - Breakdown (Need-Action, FYI, Newsletter, etc.)
6. **Success Rate** - Percentage of successful runs
7. **Script Run Count** - Number of executions
8. **Error Count** - Errors in last 24h
9. **Average API Response Time** - API performance
10. **Estimated API Cost** - Cost tracking at $0.01 per call
11. **Cache Utilization** - Current vs max size
12. **Recent Errors** - Last 10 errors with timestamps

Access metrics via the web interface by clicking the **"Metrics"** button!

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt

# For development and testing
pip install -r requirements-dev.txt
```

### 2. Configure Gmail API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable Gmail API
4. Create OAuth 2.0 credentials
5. Download `credentials.json` to project root

### 3. Set API Key

```bash
export GOOGLE_API_KEY='your_gemini_api_key_here'
```

Get your key from: https://aistudio.google.com/app/apikey

### 4. Run the Application

**Option A: Command Line**
```bash
python src/main.py
```

**Option B: Web Interface**
```bash
./scripts/start_server.sh
# or
python src/web/server.py
```

Then open: **http://localhost:8001**

## 📁 Project Structure

```
emailAssistant/
├── src/
│   ├── main.py                 # Main application entry point
│   ├── utils/                  # Utility modules
│   │   ├── email_utils.py      # Gmail API operations
│   │   ├── gemini_utils.py     # Gemini AI operations
│   │   ├── display_utils.py    # Digest generation
│   │   ├── logger_utils.py     # Logging configuration
│   │   └── metrics_utils.py    # Metrics tracking (SQLite)
│   ├── core/                   # Core modules
│   │   ├── config_manager.py   # Configuration management
│   │   └── cache_manager.py    # Cache management (LRU)
│   └── web/                    # Web interface
│       ├── server.py           # Flask server
│       ├── templates/          # HTML templates
│       │   ├── digest.html     # Main digest page
│       │   └── test_results.html  # Test results page
│       └── static/             # CSS and JavaScript
│           ├── style.css       # Professional styling
│           ├── script.js       # Interactive functionality
│           ├── test_style.css  # Test page styling
│           └── test_script.js  # Test page functionality
├── tests/                      # Testing suite
│   ├── conftest.py             # Test fixtures and utilities
│   ├── fixtures/               # Test data (sample emails, responses)
│   ├── integration/            # Integration tests
│   │   └── test_email_flow.py  # End-to-end workflow tests
│   └── unit/                   # Unit tests
│       ├── test_cache_manager.py    # Cache tests
│       ├── test_email_utils.py      # Email utils tests
│       ├── test_display_utils.py    # Display utils tests
│       └── test_api_contracts.py    # API contract tests
├── config/
│   └── config.json             # Configuration file
├── data/
│   ├── cache/                  # Email cache (JSON)
│   ├── digest/                 # Digest data (JSON)
│   ├── metrics/                # Metrics database (SQLite)
│   └── test_results/           # Test execution results (JSON)
├── logs/
│   └── email_assistant.log     # Application logs
├── docs/                       # Additional documentation
├── scripts/
│   └── start_server.sh         # Server startup script
├── requirements.txt            # Python dependencies
├── requirements-dev.txt        # Development dependencies
├── run_tests.py                # Test runner script
├── pytest.ini                  # Pytest configuration
└── README.md                   # This file
```

## ⚙️ Configuration

Edit `config/config.json` to customize:

```json
{
  "api_settings": {
    "gemini_model": "gemini-2.5-flash-lite",
    "requests_per_minute": 30,
    "max_retries": 3,
    "timeout_seconds": 30
  },
  "gmail_settings": {
    "max_emails_to_fetch": 10,
    "search_query": "is:unread newer_than:1d"
  },
  "cache_settings": {
    "enabled": true,
    "max_cached_emails": 30,
    "cache_expiry_hours": 24
  }
}
```

## 📝 Logging

Logs are written to `logs/email_assistant.log` with:
- **Timestamp** - ISO format with timezone
- **Log Level** - INFO, WARNING, ERROR
- **Module** - Source module name
- **Function:Line** - Exact code location
- **Message** - Detailed description
- **Stack Trace** - Full traceback for errors

**Log Level**: INFO by default (configurable in logger_utils.py)

## 🔍 Observability

### Metrics Dashboard
Access via the **"Metrics"** button in the web interface:
- **Tabs**: Last 24 Hours, Last 7 Days, All Time
- **Cards**: Visual metric cards with values and units
- **Categories**: Email breakdown by type (all-time view)

### Error Tracking
Recent errors appear automatically at the bottom of the digest page:
- **Timestamp** - When the error occurred
- **Module** - Where it happened
- **Error Type** - Exception type
- **Message** - Error description

### API Endpoints
- `GET /api/digest` - Current digest data
- `POST /api/refresh` - Trigger email processing
- `GET /api/status` - Check if script is running
- `GET /api/metrics` - Get all metrics
- `GET /api/errors` - Get recent errors

## 🐛 Troubleshooting

### No digest data available
Run the main script first to generate initial data:
```bash
python src/main.py
```

### Lock file stuck
If the "Refreshing..." button won't reset:
```bash
rm script.lock
```
Then refresh the browser page.

### Permission errors
Ensure directories exist and are writable:
```bash
mkdir -p data/cache data/digest data/metrics logs config
chmod -R 755 data logs config
```

### Server won't start (port conflict)
Check if port 8001 is in use:
```bash
lsof -i :8001
kill -9 <PID>  # If needed
```

### Import errors
Ensure you're in the project root and virtual environment is activated:
```bash
cd /Users/omega/Projects/emailAssistant
source .venv/bin/activate
```

### API quota exceeded
- Check cache hit rate in metrics
- Reduce `max_emails_to_fetch` in config
- Increase `cache_expiry_hours` to retain cache longer

## 🧪 Testing

### Running Tests

The application includes a comprehensive testing suite with 55+ tests:

**Quick Test Suites**:
```bash
# Basic tests (fast, most critical - ~10-20 seconds)
python run_tests.py basic

# Extended tests (moderate coverage - ~30-45 seconds)
python run_tests.py extended

# Comprehensive tests (full coverage - ~1-2 minutes)
python run_tests.py comprehensive
```

**Web Interface**:
1. Start the web server: `python src/web/server.py`
2. Navigate to: http://localhost:8001/tests
3. Click test suite buttons to run and view results

**Using pytest directly**:
```bash
# Run all tests
pytest -v

# Run only basic tests
pytest -v -m basic

# Run with coverage report
pytest -v --cov=src --cov-report=html
```

### Test Coverage

- **Integration Tests**: End-to-end workflows
- **Unit Tests**: Cache manager, email utils, display utils
- **Contract Tests**: Gemini/Gmail API interactions
- **Test Documentation**: See `tests/README.md` for detailed information

## 🎯 Usage Tips

1. **First Run**: Always run `python src/main.py` once to generate initial digest
2. **Caching**: Second run will be much faster (0 API calls if all cached)
3. **Monitoring**: Check metrics regularly to track API usage and costs
4. **Errors**: Review error section at bottom of page for issues
5. **Performance**: Use cache settings to optimize execution time
6. **Testing**: Run `python run_tests.py basic` before committing changes

## 📊 Performance

### Typical Execution Times
- **First run** (no cache): 13-20 seconds (10 emails)
- **Second run** (100% cached): 5-8 seconds
- **Page load**: < 1 second
- **Status polling**: 2 second intervals

### API Calls (per refresh)
- **First run**: 10-15 calls
  - 10 email categorizations
  - 2 category summaries
  - 3-7 newsletter summaries
- **Cached run**: 0-3 calls (only new emails)

## 🔐 Security Notes

- **API Keys**: Never commit API keys to version control
- **OAuth Tokens**: `token.json` is gitignored
- **Credentials**: `credentials.json` contains OAuth client secrets
- **Environment Variables**: Use for API keys in production
- **HTTPS**: Recommended for production deployments

## 🚀 Deployment

For production deployment:

1. **Use WSGI Server**: Replace Flask dev server with Gunicorn
   ```bash
   gunicorn -w 4 -b 0.0.0.0:8001 src.web.server:app
   ```

2. **Set Environment Variables**:
   ```bash
   export FLASK_ENV=production
   export GOOGLE_API_KEY='your_key'
   ```

3. **Configure Reverse Proxy**: Use Nginx for HTTPS
4. **Database Backup**: Regularly backup `data/metrics/metrics.db`
5. **Log Rotation**: Configure logrotate for `logs/email_assistant.log`

## 🤝 Contributing

This is a personal project, but suggestions are welcome!

## 📄 License

MIT License - feel free to use and modify

## 👤 Author

**Uday**

## 🙏 Acknowledgments

- Google Gemini AI for categorization
- Gmail API for email access
- Flask for web framework
- Claude Code for development assistance

---

**Version**: 2.1 (Phase 5 - Testing Infrastructure)
**Last Updated**: January 12, 2026
**Python**: 3.11+
**Status**: Production Ready
**Test Coverage**: 55+ tests across integration, unit, and contract testing
