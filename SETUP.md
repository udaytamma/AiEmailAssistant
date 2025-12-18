# Email Assistant - Setup Guide

## First-Time Setup

### 1. Clone Repository
```bash
git clone https://github.com/YOUR_USERNAME/emailAssistant.git
cd emailAssistant
```

### 2. Install Dependencies
```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install packages
pip install -r requirements.txt

# For development/testing
pip install -r requirements-dev.txt
```

### 3. Configure Application

#### a) Create Configuration File
```bash
cp config/config.example.json config/config.json
```

Edit `config/config.json` with your preferences.

#### b) Set Up Gmail API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable Gmail API
4. Enable Google Calendar API (if using automation)
5. Enable Google Tasks API (if using automation)
6. Create OAuth 2.0 credentials:
   - Application type: Desktop app
   - Download credentials as `credentials.json`
7. Place `credentials.json` in project root

#### c) Set Up Gemini API

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create API key
3. Export as environment variable:
```bash
export GOOGLE_API_KEY='your-api-key-here'
```

Add to your `~/.bashrc` or `~/.zshrc` for persistence:
```bash
echo 'export GOOGLE_API_KEY="your-api-key-here"' >> ~/.bashrc
source ~/.bashrc
```

### 4. Create Required Directories
```bash
mkdir -p data/cache data/digest data/metrics data/test_results logs
```

### 5. First Run
```bash
# Generate initial digest
python src/main.py

# Start web server
python src/web/server.py
```

Visit: http://localhost:8001

### 6. Authentication

On first run, you'll be prompted to authenticate:
1. Browser will open automatically
2. Sign in with your Google account
3. Grant permissions
4. Token saved to `token.json` (do NOT commit this)

## Security Notes

**NEVER commit these files to GitHub:**
- `credentials.json` - OAuth credentials
- `token.json` - Access token
- `config/config.json` - May contain sensitive data
- `data/` - Contains personal email data
- `.env` - Environment variables

These are protected by `.gitignore`.

## Troubleshooting

### "credentials.json not found"
Download from Google Cloud Console and place in project root.

### "GOOGLE_API_KEY not set"
Export the environment variable as shown in step 3c.

### "Permission denied" errors
Run: `chmod +x scripts/*.sh`

### Dependencies issues
```bash
pip install --upgrade -r requirements.txt
```

## Development Setup

```bash
# Run tests
python run_tests.py basic

# View test results in browser
python src/web/server.py
# Navigate to http://localhost:8001/tests
```

## Production Deployment

See `README.md` for production deployment guidelines.
