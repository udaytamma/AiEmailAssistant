/**
 * Email Digest - JavaScript
 * Handles data loading, button interactions, and dynamic content rendering
 */

// ===== State Management =====
let isRefreshing = false;
let checkStatusInterval = null;

// ===== DOM Elements =====
const refreshBtn = document.getElementById('refreshBtn');
const loadingOverlay = document.getElementById('loadingOverlay');
const errorMessage = document.getElementById('errorMessage');
const errorText = document.getElementById('errorText');
const digestContent = document.getElementById('digestContent');
const emptyState = document.getElementById('emptyState');

// Metadata elements
const lastRefreshedEl = document.getElementById('lastRefreshed');
const executionTimeEl = document.getElementById('executionTime');

// Section elements
const needActionSection = document.getElementById('needActionSection');
const needActionContent = document.getElementById('needActionContent');
const needActionCount = document.getElementById('needActionCount');

const fyiSection = document.getElementById('fyiSection');
const fyiContent = document.getElementById('fyiContent');
const fyiCount = document.getElementById('fyiCount');

const newslettersSection = document.getElementById('newslettersSection');
const newslettersContent = document.getElementById('newslettersContent');
const newslettersCount = document.getElementById('newslettersCount');

// ===== Utility Functions =====

/**
 * Format ISO datetime string to readable format
 */
function formatDateTime(isoString) {
    const date = new Date(isoString);
    return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Show toast notification
 */
function showToast(message, duration = 3000) {
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toastMessage');

    toastMessage.textContent = message;
    toast.classList.remove('hidden');

    setTimeout(() => {
        toast.classList.add('hidden');
    }, duration);
}

/**
 * Show loading overlay
 */
function showLoading() {
    loadingOverlay.classList.remove('hidden');
}

/**
 * Hide loading overlay
 */
function hideLoading() {
    loadingOverlay.classList.add('hidden');
}

/**
 * Show error message
 */
function showError(message) {
    errorText.textContent = message;
    errorMessage.classList.remove('hidden');
    digestContent.classList.add('hidden');
}

/**
 * Hide error message
 */
function hideError() {
    errorMessage.classList.add('hidden');
}

// ===== Data Loading =====

/**
 * Load digest data from API
 */
async function loadDigestData() {
    try {
        const response = await fetch('/api/digest');

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to load digest data');
        }

        const data = await response.json();
        renderDigest(data);
        hideError();

    } catch (error) {
        console.error('Error loading digest:', error);
        showError(error.message + ' Check the console for more details.');
    }
}

// ===== Rendering Functions =====

/**
 * Render the complete digest
 */
function renderDigest(data) {
    // Update metadata
    lastRefreshedEl.textContent = formatDateTime(data.metadata.last_updated);
    executionTimeEl.textContent = `${data.metadata.execution_time}s`;

    const digest = data.digest;

    // Render Need-Action section
    renderNeedAction(digest.need_action);

    // Render FYI section
    renderFYI(digest.fyi);

    // Render Newsletters section
    renderNewsletters(digest.newsletters);

    // Show digest content
    digestContent.classList.remove('hidden');

    // Check if all sections are empty
    const hasContent = digest.need_action.emails.length > 0 ||
                      digest.fyi.emails.length > 0 ||
                      digest.newsletters.length > 0;

    if (!hasContent) {
        emptyState.classList.remove('hidden');
    } else {
        emptyState.classList.add('hidden');
    }
}

/**
 * Render Need-Action section
 */
function renderNeedAction(needAction) {
    if (needAction.emails.length === 0) {
        needActionSection.classList.add('hidden');
        return;
    }

    needActionSection.classList.remove('hidden');
    needActionCount.textContent = needAction.emails.length;

    const bulletList = document.createElement('ul');
    bulletList.className = 'bullet-list';

    needAction.summary.forEach(point => {
        const li = document.createElement('li');
        li.className = 'bullet-item';
        li.innerHTML = `
            <span class="bullet-icon"></span>
            <span class="bullet-text">${point}</span>
        `;
        bulletList.appendChild(li);
    });

    needActionContent.innerHTML = '';
    needActionContent.appendChild(bulletList);
}

/**
 * Render FYI section
 */
function renderFYI(fyi) {
    if (fyi.emails.length === 0) {
        fyiSection.classList.add('hidden');
        return;
    }

    fyiSection.classList.remove('hidden');
    fyiCount.textContent = fyi.emails.length;

    const bulletList = document.createElement('ul');
    bulletList.className = 'bullet-list';

    fyi.summary.forEach(point => {
        const li = document.createElement('li');
        li.className = 'bullet-item';
        li.innerHTML = `
            <span class="bullet-icon"></span>
            <span class="bullet-text">${point}</span>
        `;
        bulletList.appendChild(li);
    });

    fyiContent.innerHTML = '';
    fyiContent.appendChild(bulletList);
}

/**
 * Render Newsletters section
 */
function renderNewsletters(newsletters) {
    if (newsletters.length === 0) {
        newslettersSection.classList.add('hidden');
        return;
    }

    newslettersSection.classList.remove('hidden');
    newslettersCount.textContent = newsletters.length;

    newslettersContent.innerHTML = '';

    newsletters.forEach((newsletter, index) => {
        const card = document.createElement('div');
        card.className = 'newsletter-card';

        const summaryId = `summary-${index}`;

        card.innerHTML = `
            <div class="newsletter-header" onclick="toggleNewsletter('${summaryId}')">
                <div class="newsletter-info">
                    <div class="newsletter-title">${newsletter.subject}</div>
                    <div class="newsletter-from">From: ${newsletter.from}</div>
                </div>
                <div id="toggle-${summaryId}" class="newsletter-toggle">▼</div>
            </div>
            <div id="${summaryId}" class="newsletter-summary">
                <ul>
                    ${newsletter.summary_points.map(point => `<li>${point}</li>`).join('')}
                </ul>
            </div>
        `;

        newslettersContent.appendChild(card);
    });
}

/**
 * Toggle newsletter expansion
 */
function toggleNewsletter(summaryId) {
    const summary = document.getElementById(summaryId);
    const toggle = document.getElementById(`toggle-${summaryId}`);

    summary.classList.toggle('expanded');
    toggle.classList.toggle('expanded');
}

// Make toggleNewsletter globally accessible
window.toggleNewsletter = toggleNewsletter;

// ===== Refresh Functionality =====

/**
 * Trigger digest refresh
 */
async function refreshDigest() {
    if (isRefreshing) {
        showToast('Refresh already in progress...');
        return;
    }

    try {
        // Disable button
        refreshBtn.disabled = true;
        refreshBtn.querySelector('.btn-text').textContent = 'Refreshing...';

        // Start refresh
        const response = await fetch('/api/refresh', {
            method: 'POST'
        });

        const result = await response.json();

        if (response.status === 409) {
            // Already running
            showToast(result.message);
            refreshBtn.disabled = false;
            refreshBtn.querySelector('.btn-text').textContent = 'Get Latest View';
            return;
        }

        if (!response.ok) {
            throw new Error(result.message || 'Failed to start refresh');
        }

        // Show loading overlay
        showLoading();
        isRefreshing = true;

        // Start checking status (check every 2 seconds = 2000 milliseconds)
        checkStatusInterval = setInterval(checkRefreshStatus, 2000);

        showToast('Fetching emails...');

    } catch (error) {
        console.error('Error starting refresh:', error);
        showToast('Error: ' + error.message);
        refreshBtn.disabled = false;
        refreshBtn.querySelector('.btn-text').textContent = 'Get Latest View';
    }
}

/**
 * Check if refresh is complete
 */
async function checkRefreshStatus() {
    try {
        const response = await fetch('/api/status');
        const status = await response.json();

        if (!status.running) {
            // Refresh complete
            clearInterval(checkStatusInterval);
            isRefreshing = false;
            hideLoading();

            // Re-enable button
            refreshBtn.disabled = false;
            refreshBtn.querySelector('.btn-text').textContent = 'Get Latest View';

            // Reload digest data
            await loadDigestData();

            showToast('✅ Digest updated successfully!');
        }

    } catch (error) {
        console.error('Error checking status:', error);
    }
}

// ===== Event Listeners =====

// Refresh button click
refreshBtn.addEventListener('click', refreshDigest);

// Load digest on page load
document.addEventListener('DOMContentLoaded', () => {
    loadDigestData();
});
