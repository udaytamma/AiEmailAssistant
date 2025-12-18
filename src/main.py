"""
AI-Powered Email Executive Assistant
Main application file with comprehensive error handling, logging, and metrics tracking.

This is the main entry point that coordinates all email processing steps:
1. Authenticate with Gmail API
2. Fetch recent unread emails
3. Categorize emails using Gemini AI
4. Generate daily digest with summaries
5. Display results
6. Track metrics and performance

All heavy lifting is done by utility modules (email_utils, gemini_utils, display_utils)
"""

import os
import json
import time
import sys
import traceback
from datetime import datetime
from pathlib import Path

# Add src directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

import google.genai as genai

# Import utility functions from organized modules
from core.config_manager import ConfigManager
from core.cache_manager import CacheManager
from utils.email_utils import connect_to_gmail, fetch_recent_emails, display_emails
from utils.gemini_utils import categorize_emails
from utils.display_utils import display_categorized_summary, generate_daily_digest, display_daily_digest
from utils.logger_utils import setup_logger, log_exception, log_performance
from utils.metrics_utils import get_metrics_tracker

# Initialize logger
logger = setup_logger(__name__)


class EmailAssistantError(Exception):
    """Base exception for Email Assistant errors."""
    pass


def save_digest_to_json(digest: dict, categorized_emails: list, execution_time: float) -> bool:
    """
    Save the daily digest to a JSON file for web visualization.

    Args:
        digest: Daily digest dictionary from generate_daily_digest()
        categorized_emails: List of all categorized emails
        execution_time: Time taken to execute the script in seconds

    Returns:
        bool: True if successful, False otherwise
    """
    logger.info("Saving digest to JSON file")
    metrics = get_metrics_tracker()

    # Use data/digest directory
    digest_dir = Path(__file__).parent.parent / 'data' / 'digest'
    digest_dir.mkdir(parents=True, exist_ok=True)
    digest_file = digest_dir / 'digest_data.json'

    digest_data = {
        'metadata': {
            'last_updated': datetime.now().isoformat(),
            'execution_time': round(execution_time, 2),
            'total_emails': len(categorized_emails)
        },
        'digest': digest,
        'categorized_emails': categorized_emails
    }

    try:
        with open(digest_file, 'w') as f:
            json.dump(digest_data, f, indent=2)

        logger.info(f"Digest saved successfully to {digest_file}")
        print(f"\n💾 Digest saved to {digest_file}")
        return True

    except PermissionError as e:
        error_msg = f"Permission denied saving digest: {e}"
        logger.error(error_msg)
        metrics.record_error(__name__, "PermissionError", error_msg)
        print(f"\n⚠️  {error_msg}")
        return False

    except Exception as e:
        log_exception(logger, e, "Error saving digest to JSON")
        metrics.record_error(__name__, type(e).__name__, str(e), traceback.format_exc())
        print(f"\n⚠️  Error saving digest to JSON: {e}")
        return False


def main():
    """
    Main execution function for the Email Assistant.

    Workflow:
    1. Load configuration and initialize cache
    2. Connect to Gmail and fetch emails
    3. Initialize Gemini AI model
    4. Categorize emails (with caching)
    5. Generate and display daily digest
    6. Save digest to JSON for web visualization
    7. Record metrics and performance data

    Configuration is loaded from config.json
    Cache is managed automatically to reduce API calls
    All operations are logged and tracked for observability
    """
    # Track execution time
    start_time = time.time()
    metrics = get_metrics_tracker()
    success = False
    error_message = None

    try:
        # === Step 0: Load Configuration and Initialize Cache ===
        logger.info("=== Email Assistant Starting ===")
        print("\n" + "=" * 80)
        print("AI-POWERED EMAIL EXECUTIVE ASSISTANT")
        print("=" * 80)

        try:
            config = ConfigManager()
            cache_enabled = config.get('cache_settings', 'enabled', True)
            logger.info(f"Configuration loaded, cache {'enabled' if cache_enabled else 'disabled'}")

        except Exception as e:
            log_exception(logger, e, "Failed to load configuration")
            metrics.record_error(__name__, type(e).__name__, "Config load failed", traceback.format_exc())
            raise EmailAssistantError(f"Configuration loading failed: {e}")

        # Initialize cache if enabled
        cache = None
        if cache_enabled:
            try:
                cache = CacheManager(
                    cache_file=config.get('cache_settings', 'cache_file'),
                    max_size=config.get('cache_settings', 'max_cached_emails', 30),
                    expiry_hours=config.get('cache_settings', 'cache_expiry_hours', 24)
                )
                cache_stats = cache.stats()
                logger.info(f"Cache initialized: {cache_stats.get('total_entries', 0)} entries")

            except Exception as e:
                log_exception(logger, e, "Cache initialization failed, continuing without cache")
                cache = None
                cache_enabled = False

        print("\n⚙️  Configuration loaded")
        print(f"   Model: {config.get('api_settings', 'gemini_model')}")
        print(f"   Cache: {'Enabled' if cache_enabled else 'Disabled'}")

        # === Step 1: Connect to Gmail and Fetch Emails ===
        logger.info("Step 1: Connecting to Gmail")
        print("\n🔄 Step 1: Connecting to Gmail...")

        try:
            service = connect_to_gmail()
            logger.info("Gmail connection successful")

        except Exception as e:
            log_exception(logger, e, "Gmail connection failed")
            metrics.record_error(__name__, type(e).__name__, "Gmail connection failed", traceback.format_exc())
            raise EmailAssistantError(f"Failed to connect to Gmail: {e}")

        max_emails = config.get('gmail_settings', 'max_emails_to_fetch', 10)
        search_query = config.get('gmail_settings', 'search_query', 'is:unread newer_than:1d')

        # Get last fetch timestamp from cache for incremental fetching
        last_fetch_timestamp = None
        if cache_enabled and cache:
            last_fetch_timestamp = cache.get_last_fetch_timestamp()
            if last_fetch_timestamp:
                logger.info(f"Incremental fetch: fetching emails after {last_fetch_timestamp}")

        try:
            my_emails = fetch_recent_emails(
                service,
                max_results=max_emails,
                query=search_query,
                after_timestamp=last_fetch_timestamp
            )
            logger.info(f"Fetched {len(my_emails)} new emails")

        except Exception as e:
            log_exception(logger, e, "Email fetching failed")
            metrics.record_error(__name__, type(e).__name__, "Email fetch failed", traceback.format_exc())
            raise EmailAssistantError(f"Failed to fetch emails: {e}")

        # === Step 2: Display Fetched Emails ===
        print(f"\n📧 Step 2: Displaying {len(my_emails)} fetched emails")
        display_emails(my_emails)

        if len(my_emails) == 0:
            logger.info("No emails to process")
            print("No emails to process. Exiting.")
            # Record successful run with 0 emails
            execution_time = time.time() - start_time
            metrics.record_script_run(execution_time, 0, True, None)
            return

        # === Step 3: Initialize Gemini AI Model ===
        logger.info("Step 3: Initializing Gemini AI")
        print("\n🤖 Step 3: Initializing Gemini AI model...")

        # Get API key from environment variable
        api_key = os.environ.get('GOOGLE_API_KEY') or os.environ.get('GEMINI_API_KEY')

        if not api_key:
            error_msg = "GOOGLE_API_KEY not found in environment variables"
            logger.error(error_msg)
            metrics.record_error(__name__, "ConfigurationError", error_msg)
            print("\n⚠️  Warning: GOOGLE_API_KEY or GEMINI_API_KEY not found in environment variables.")
            print("\nTo set your API key:")
            print("  export GOOGLE_API_KEY='your_api_key_here'")
            print("\nOr add it to your ~/.bashrc or ~/.zshrc file")
            print("\nGet your API key from: https://aistudio.google.com/app/apikey")
            raise EmailAssistantError("GOOGLE_API_KEY not configured")

        try:
            # Initialize Gemini client
            client = genai.Client(api_key=api_key)

            # Get model name from config
            model_name = config.get('api_settings', 'gemini_model', 'gemini-2.5-flash-lite')

            logger.info(f"Gemini client initialized: {model_name}")
            print(f"✅ Gemini client initialized successfully (using {model_name})")

        except Exception as e:
            log_exception(logger, e, "Gemini initialization failed")
            metrics.record_error(__name__, type(e).__name__, "Gemini init failed", traceback.format_exc())
            raise EmailAssistantError(f"Failed to initialize Gemini: {e}")

        # === Step 4: Categorize Emails with Gemini (incremental processing) ===
        logger.info("Step 4: Categorizing emails")
        print("\n🧠 Step 4: Categorizing emails with Gemini LLM...")

        categorized_emails = []
        new_emails_count = 0

        try:
            # Load all cached emails first
            if cache_enabled and cache:
                cached_emails_dict = cache.get_all_cached_emails()
                categorized_emails = list(cached_emails_dict.values())
                logger.info(f"Loaded {len(categorized_emails)} emails from cache")
                print(f"  ✓ Loaded {len(categorized_emails)} previously processed emails from cache")

            # Categorize only new emails (not in cache)
            new_emails = [e for e in my_emails if not (cache_enabled and cache and cache.has(e['id']))]
            new_emails_count = len(new_emails)

            if new_emails_count > 0:
                logger.info(f"Categorizing {new_emails_count} new emails")
                print(f"  🆕 Categorizing {new_emails_count} new emails...")

                newly_categorized = categorize_emails(new_emails, client, model_name)

                # Add to results and cache
                for cat_email in newly_categorized:
                    categorized_emails.append(cat_email)

                    # Cache the categorization
                    if cache_enabled and cache:
                        cache_data = {
                            'category': cat_email['category'],
                            'subcategory': cat_email['subcategory'],
                            'summary': cat_email['summary'],
                            'action_item': cat_email['action_item'],
                            'date_due': cat_email['date_due'],
                            'from': cat_email['from'],
                            'subject': cat_email['subject'],
                            'date': cat_email['date'],
                            'snippet': cat_email['snippet'],
                            'id': cat_email['id']
                        }
                        cache.set(cat_email['id'], cache_data)
                        metrics.record_cache_operation('SET', 'email_categorization', None)

                # Update last fetch timestamp
                if cache_enabled and cache:
                    cache.update_last_fetch_timestamp(datetime.now().isoformat())
                    cache.save()
                    logger.info(f"Updated last fetch timestamp and saved cache")

                print(f"  ✅ {new_emails_count} new emails categorized and cached")
            else:
                logger.info("No new emails to categorize")
                print("  ℹ️ No new emails to categorize")

            logger.info(f"Total emails: {len(categorized_emails)} ({new_emails_count} new)")

        except Exception as e:
            log_exception(logger, e, "Email categorization failed")
            metrics.record_error(__name__, type(e).__name__, "Categorization failed", traceback.format_exc())
            raise EmailAssistantError(f"Failed to categorize emails: {e}")

        # === Step 5: Display Categorization Summary ===
        logger.info("Step 5: Displaying categorization summary")
        print("\n📊 Step 5: Displaying categorization summary...")
        display_categorized_summary(categorized_emails)

        # === Step 6: Generate Daily Digest ===
        logger.info("Step 6: Generating daily digest")
        print("\n📰 Step 6: Generating Daily Digest...")

        try:
            daily_digest = generate_daily_digest(
                categorized_emails,
                service,
                client,
                model_name,
                cache=cache if cache_enabled else None,
                new_emails_count=new_emails_count
            )
            logger.info("Daily digest generation successful")

        except Exception as e:
            log_exception(logger, e, "Daily digest generation failed")
            metrics.record_error(__name__, type(e).__name__, "Digest generation failed", traceback.format_exc())
            raise EmailAssistantError(f"Failed to generate daily digest: {e}")

        # === Step 7: Display Daily Digest ===
        logger.info("Step 7: Displaying daily digest")
        print("\n📋 Step 7: Displaying Daily Digest...")
        display_daily_digest(daily_digest)

        # Save cache after digest generation (for newsletter summaries and category summaries)
        if cache_enabled:
            cache.save()
            print("\n💾 Cache saved successfully")
            cache.stats()

        # === Step 8: Save Digest to JSON for Web Visualization ===
        execution_time = time.time() - start_time
        save_digest_to_json(daily_digest, categorized_emails, execution_time)

        # Record successful execution
        success = True
        log_performance(logger, "Full Email Processing", execution_time)
        logger.info(f"=== Email Assistant Completed Successfully ({execution_time:.2f}s) ===")
        print(f"\n✅ Email processing complete! (Execution time: {execution_time:.2f}s)")

    except EmailAssistantError as e:
        error_message = str(e)
        logger.error(f"Email Assistant failed: {error_message}")
        print(f"\n❌ Error: {error_message}")
        success = False

    except KeyboardInterrupt:
        error_message = "Interrupted by user"
        logger.warning("Email Assistant interrupted by user")
        print("\n⚠️  Process interrupted by user")
        success = False

    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"
        log_exception(logger, e, "Unexpected error in main execution")
        metrics.record_error(__name__, type(e).__name__, str(e), traceback.format_exc())
        print(f"\n❌ Unexpected error: {e}")
        print("Check logs/email_assistant.log for details")
        success = False

    finally:
        # Record script execution metrics
        execution_time = time.time() - start_time
        total_emails = len(categorized_emails) if 'categorized_emails' in locals() else 0
        metrics.record_script_run(execution_time, total_emails, success, error_message)
        logger.info(f"Script execution recorded: success={success}, emails={total_emails}, time={execution_time:.2f}s")


# === Application Entry Point ===
if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
