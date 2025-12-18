"""
AI-Powered Email Executive Assistant
Main application file - orchestrates email fetching, categorization, and daily digest generation

This is the main entry point that coordinates all email processing steps:
1. Authenticate with Gmail API
2. Fetch recent unread emails
3. Categorize emails using Gemini AI
4. Generate daily digest with summaries
5. Display results

All heavy lifting is done by utility modules (email_utils, gemini_utils, display_utils)
"""

import os
import json
import time
from datetime import datetime
import google.genai as genai

# Import utility functions from organized modules
from config_manager import ConfigManager
from cache_manager import CacheManager
from email_utils import connect_to_gmail, fetch_recent_emails, display_emails
from gemini_utils import categorize_emails
from display_utils import display_categorized_summary, generate_daily_digest, display_daily_digest


def save_digest_to_json(digest, categorized_emails, execution_time):
    """
    Save the daily digest to a JSON file for web visualization.

    Args:
        digest: Daily digest dictionary from generate_daily_digest()
        categorized_emails: List of all categorized emails
        execution_time: Time taken to execute the script in seconds
    """
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
        with open('digest_data.json', 'w') as f:
            json.dump(digest_data, f, indent=2)
        print(f"\n💾 Digest saved to digest_data.json")
    except Exception as e:
        print(f"\n⚠️  Error saving digest to JSON: {e}")


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

    Configuration is loaded from config.json
    Cache is managed automatically to reduce API calls
    """
    # Track execution time
    start_time = time.time()

    # === Step 0: Load Configuration and Initialize Cache ===
    print("\n" + "=" * 80)
    print("AI-POWERED EMAIL EXECUTIVE ASSISTANT")
    print("=" * 80)

    config = ConfigManager()
    cache_enabled = config.get('cache_settings', 'enabled', True)

    # Initialize cache if enabled
    if cache_enabled:
        cache = CacheManager(
            cache_file=config.get('cache_settings', 'cache_file', 'email_cache.json'),
            max_size=config.get('cache_settings', 'max_cached_emails', 30),
            expiry_hours=config.get('cache_settings', 'cache_expiry_hours', 24)
        )
        cache.stats()  # Display cache statistics
    else:
        cache = None

    print("\n⚙️  Configuration loaded")
    print(f"   Model: {config.get('api_settings', 'gemini_model')}")
    print(f"   Cache: {'Enabled' if cache_enabled else 'Disabled'}")

    # === Step 1: Connect to Gmail and Fetch Emails ===
    print("\n🔄 Step 1: Connecting to Gmail...")
    service = connect_to_gmail()

    max_emails = config.get('gmail_settings', 'max_emails_to_fetch', 10)
    search_query = config.get('gmail_settings', 'search_query', 'is:unread newer_than:1d')

    my_emails = fetch_recent_emails(service, max_results=max_emails, query=search_query)

    # === Step 2: Display Fetched Emails ===
    print(f"\n📧 Step 2: Displaying {len(my_emails)} fetched emails")
    display_emails(my_emails)

    if len(my_emails) == 0:
        print("No emails to process. Exiting.")
        return

    # === Step 3: Initialize Gemini AI Model ===
    print("\n🤖 Step 3: Initializing Gemini AI model...")

    # Get API key from environment variable
    api_key = os.environ.get('GOOGLE_API_KEY') or os.environ.get('GEMINI_API_KEY')

    if not api_key:
        print("\n⚠️  Warning: GOOGLE_API_KEY or GEMINI_API_KEY not found in environment variables.")
        print("\nTo set your API key:")
        print("  export GOOGLE_API_KEY='your_api_key_here'")
        print("\nOr add it to your ~/.bashrc or ~/.zshrc file")
        print("\nGet your API key from: https://aistudio.google.com/app/apikey")
        return

    # Initialize Gemini client
    client = genai.Client(api_key=api_key)

    # Get model name from config
    model_name = config.get('api_settings', 'gemini_model', 'gemini-2.5-flash-lite')

    print(f"✅ Gemini client initialized successfully (using {model_name})")

    # === Step 4: Categorize Emails with Gemini (with caching) ===
    print("\n🧠 Step 4: Categorizing emails with Gemini LLM...")

    categorized_emails = []
    cache_hits = 0
    cache_misses = 0

    # Check cache for each email
    for email in my_emails:
        email_id = email['id']

        # Try to get from cache
        if cache_enabled and cache.has(email_id):
            cached_data = cache.get(email_id)
            # Merge email data with cached categorization
            categorized_email = {**email, **cached_data}
            categorized_emails.append(categorized_email)
            cache_hits += 1
            print(f"  ✓ Using cached data for: {email['subject'][:50]}...")
        else:
            cache_misses += 1

    # Categorize uncached emails
    if cache_misses > 0:
        uncached_emails = [e for e in my_emails if not (cache_enabled and cache.has(e['id']))]
        newly_categorized = categorize_emails(uncached_emails, client, model_name)

        # Add to results and cache
        for cat_email in newly_categorized:
            categorized_emails.append(cat_email)

            # Cache the categorization
            if cache_enabled:
                cache_data = {
                    'category': cat_email['category'],
                    'subcategory': cat_email['subcategory'],
                    'summary': cat_email['summary'],
                    'action_item': cat_email['action_item'],
                    'date_due': cat_email['date_due']
                }
                cache.set(cat_email['id'], cache_data)

    # Save cache and display stats
    if cache_enabled:
        cache.save()
        print(f"\n📊 Cache Stats: {cache_hits} hits, {cache_misses} misses ({len(cache.cache)}/{cache.max_size} cached)")

    # === Step 5: Display Categorization Summary ===
    print("\n📊 Step 5: Displaying categorization summary...")
    display_categorized_summary(categorized_emails)

    # === Step 6: Generate Daily Digest ===
    print("\n📰 Step 6: Generating Daily Digest...")
    daily_digest = generate_daily_digest(
        categorized_emails,
        service,
        client,
        model_name,
        cache=cache if cache_enabled else None
    )

    # === Step 7: Display Daily Digest ===
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

    print(f"\n✅ Email processing complete! (Execution time: {execution_time:.2f}s)")


# === Application Entry Point ===
if __name__ == '__main__':
    main()
