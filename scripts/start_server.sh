#!/bin/bash

# Email Digest Web Server Startup Script

echo "Starting Email Digest Web Server..."
echo ""

# Navigate to project root
cd "$(dirname "$0")/.."

# Activate virtual environment
source .venv/bin/activate

# Load API key from .env file if it exists
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Check if API key is set
if [ -z "$GOOGLE_API_KEY" ]; then
    echo "ERROR: GOOGLE_API_KEY is not set."
    echo "Please either:"
    echo "  1. Create a .env file with: GOOGLE_API_KEY=your_key_here"
    echo "  2. Or set the environment variable: export GOOGLE_API_KEY=your_key"
    echo ""
    echo "Get your API key from: https://aistudio.google.com/app/apikey"
    exit 1
fi

# Start Flask server
python src/web/server.py
