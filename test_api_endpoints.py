#!/usr/bin/env python3
"""
Test script for Email Assistant API endpoints.
Tests all the new email action endpoints.
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8001"

def test_delete_email():
    """Test DELETE email endpoint."""
    print("\n" + "="*80)
    print("TEST 1: Delete Email")
    print("="*80)

    # Using a test email ID (this will be trashed, not permanently deleted)
    payload = {
        "email_id": "19b2dc0dc7e9e1af"  # Holiday lights email
    }

    print(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(f"{BASE_URL}/api/email/delete", json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200 and response.json().get('success'):
            print("✅ DELETE EMAIL TEST PASSED")
            return True
        else:
            print("❌ DELETE EMAIL TEST FAILED")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_mark_read():
    """Test MARK AS READ endpoint."""
    print("\n" + "="*80)
    print("TEST 2: Mark Email as Read")
    print("="*80)

    payload = {
        "email_id": "19b31c406ed76be3"  # Chase statement email
    }

    print(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(f"{BASE_URL}/api/email/mark-read", json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200 and response.json().get('success'):
            print("✅ MARK AS READ TEST PASSED")
            return True
        else:
            print("❌ MARK AS READ TEST FAILED")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_add_calendar():
    """Test ADD TO CALENDAR endpoint."""
    print("\n" + "="*80)
    print("TEST 3: Add to Calendar")
    print("="*80)

    payload = {
        "email_id": "19b3366d6f81d2c4",  # Discover Card statement
        "subject": "Pay Discover Card - Minimum $35 due Jan 14"
    }

    print(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(f"{BASE_URL}/api/email/add-calendar", json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200 and response.json().get('success'):
            print("✅ ADD TO CALENDAR TEST PASSED")
            return True
        else:
            print("❌ ADD TO CALENDAR TEST FAILED")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_add_task():
    """Test ADD TO TASKS endpoint."""
    print("\n" + "="*80)
    print("TEST 4: Add to Tasks")
    print("="*80)

    payload = {
        "email_id": "19b33486acefc819",  # HOA dues email
        "subject": "Pay HOA dues - $107.73"
    }

    print(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(f"{BASE_URL}/api/email/add-task", json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200 and response.json().get('success'):
            print("✅ ADD TO TASKS TEST PASSED")
            return True
        else:
            print("❌ ADD TO TASKS TEST FAILED")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_unsubscribe():
    """Test UNSUBSCRIBE endpoint."""
    print("\n" + "="*80)
    print("TEST 5: Unsubscribe from Email")
    print("="*80)

    payload = {
        "email_id": "test_spam_email_123",
        "unsubscribe_email": "unsubscribe@example.com"
    }

    print(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(f"{BASE_URL}/api/email/unsubscribe", json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200 and response.json().get('success'):
            print("✅ UNSUBSCRIBE TEST PASSED")
            return True
        else:
            print("❌ UNSUBSCRIBE TEST FAILED")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_error_handling():
    """Test error handling with missing parameters."""
    print("\n" + "="*80)
    print("TEST 6: Error Handling (Missing email_id)")
    print("="*80)

    payload = {}  # Missing email_id

    print(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(f"{BASE_URL}/api/email/delete", json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 400 and not response.json().get('success'):
            print("✅ ERROR HANDLING TEST PASSED")
            return True
        else:
            print("❌ ERROR HANDLING TEST FAILED")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "="*80)
    print("EMAIL ASSISTANT API ENDPOINT TESTS")
    print("="*80)
    print(f"Testing server at: {BASE_URL}")

    results = []

    # Run all tests
    results.append(("Delete Email", test_delete_email()))
    results.append(("Mark as Read", test_mark_read()))
    results.append(("Add to Calendar", test_add_calendar()))
    results.append(("Add to Tasks", test_add_task()))
    results.append(("Unsubscribe", test_unsubscribe()))
    results.append(("Error Handling", test_error_handling()))

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:.<50} {status}")

    print("="*80)
    print(f"Total: {passed}/{total} tests passed")
    print("="*80)

    sys.exit(0 if passed == total else 1)
