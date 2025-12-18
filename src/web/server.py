"""
Flask Web Server for Email Digest Visualization
Serves the daily digest in a beautiful web interface with refresh functionality,
metrics tracking, and comprehensive error handling.
"""

import os
import json
import subprocess
import threading
import traceback
import sys
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, jsonify, request

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger_utils import setup_logger, log_exception
from utils.metrics_utils import get_metrics_tracker
from core.context_memory import ContextMemoryManager

# Initialize logger
logger = setup_logger(__name__)

# Initialize Flask app with proper template and static paths
template_dir = Path(__file__).parent / 'templates'
static_dir = Path(__file__).parent / 'static'
app = Flask(__name__, template_folder=str(template_dir), static_folder=str(static_dir))

# File paths
LOCK_FILE = Path(__file__).parent.parent.parent / 'script.lock'
DIGEST_FILE = Path(__file__).parent.parent.parent / 'data' / 'digest' / 'digest_data.json'


def is_script_running() -> bool:
    """
    Check if main.py is currently running.

    Returns:
        bool: True if script is running, False otherwise
    """
    return LOCK_FILE.exists()


def load_digest_data() -> dict:
    """
    Load digest data from JSON file.

    Returns:
        dict: Digest data with metadata, or None if file doesn't exist
    """
    metrics = get_metrics_tracker()

    try:
        if not DIGEST_FILE.exists():
            logger.warning("Digest file does not exist")
            return None

        with open(DIGEST_FILE, 'r') as f:
            data = json.load(f)

        logger.debug("Digest data loaded successfully")
        return data

    except json.JSONDecodeError as e:
        error_msg = f"Error parsing digest file: {e}"
        logger.error(error_msg)
        metrics.record_error(__name__, "JSONDecodeError", error_msg)
        return None

    except PermissionError as e:
        error_msg = f"Permission denied reading digest file: {e}"
        logger.error(error_msg)
        metrics.record_error(__name__, "PermissionError", error_msg)
        return None

    except Exception as e:
        log_exception(logger, e, "Error loading digest data")
        metrics.record_error(__name__, type(e).__name__, str(e), traceback.format_exc())
        return None


def run_email_assistant():
    """
    Run main.py script in the background.
    Creates a lock file to prevent simultaneous executions.
    """
    logger.info("Starting Email Assistant script execution")
    metrics = get_metrics_tracker()

    # Create lock file
    try:
        LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOCK_FILE, 'w') as f:
            f.write(str(datetime.now().isoformat()))
        logger.debug(f"Lock file created: {LOCK_FILE}")

    except Exception as e:
        log_exception(logger, e, "Failed to create lock file")
        metrics.record_error(__name__, type(e).__name__, "Lock file creation failed", traceback.format_exc())
        return

    try:
        # Get the API key from environment
        env = os.environ.copy()
        api_key = env.get('GOOGLE_API_KEY')

        if not api_key:
            # Try fallback key
            api_key = 'AIzaSyA1GD5wywl9HKvp68GpiYjyjnSiyBJSflM'
            env['GOOGLE_API_KEY'] = api_key
            logger.warning("Using fallback API key")

        # Run the script using the virtual environment's Python
        venv_python = Path(__file__).parent.parent.parent / '.venv' / 'bin' / 'python'
        main_script = Path(__file__).parent.parent / 'main.py'

        if not venv_python.exists():
            venv_python = 'python3'  # Fallback to system python
            logger.warning(f"Virtual environment Python not found, using system Python")

        if not main_script.exists():
            error_msg = f"Main script not found: {main_script}"
            logger.error(error_msg)
            metrics.record_error(__name__, "FileNotFoundError", error_msg)
            return

        logger.info(f"Executing: {venv_python} {main_script}")

        result = subprocess.run(
            [str(venv_python), str(main_script)],
            env=env,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        logger.info(f"Script execution completed with exit code: {result.returncode}")

        if result.returncode != 0:
            error_msg = f"Script execution failed: {result.stderr}"
            logger.error(error_msg)
            metrics.record_error(__name__, "ScriptExecutionError", error_msg)
            print(f"Error output: {result.stderr}")
        else:
            logger.info("Script execution successful")
            print("Email Assistant execution completed successfully")

    except subprocess.TimeoutExpired:
        error_msg = "Script execution timed out after 5 minutes"
        logger.error(error_msg)
        metrics.record_error(__name__, "TimeoutError", error_msg)
        print(error_msg)

    except FileNotFoundError as e:
        error_msg = f"Python or script file not found: {e}"
        logger.error(error_msg)
        metrics.record_error(__name__, "FileNotFoundError", error_msg)
        print(error_msg)

    except Exception as e:
        log_exception(logger, e, "Error running Email Assistant script")
        metrics.record_error(__name__, type(e).__name__, str(e), traceback.format_exc())
        print(f"Error running script: {e}")

    finally:
        # Remove lock file
        try:
            if LOCK_FILE.exists():
                LOCK_FILE.unlink()
                logger.debug("Lock file removed")
        except Exception as e:
            logger.error(f"Failed to remove lock file: {e}")


@app.route('/')
def index():
    """Serve the main digest page."""
    logger.debug("Serving main page")
    try:
        return render_template('digest.html')
    except Exception as e:
        log_exception(logger, e, "Error serving main page")
        return f"Error loading page: {e}", 500


@app.route('/tests')
def tests_page():
    """Serve the test results page."""
    logger.debug("Serving test results page")
    try:
        return render_template('test_results.html')
    except Exception as e:
        log_exception(logger, e, "Error serving test results page")
        return f"Error loading page: {e}", 500


@app.route('/gemini-review')
def gemini_review_page():
    """Serve the Gemini review page."""
    logger.debug("Serving Gemini review page")
    try:
        return render_template('gemini_review.html')
    except Exception as e:
        log_exception(logger, e, "Error serving Gemini review page")
        return f"Error loading page: {e}", 500


@app.route('/api/digest')
def get_digest():
    """
    API endpoint to get the current digest data.

    Returns:
        JSON response with digest data or error message
    """
    logger.debug("API: Get digest request")
    metrics = get_metrics_tracker()

    try:
        data = load_digest_data()

        if data is None:
            logger.info("No digest data available")
            return jsonify({
                'error': 'No digest data available. Please click "Get Latest View" to generate the digest.'
            }), 404

        logger.debug("Digest data returned successfully")
        return jsonify(data)

    except Exception as e:
        log_exception(logger, e, "Error in get_digest endpoint")
        metrics.record_error(__name__, type(e).__name__, f"API error: {e}", traceback.format_exc())
        return jsonify({
            'error': f'Server error: {str(e)}'
        }), 500


@app.route('/api/refresh', methods=['POST'])
def refresh_digest():
    """
    API endpoint to trigger main.py execution.

    Returns:
        JSON response indicating success or if script is already running
    """
    logger.info("API: Refresh digest request")
    metrics = get_metrics_tracker()

    try:
        if is_script_running():
            logger.info("Script already running, returning 409")
            return jsonify({
                'status': 'running',
                'message': 'Email assistant is already running. Please wait for it to complete.'
            }), 409

        # Run script in background thread
        thread = threading.Thread(target=run_email_assistant)
        thread.daemon = True
        thread.start()

        logger.info("Script execution started in background thread")
        return jsonify({
            'status': 'started',
            'message': 'Email assistant started successfully.'
        })

    except Exception as e:
        log_exception(logger, e, "Error in refresh_digest endpoint")
        metrics.record_error(__name__, type(e).__name__, f"API error: {e}", traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'Failed to start email assistant: {str(e)}'
        }), 500


@app.route('/api/status')
def check_status():
    """
    API endpoint to check if the script is running.

    Returns:
        JSON response with running status
    """
    logger.debug("API: Status check request")

    try:
        running = is_script_running()
        return jsonify({
            'running': running
        })

    except Exception as e:
        log_exception(logger, e, "Error in check_status endpoint")
        return jsonify({
            'running': False,
            'error': str(e)
        }), 500


@app.route('/api/metrics')
def get_metrics():
    """
    API endpoint to get observability metrics.

    Returns:
        JSON response with comprehensive metrics data
    """
    logger.debug("API: Metrics request")
    metrics = get_metrics_tracker()

    try:
        metrics_summary = metrics.get_metrics_summary()
        logger.debug("Metrics data returned successfully")
        return jsonify(metrics_summary)

    except Exception as e:
        log_exception(logger, e, "Error in get_metrics endpoint")
        return jsonify({
            'error': f'Failed to fetch metrics: {str(e)}'
        }), 500


@app.route('/api/context-memory/latest')
def get_latest_context_memory():
    """
    API endpoint to get the latest context memory.

    Returns:
        JSON response with latest context memory data
    """
    logger.debug("API: Latest context memory request")

    try:
        context_manager = ContextMemoryManager()
        latest_context = context_manager.get_latest_context()
        context_manager.close()

        if not latest_context:
            logger.info("No context memory found")
            return jsonify({
                'error': 'No context memory available'
            }), 404

        logger.debug("Latest context memory returned successfully")
        return jsonify(latest_context)

    except Exception as e:
        log_exception(logger, e, "Error in get_latest_context_memory endpoint")
        return jsonify({
            'error': f'Failed to fetch context memory: {str(e)}'
        }), 500


@app.route('/api/errors')
def get_errors():
    """
    API endpoint to get recent errors.

    Returns:
        JSON response with recent error list
    """
    logger.debug("API: Errors request")
    metrics = get_metrics_tracker()

    try:
        errors = metrics.get_recent_errors(limit=10)
        logger.debug(f"Returning {len(errors)} recent errors")
        return jsonify({
            'errors': errors
        })

    except Exception as e:
        log_exception(logger, e, "Error in get_errors endpoint")
        return jsonify({
            'errors': [],
            'error': str(e)
        }), 500


@app.route('/api/tests/run/<suite>', methods=['POST'])
def run_tests(suite):
    """
    API endpoint to run test suites.

    Args:
        suite: 'basic', 'extended', or 'comprehensive'

    Returns:
        JSON response with test results
    """
    logger.info(f"API: Run {suite} tests request")
    metrics = get_metrics_tracker()

    if suite not in ['basic', 'extended', 'comprehensive']:
        return jsonify({
            'error': f"Invalid test suite: {suite}. Must be 'basic', 'extended', or 'comprehensive'."
        }), 400

    try:
        # Run the test runner script
        project_root = Path(__file__).parent.parent.parent
        run_tests_script = project_root / 'run_tests.py'

        if not run_tests_script.exists():
            error_msg = f"Test runner script not found: {run_tests_script}"
            logger.error(error_msg)
            return jsonify({'error': error_msg}), 500

        # Get venv python
        venv_python = project_root / '.venv' / 'bin' / 'python'
        if not venv_python.exists():
            venv_python = 'python3'

        logger.info(f"Executing: {venv_python} {run_tests_script} {suite}")

        result = subprocess.run(
            [str(venv_python), str(run_tests_script), suite],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            cwd=str(project_root)
        )

        # Load results from JSON file
        results_file = project_root / 'data' / 'test_results' / f'results_{suite}.json'

        if results_file.exists():
            with open(results_file, 'r') as f:
                results_data = json.load(f)

            logger.info(f"Test suite {suite} completed: {results_data.get('passed', 0)} passed, {results_data.get('failed', 0)} failed")
            return jsonify(results_data)
        else:
            # Fallback: return basic results from subprocess
            logger.warning(f"Results file not found: {results_file}")
            return jsonify({
                'suite': suite,
                'timestamp': datetime.now().isoformat(),
                'duration': 0,
                'passed': 0,
                'failed': 0,
                'total': 0,
                'success': result.returncode == 0,
                'output': result.stdout
            })

    except subprocess.TimeoutExpired:
        error_msg = "Test execution timed out after 5 minutes"
        logger.error(error_msg)
        metrics.record_error(__name__, "TimeoutError", error_msg)
        return jsonify({
            'error': error_msg,
            'suite': suite,
            'success': False
        }), 500

    except Exception as e:
        log_exception(logger, e, f"Error running {suite} tests")
        metrics.record_error(__name__, type(e).__name__, str(e), traceback.format_exc())
        return jsonify({
            'error': f'Failed to run tests: {str(e)}',
            'suite': suite,
            'success': False
        }), 500


@app.route('/api/tests/latest')
def get_latest_tests():
    """
    API endpoint to get the most recent test results.

    Returns:
        JSON response with latest test results
    """
    logger.debug("API: Get latest test results")

    try:
        # Check for most recent results file
        results_dir = Path(__file__).parent.parent.parent / 'data' / 'test_results'

        if not results_dir.exists():
            return jsonify({}), 404

        # Find most recent results file
        result_files = list(results_dir.glob('results_*.json'))

        if not result_files:
            return jsonify({}), 404

        # Sort by modification time
        latest_file = max(result_files, key=lambda p: p.stat().st_mtime)

        with open(latest_file, 'r') as f:
            results = json.load(f)

        logger.debug(f"Returning latest test results from {latest_file.name}")
        return jsonify(results)

    except Exception as e:
        log_exception(logger, e, "Error getting latest test results")
        return jsonify({
            'error': str(e)
        }), 500


@app.route('/api/gemini-review')
def get_gemini_review():
    """
    API endpoint to fetch fresh emails and run Gemini categorization with automation analysis.

    Returns:
        JSON response with categorized emails and automation results
    """
    logger.info("API: Gemini review request - processing fresh emails")
    metrics = get_metrics_tracker()

    try:
        import google.genai as genai
        from core.config_manager import ConfigManager
        from utils.email_utils import connect_to_gmail, fetch_recent_emails
        from utils.gemini_utils import categorize_emails
        from utils.automation_workflow import process_need_action_automations, process_spam_automations

        # Load configuration
        config = ConfigManager()
        model_name = config.get('api_settings', 'gemini_model', 'gemini-2.5-flash-lite')
        max_emails = 30  # Fixed to 30 emails for Gemini review
        search_query = 'is:unread'  # Only unread emails for this page

        # Get API key
        api_key = os.environ.get('GOOGLE_API_KEY')
        if not api_key:
            api_key = 'AIzaSyA1GD5wywl9HKvp68GpiYjyjnSiyBJSflM'  # Fallback
            os.environ['GOOGLE_API_KEY'] = api_key

        # Connect to Gmail
        logger.info("Connecting to Gmail")
        gmail_service = connect_to_gmail()

        # Fetch fresh emails (ignore cache)
        logger.info(f"Fetching {max_emails} recent emails")
        emails = fetch_recent_emails(
            gmail_service,
            max_results=max_emails,
            query=search_query,
            after_timestamp=None  # Ignore cache, get all recent emails
        )

        if not emails:
            logger.info("No emails found")
            return jsonify({
                'emails': [],
                'message': 'No recent emails found'
            })

        logger.info(f"Fetched {len(emails)} emails, categorizing with Gemini")

        # Initialize Gemini client
        gemini_client = genai.Client(api_key=api_key)

        # Categorize all emails
        categorized_emails = categorize_emails(emails, gemini_client, model_name)

        # Separate emails by category for automation processing
        need_action_emails = [e for e in categorized_emails if e.get('category') == 'Need-Action']
        spam_emails = [e for e in categorized_emails if e.get('category') == 'SPAM']

        logger.info(f"Categorized: {len(need_action_emails)} Need-Action, {len(spam_emails)} SPAM")

        # Process automations (but don't execute, just analyze)
        automation_results = {}

        if need_action_emails:
            logger.info("Analyzing Need-Action emails for automation opportunities")
            # Note: We're not actually executing automations, just analyzing
            for email in need_action_emails:
                email_id = email.get('id')
                automation_results[email_id] = {
                    'automation_result': 'Analysis pending',
                    'action_taken': 'Waiting for approval'
                }

        if spam_emails:
            logger.info("Analyzing SPAM emails for unsubscribe opportunities")
            for email in spam_emails:
                email_id = email.get('id')
                automation_results[email_id] = {
                    'spam_info': 'SPAM detected - unsubscribe analysis pending',
                    'action_taken': 'No'
                }

        # Format response data
        response_emails = []
        for email in categorized_emails:
            email_id = email.get('id')
            category = email.get('category', 'Other')

            # Determine action taken status
            action_taken = 'No'
            automation_result = None
            spam_info = None

            if email_id in automation_results:
                action_taken = automation_results[email_id].get('action_taken', 'No')
                automation_result = automation_results[email_id].get('automation_result')
                spam_info = automation_results[email_id].get('spam_info')

            response_emails.append({
                'from': email.get('from', 'Unknown'),
                'subject': email.get('subject', 'No Subject'),
                'category': category,
                'subcategory': email.get('subcategory', ''),
                'action_item': email.get('action_item', ''),
                'automation_result': automation_result,
                'spam_info': spam_info,
                'action_taken': action_taken,
                'id': email_id
            })

        logger.info(f"Returning {len(response_emails)} categorized emails")

        return jsonify({
            'emails': response_emails,
            'timestamp': datetime.now().isoformat(),
            'total': len(response_emails)
        })

    except Exception as e:
        log_exception(logger, e, "Error in get_gemini_review endpoint")
        metrics.record_error(__name__, type(e).__name__, f"Gemini review API error: {e}", traceback.format_exc())
        return jsonify({
            'error': f'Failed to process emails: {str(e)}'
        }), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    logger.warning(f"404 Not Found: {request.url}")
    return jsonify({
        'error': 'Resource not found'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"500 Internal Error: {error}")
    return jsonify({
        'error': 'Internal server error'
    }), 500


if __name__ == '__main__':
    try:
        # Create directories if they don't exist
        template_dir.mkdir(parents=True, exist_ok=True)
        static_dir.mkdir(parents=True, exist_ok=True)
        (Path(__file__).parent.parent.parent / 'data' / 'digest').mkdir(parents=True, exist_ok=True)

        logger.info("Email Digest Web Server starting")
        print("\n" + "=" * 80)
        print("EMAIL DIGEST WEB SERVER")
        print("=" * 80)
        print(f"\n🌐 Starting server on http://localhost:8001")
        print("📧 Access your daily digest at: http://localhost:8001")
        print("\nPress CTRL+C to stop the server\n")

        # Run Flask app
        app.run(host='0.0.0.0', port=8001, debug=True, use_reloader=False)

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        print("\n⚠️  Server stopped by user")

    except Exception as e:
        log_exception(logger, e, "Server startup failed")
        print(f"\n❌ Server startup failed: {e}")
        sys.exit(1)
