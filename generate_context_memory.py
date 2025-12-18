"""
One-time script to generate context memory for today's emails.
Reads digest data, generates compressed context and elaborate summary, saves to database.
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

import json
import google.genai as genai
from datetime import datetime

from core.context_memory import ContextMemoryManager
from utils.context_utils import generate_compressed_context, generate_elaborate_summary
from utils.logger_utils import setup_logger

# Initialize logger
logger = setup_logger(__name__)


def main():
    """Generate context memory for today's emails."""
    print("\n" + "=" * 80)
    print("GENERATING CONTEXT MEMORY FOR TODAY'S EMAILS")
    print("=" * 80 + "\n")

    # Load digest data
    digest_file = Path(__file__).parent / 'data' / 'digest' / 'digest_data.json'

    if not digest_file.exists():
        print(f"❌ Digest file not found: {digest_file}")
        print("   Run 'python src/main.py' first to generate digest data")
        return

    print(f"📂 Loading digest data from: {digest_file}")
    with open(digest_file, 'r') as f:
        digest_data = json.load(f)

    categorized_emails = digest_data.get('categorized_emails', [])

    if not categorized_emails:
        print("❌ No emails found in digest data")
        return

    # Filter Need-Action and FYI emails
    categories = ['Need-Action', 'FYI']
    filtered_emails = [e for e in categorized_emails if e.get('category') in categories]

    print(f"   Total emails: {len(categorized_emails)}")
    print(f"   Need-Action & FYI emails: {len(filtered_emails)}")

    if not filtered_emails:
        print("❌ No Need-Action or FYI emails found")
        return

    # Initialize Gemini client
    api_key = os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        print("\n❌ GOOGLE_API_KEY not found in environment variables")
        print("   Set it with: export GOOGLE_API_KEY='your_api_key'")
        return

    client = genai.Client(api_key=api_key)
    model_name = 'gemini-2.0-flash-exp'

    print(f"\n🤖 Initializing Gemini AI (model: {model_name})")

    # Generate compressed context
    print("\n⚙️  Generating compressed context...")
    compressed_context = generate_compressed_context(
        filtered_emails,
        categories,
        client,
        model_name
    )
    print("   ✅ Compressed context generated")

    # Generate elaborate summary
    print("\n⚙️  Generating elaborate summary (max 10 bullets)...")
    elaborate_summary = generate_elaborate_summary(
        filtered_emails,
        categories,
        client,
        model_name,
        max_bullets=10
    )
    print(f"   ✅ Elaborate summary generated ({len(elaborate_summary)} bullet points)")

    # Display summary
    print("\n📋 Today's Email Context Summary:")
    print("-" * 80)
    for idx, bullet in enumerate(elaborate_summary, 1):
        print(f"  {idx}. {bullet}")
    print("-" * 80)

    # Save to database
    print("\n💾 Saving context memory to database...")
    context_manager = ContextMemoryManager()

    metadata = {
        'total_emails': len(categorized_emails),
        'filtered_emails': len(filtered_emails),
        'model': model_name,
        'generated_at': datetime.now().isoformat()
    }

    success = context_manager.save_context(
        compressed_context=compressed_context,
        elaborate_summary=elaborate_summary,
        email_count=len(filtered_emails),
        categories=categories,
        metadata=metadata
    )

    context_manager.close()

    if success:
        print("   ✅ Context memory saved successfully!")
        print(f"   📊 Stats: {len(filtered_emails)} emails, {len(categories)} categories")
    else:
        print("   ❌ Failed to save context memory")

    print("\n✅ Context memory generation complete!")
    print("\n   View in digest webpage: Click 'Context Memory' button")
    print("=" * 80 + "\n")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.exception("Context memory generation failed")
        sys.exit(1)
