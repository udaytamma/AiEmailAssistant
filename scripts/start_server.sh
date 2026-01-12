#!/bin/bash

# Email Digest Web Server Startup Script

echo "Starting Email Digest Web Server..."
echo ""

# Navigate to project root
cd "$(dirname "$0")/.."

# Activate virtual environment
source .venv/bin/activate

# Set API key
export GOOGLE_API_KEY='REDACTED_GEMINI_API_KEY'

# Start Flask server
python src/web/server.py
