#!/bin/bash

# Email Digest Web Server Startup Script

echo "Starting Email Digest Web Server..."
echo ""

# Activate virtual environment
source .venv/bin/activate

# Set API key
export GOOGLE_API_KEY='AIzaSyD-tzw5Rp3DZ9jMMctwqPyMxdEsv2ZXoRU'

# Start Flask server
python digest_server.py
