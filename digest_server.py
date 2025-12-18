"""
Flask Web Server for Email Digest Visualization
Serves the daily digest in a beautiful web interface with refresh functionality
"""

import os
import json
import subprocess
import threading
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from pathlib import Path

app = Flask(__name__)

# Lock file to prevent simultaneous script executions
LOCK_FILE = 'script.lock'
DIGEST_FILE = 'digest_data.json'


def is_script_running():
    """Check if EmailAssistant.py is currently running."""
    return os.path.exists(LOCK_FILE)


def load_digest_data():
    """
    Load digest data from JSON file.

    Returns:
        dict: Digest data with metadata, or None if file doesn't exist
    """
    try:
        if os.path.exists(DIGEST_FILE):
            with open(DIGEST_FILE, 'r') as f:
                return json.load(f)
        return None
    except Exception as e:
        print(f"Error loading digest data: {e}")
        return None


def run_email_assistant():
    """
    Run EmailAssistant.py script in the background.
    Creates a lock file to prevent simultaneous executions.
    """
    # Create lock file
    with open(LOCK_FILE, 'w') as f:
        f.write(str(datetime.now().isoformat()))

    try:
        # Get the API key from environment
        env = os.environ.copy()
        api_key = env.get('GOOGLE_API_KEY')

        if not api_key:
            # Try to get from parent process
            api_key = 'AIzaSyA1GD5wywl9HKvp68GpiYjyjnSiyBJSflM'  # Fallback to known key
            env['GOOGLE_API_KEY'] = api_key

        # Run the script using the virtual environment's Python
        venv_python = '.venv/bin/python'
        if not os.path.exists(venv_python):
            venv_python = 'python'  # Fallback to system python

        result = subprocess.run(
            [venv_python, 'EmailAssistant.py'],
            env=env,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        print("EmailAssistant.py execution completed")
        print(f"Exit code: {result.returncode}")

        if result.returncode != 0:
            print(f"Error output: {result.stderr}")

    except subprocess.TimeoutExpired:
        print("EmailAssistant.py execution timed out")
    except Exception as e:
        print(f"Error running EmailAssistant.py: {e}")
    finally:
        # Remove lock file
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)


@app.route('/')
def index():
    """Serve the main digest page."""
    return render_template('digest.html')


@app.route('/api/digest')
def get_digest():
    """
    API endpoint to get the current digest data.

    Returns:
        JSON response with digest data or error message
    """
    data = load_digest_data()

    if data is None:
        return jsonify({
            'error': 'No digest data available. Please click "Get Latest View" to generate the digest.'
        }), 404

    return jsonify(data)


@app.route('/api/refresh', methods=['POST'])
def refresh_digest():
    """
    API endpoint to trigger EmailAssistant.py execution.

    Returns:
        JSON response indicating success or if script is already running
    """
    if is_script_running():
        return jsonify({
            'status': 'running',
            'message': 'Email assistant is already running. Please wait for it to complete.'
        }), 409

    # Run script in background thread
    thread = threading.Thread(target=run_email_assistant)
    thread.daemon = True
    thread.start()

    return jsonify({
        'status': 'started',
        'message': 'Email assistant started successfully.'
    })


@app.route('/api/status')
def check_status():
    """
    API endpoint to check if the script is running.

    Returns:
        JSON response with running status
    """
    return jsonify({
        'running': is_script_running()
    })


if __name__ == '__main__':
    # Create directories if they don't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)

    print("\n" + "=" * 80)
    print("EMAIL DIGEST WEB SERVER")
    print("=" * 80)
    print(f"\n🌐 Starting server on http://localhost:8001")
    print("📧 Access your daily digest at: http://localhost:8001")
    print("\nPress CTRL+C to stop the server\n")

    # Run Flask app
    app.run(host='0.0.0.0', port=8001, debug=True, use_reloader=False)
