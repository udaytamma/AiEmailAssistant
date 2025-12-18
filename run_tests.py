"""
Test Runner Script for Email Assistant

Runs pytest with different test suites:
- Basic: Most critical tests (fast, essential checks)
- Extended: Additional health checks (moderate coverage)
- Comprehensive: Full test suite (complete coverage)

Usage:
    python run_tests.py basic
    python run_tests.py extended
    python run_tests.py comprehensive
"""

import sys
import subprocess
import json
import time
from datetime import datetime
from pathlib import Path


def run_pytest(test_suite: str) -> dict:
    """
    Run pytest with specified test markers.

    Args:
        test_suite: 'basic', 'extended', or 'comprehensive'

    Returns:
        dict: Test results with stats, duration, passed/failed counts
    """
    print(f"\n{'=' * 80}")
    print(f"Running {test_suite.upper()} Test Suite")
    print(f"{'=' * 80}\n")

    start_time = time.time()

    # Build pytest command based on suite
    if test_suite == 'basic':
        # Run only tests marked as 'basic'
        # Note: Using --no-cov and -p no:asyncio for Python 3.14 compatibility
        cmd = ['pytest', '-v', '-m', 'basic', '--tb=short', '--no-cov', '-p', 'no:asyncio']
    elif test_suite == 'extended':
        # Run basic + extended tests
        cmd = ['pytest', '-v', '-m', 'basic or extended', '--tb=short', '--no-cov', '-p', 'no:asyncio']
    elif test_suite == 'comprehensive':
        # Run all tests
        cmd = ['pytest', '-v', '--tb=short', '--no-cov', '-p', 'no:asyncio']
    else:
        raise ValueError(f"Unknown test suite: {test_suite}")

    # Run pytest
    try:
        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True
        )

        duration = time.time() - start_time

        # Parse pytest output for summary
        output_lines = result.stdout.split('\n')
        passed = 0
        failed = 0
        skipped = 0

        for line in output_lines:
            if 'passed' in line.lower():
                # Extract numbers from pytest summary
                parts = line.split()
                for i, part in enumerate(parts):
                    if 'passed' in part and i > 0:
                        try:
                            passed = int(parts[i-1])
                        except ValueError:
                            pass
            if 'failed' in line.lower():
                parts = line.split()
                for i, part in enumerate(parts):
                    if 'failed' in part and i > 0:
                        try:
                            failed = int(parts[i-1])
                        except ValueError:
                            pass

        # Create results summary
        results = {
            'suite': test_suite,
            'timestamp': datetime.now().isoformat(),
            'duration': round(duration, 2),
            'passed': passed,
            'failed': failed,
            'skipped': skipped,
            'total': passed + failed + skipped,
            'success': result.returncode == 0,
            'output': result.stdout
        }

        # Print summary
        print(f"\n{'=' * 80}")
        print(f"Test Results Summary")
        print(f"{'=' * 80}")
        print(f"Suite: {test_suite.upper()}")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Total: {passed + failed + skipped}")
        print(f"Status: {'✅ SUCCESS' if results['success'] else '❌ FAILED'}")
        print(f"{'=' * 80}\n")

        return results

    except Exception as e:
        print(f"Error running tests: {e}")
        return {
            'suite': test_suite,
            'timestamp': datetime.now().isoformat(),
            'duration': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'total': 0,
            'success': False,
            'error': str(e)
        }


def save_results(results: dict):
    """Save test results to JSON file for web display."""
    results_dir = Path(__file__).parent / 'data' / 'test_results'
    results_dir.mkdir(parents=True, exist_ok=True)

    results_file = results_dir / f"results_{results['suite']}.json"

    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"Results saved to {results_file}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python run_tests.py [basic|extended|comprehensive]")
        print("\nTest Suites:")
        print("  basic         - Most critical tests (fast)")
        print("  extended      - Basic + additional health checks")
        print("  comprehensive - Full test suite (all tests)")
        sys.exit(1)

    test_suite = sys.argv[1].lower()

    if test_suite not in ['basic', 'extended', 'comprehensive']:
        print(f"Error: Unknown test suite '{test_suite}'")
        print("Valid options: basic, extended, comprehensive")
        sys.exit(1)

    # Run tests
    results = run_pytest(test_suite)

    # Save results
    save_results(results)

    # Exit with appropriate code
    sys.exit(0 if results['success'] else 1)
