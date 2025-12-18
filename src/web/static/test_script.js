/**
 * Test Results Page JavaScript
 *
 * Handles:
 * - Running test suites via API calls
 * - Displaying test results
 * - Loading states
 * - Error handling
 */

// ==============================================================================
// Test Execution
// ==============================================================================

/**
 * Run tests for specified suite
 * @param {string} suite - 'basic', 'extended', or 'comprehensive'
 */
async function runTests(suite) {
    console.log(`Running ${suite} tests...`);

    // Show loading overlay
    const loadingOverlay = document.getElementById('loadingOverlay');
    const loadingSuite = document.getElementById('loadingSuite');
    loadingSuite.textContent = `Running ${suite.toUpperCase()} test suite...`;
    loadingOverlay.classList.remove('hidden');

    // Hide previous results and errors
    document.getElementById('resultsSection').classList.add('hidden');
    document.getElementById('errorMessage').classList.add('hidden');

    // Disable all test buttons
    disableTestButtons(true);

    try {
        // Call API to run tests
        const response = await fetch(`/api/tests/run/${suite}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const results = await response.json();

        // Hide loading
        loadingOverlay.classList.add('hidden');

        // Display results
        displayResults(results);

        // Show toast
        showToast(`${suite.toUpperCase()} tests completed`);

    } catch (error) {
        console.error('Error running tests:', error);

        // Hide loading
        loadingOverlay.classList.add('hidden');

        // Show error
        showError(error.message || 'Failed to run tests');

        // Show toast
        showToast('Error running tests', 'error');

    } finally {
        // Re-enable buttons
        disableTestButtons(false);
    }
}

/**
 * Disable/enable test buttons
 * @param {boolean} disabled - Whether to disable buttons
 */
function disableTestButtons(disabled) {
    document.getElementById('runBasicBtn').disabled = disabled;
    document.getElementById('runExtendedBtn').disabled = disabled;
    document.getElementById('runComprehensiveBtn').disabled = disabled;
}

// ==============================================================================
// Results Display
// ==============================================================================

/**
 * Display test results
 * @param {object} results - Test results object
 */
function displayResults(results) {
    console.log('Displaying results:', results);

    // Show results section
    const resultsSection = document.getElementById('resultsSection');
    resultsSection.classList.remove('hidden');

    // Update suite name and timestamp
    document.getElementById('resultsSuite').textContent = results.suite.toUpperCase();

    const timestamp = new Date(results.timestamp);
    document.getElementById('resultsTimestamp').textContent =
        timestamp.toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });

    // Update summary cards
    document.getElementById('passedCount').textContent = results.passed || 0;
    document.getElementById('failedCount').textContent = results.failed || 0;
    document.getElementById('totalCount').textContent = results.total || 0;
    document.getElementById('durationValue').textContent = `${results.duration}s`;

    // Update overall status
    const statusBanner = document.getElementById('overallStatus');
    const statusIcon = document.getElementById('statusIcon');
    const statusText = document.getElementById('statusText');

    if (results.success) {
        statusBanner.className = 'status-banner success';
        statusIcon.textContent = '✅';
        statusText.textContent = 'All tests passed successfully!';
    } else {
        statusBanner.className = 'status-banner failure';
        statusIcon.textContent = '❌';
        statusText.textContent = `${results.failed} test(s) failed`;
    }

    // Update detailed output
    const outputElement = document.getElementById('testOutput');
    outputElement.textContent = results.output || 'No output available';

    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/**
 * Show error message
 * @param {string} message - Error message
 */
function showError(message) {
    const errorMessage = document.getElementById('errorMessage');
    const errorText = document.getElementById('errorText');

    errorText.textContent = message;
    errorMessage.classList.remove('hidden');
}

// ==============================================================================
// Toast Notifications
// ==============================================================================

/**
 * Show toast notification
 * @param {string} message - Toast message
 * @param {string} type - 'success' or 'error'
 */
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toastMessage');

    toastMessage.textContent = message;
    toast.className = `toast ${type}`;
    toast.classList.remove('hidden');

    // Hide after 3 seconds
    setTimeout(() => {
        toast.classList.add('hidden');
    }, 3000);
}

// ==============================================================================
// Auto-load latest results on page load
// ==============================================================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('Test results page loaded');

    // Optionally load most recent test results
    loadLatestResults();
});

/**
 * Load the most recent test results (if any)
 */
async function loadLatestResults() {
    try {
        const response = await fetch('/api/tests/latest');

        if (response.ok) {
            const results = await response.json();
            if (results && results.suite) {
                displayResults(results);
            }
        }
    } catch (error) {
        console.log('No previous test results found');
    }
}
