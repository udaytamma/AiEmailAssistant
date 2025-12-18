/**
 * Email Digest - JavaScript
 * Handles data loading, button interactions, and dynamic content rendering
 */

// ===== Theme Management =====
let manualThemeOverride = localStorage.getItem('themeOverride'); // 'light', 'dark', or null for auto

function applyDarkModeBasedOnTime() {
    // Check if manual override is set
    if (manualThemeOverride) {
        if (manualThemeOverride === 'dark') {
            document.body.classList.add('dark-mode');
        } else {
            document.body.classList.remove('dark-mode');
        }
        updateThemeButton();
        return;
    }

    // Auto mode: based on time
    const now = new Date();

    // Convert to CST (UTC-6)
    const cstOffset = -6 * 60; // CST is UTC-6
    const utcTime = now.getTime() + (now.getTimezoneOffset() * 60000);
    const cstTime = new Date(utcTime + (cstOffset * 60000));

    const hour = cstTime.getHours();

    // Dark mode: 5pm (17:00) to 8am (08:00) CST
    const isDarkTime = hour >= 17 || hour < 8;

    if (isDarkTime) {
        document.body.classList.add('dark-mode');
    } else {
        document.body.classList.remove('dark-mode');
    }

    updateThemeButton();
}

function toggleTheme() {
    const isDark = document.body.classList.contains('dark-mode');

    if (isDark) {
        // Switch to light
        manualThemeOverride = 'light';
        document.body.classList.remove('dark-mode');
    } else {
        // Switch to dark
        manualThemeOverride = 'dark';
        document.body.classList.add('dark-mode');
    }

    localStorage.setItem('themeOverride', manualThemeOverride);
    updateThemeButton();
}

function updateThemeButton() {
    const themeIcon = document.getElementById('themeIcon');
    const themeText = document.getElementById('themeText');
    const isDark = document.body.classList.contains('dark-mode');

    if (isDark) {
        themeIcon.textContent = '☀️';
        themeText.textContent = 'Light';
    } else {
        themeIcon.textContent = '🌙';
        themeText.textContent = 'Dark';
    }
}

// Apply theme on page load and check every minute
applyDarkModeBasedOnTime();
setInterval(applyDarkModeBasedOnTime, 60000); // Check every minute

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

const marketingSection = document.getElementById('marketingSection');
const marketingContent = document.getElementById('marketingContent');
const marketingCount = document.getElementById('marketingCount');

const spamSection = document.getElementById('spamSection');
const spamContent = document.getElementById('spamContent');
const spamCount = document.getElementById('spamCount');

const otherSection = document.getElementById('otherSection');
const otherContent = document.getElementById('otherContent');
const otherCount = document.getElementById('otherCount');

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

    // Render additional categories from categorized_emails
    renderAdditionalCategories(data.categorized_emails);

    // Show digest content
    digestContent.classList.remove('hidden');

    // Check if all sections are empty
    const hasContent = digest.need_action.emails.length > 0 ||
                      digest.fyi.emails.length > 0 ||
                      digest.newsletters.length > 0 ||
                      data.categorized_emails.length > 0;

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

/**
 * Render additional categories (Marketing, SPAM, Other)
 */
function renderAdditionalCategories(categorizedEmails) {
    // Group emails by category
    const categories = {
        'Marketing': [],
        'SPAM': [],
        'Other': []
    };

    categorizedEmails.forEach(email => {
        const category = email.category;
        if (category === 'Marketing') {
            categories['Marketing'].push(email);
        } else if (category === 'SPAM') {
            categories['SPAM'].push(email);
        } else if (!['Need-Action', 'FYI', 'Newsletter'].includes(category)) {
            categories['Other'].push(email);
        }
    });

    // Render Marketing
    renderCategorySection(
        categories['Marketing'],
        marketingSection,
        marketingContent,
        marketingCount
    );

    // Render SPAM
    renderCategorySection(
        categories['SPAM'],
        spamSection,
        spamContent,
        spamCount
    );

    // Render Other
    renderCategorySection(
        categories['Other'],
        otherSection,
        otherContent,
        otherCount
    );
}

/**
 * Render a generic category section with email list
 */
function renderCategorySection(emails, sectionEl, contentEl, countEl) {
    if (emails.length === 0) {
        sectionEl.classList.add('hidden');
        return;
    }

    sectionEl.classList.remove('hidden');
    countEl.textContent = emails.length;

    const emailList = document.createElement('div');
    emailList.className = 'email-list';

    emails.forEach(email => {
        const emailCard = document.createElement('div');
        emailCard.className = 'email-card';

        emailCard.innerHTML = `
            <div class="email-subject">${email.subject}</div>
            <div class="email-from">From: ${email.from}</div>
            <div class="email-summary">${email.summary}</div>
            ${email.action_item !== 'None' ? `<div class="email-action">Action: ${email.action_item}</div>` : ''}
        `;

        emailList.appendChild(emailCard);
    });

    contentEl.innerHTML = '';
    contentEl.appendChild(emailList);
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
    loadRecentErrors();
});

// ===== Metrics Modal Functions =====

/**
 * Open metrics modal and load data
 */
async function openMetricsModal() {
    const modal = document.getElementById('metricsModal');
    modal.classList.remove('hidden');

    // Load metrics
    await loadMetrics('24h');
}

/**
 * Close metrics modal
 */
function closeMetricsModal() {
    const modal = document.getElementById('metricsModal');
    modal.classList.add('hidden');
}

/**
 * Load metrics for a specific time period
 */
async function loadMetrics(period) {
    const metricsContent = document.getElementById('metricsContent');

    // Update active tab
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.tab === period) {
            btn.classList.add('active');
        }
    });

    try {
        const response = await fetch('/api/metrics');
        const data = await response.json();

        const metrics = data[period];
        if (!metrics) {
            metricsContent.innerHTML = '<p class="error">No metrics available for this period.</p>';
            return;
        }

        // Render metrics grid
        let html = '<div class="metrics-grid">';

        html += `
            <div class="metric-card">
                <div class="metric-label">Total Emails</div>
                <div class="metric-value">${metrics.total_emails_processed || 0}</div>
            </div>
        `;

        html += `
            <div class="metric-card">
                <div class="metric-label">Script Runs</div>
                <div class="metric-value">${metrics.script_run_count || 0}</div>
            </div>
        `;

        html += `
            <div class="metric-card">
                <div class="metric-label">Success Rate</div>
                <div class="metric-value">${(metrics.success_rate || 0).toFixed(1)}<span class="metric-unit">%</span></div>
            </div>
        `;

        html += `
            <div class="metric-card">
                <div class="metric-label">Cache Hit Rate</div>
                <div class="metric-value">${(metrics.cache_hit_rate || 0).toFixed(1)}<span class="metric-unit">%</span></div>
            </div>
        `;

        html += `
            <div class="metric-card">
                <div class="metric-label">API Calls</div>
                <div class="metric-value">${metrics.api_calls_made || 0}</div>
            </div>
        `;

        html += `
            <div class="metric-card">
                <div class="metric-label">Avg Execution Time</div>
                <div class="metric-value">${(metrics.avg_execution_time || 0).toFixed(1)}<span class="metric-unit">s</span></div>
            </div>
        `;

        if (period === 'all_time') {
            html += `
                <div class="metric-card">
                    <div class="metric-label">Estimated API Cost</div>
                    <div class="metric-value">$${(metrics.estimated_api_cost || 0).toFixed(2)}</div>
                </div>
            `;

            html += `
                <div class="metric-card">
                    <div class="metric-label">Avg API Response</div>
                    <div class="metric-value">${(metrics.avg_api_response_time || 0).toFixed(2)}<span class="metric-unit">s</span></div>
                </div>
            `;
        }

        if (period === '24h') {
            html += `
                <div class="metric-card">
                    <div class="metric-label">Errors (24h)</div>
                    <div class="metric-value">${metrics.error_count || 0}</div>
                </div>
            `;
        }

        html += '</div>';

        // Show emails by category for all-time
        if (period === 'all_time' && metrics.emails_by_category) {
            html += '<h3>Emails by Category</h3>';
            html += '<div class="metrics-grid">';
            for (const [category, count] of Object.entries(metrics.emails_by_category)) {
                html += `
                    <div class="metric-card">
                        <div class="metric-label">${category}</div>
                        <div class="metric-value">${count}</div>
                    </div>
                `;
            }
            html += '</div>';
        }

        metricsContent.innerHTML = html;

    } catch (error) {
        console.error('Error loading metrics:', error);
        metricsContent.innerHTML = '<p class="error">Failed to load metrics. Please try again.</p>';
    }
}

/**
 * Load and display recent errors
 */
async function loadRecentErrors() {
    try {
        const response = await fetch('/api/errors');
        const data = await response.json();

        if (data.errors && data.errors.length > 0) {
            const errorsSection = document.getElementById('recentErrorsSection');
            const errorsContent = document.getElementById('recentErrorsContent');

            let html = '';
            data.errors.forEach(error => {
                html += `
                    <div class="error-item">
                        <div class="error-time">${formatDateTime(error.timestamp)}</div>
                        <div class="error-module">${error.module} - ${error.error_type}</div>
                        <div class="error-message-text">${error.error_message}</div>
                    </div>
                `;
            });

            errorsContent.innerHTML = html;
            errorsSection.classList.remove('hidden');
        }
    } catch (error) {
        console.error('Error loading recent errors:', error);
    }
}

/**
 * Dismiss errors section
 */
function dismissErrors() {
    const errorsSection = document.getElementById('recentErrorsSection');
    errorsSection.classList.add('hidden');
}

// ===== Context Memory Modal Functions =====

/**
 * Open context memory modal and load today's summary
 */
async function openContextMemoryModal() {
    const modal = document.getElementById('contextMemoryModal');
    modal.classList.remove('hidden');

    // Load context memory
    await loadContextMemory();
}

/**
 * Close context memory modal
 */
function closeContextMemoryModal() {
    const modal = document.getElementById('contextMemoryModal');
    modal.classList.add('hidden');
}

/**
 * Load context memory from API
 */
async function loadContextMemory() {
    const content = document.getElementById('contextMemoryContent');
    content.innerHTML = '<p class="loading-text">Loading context memory...</p>';

    try {
        const response = await fetch('/api/context-memory/latest');
        if (!response.ok) {
            throw new Error('Failed to load context memory');
        }

        const data = await response.json();

        if (!data || !data.elaborate_summary || data.elaborate_summary.length === 0) {
            content.innerHTML = '<p class="no-data-message">No context memory available for today.</p>';
            return;
        }

        // Display context memory
        let html = `
            <div class="context-memory-info">
                <div class="info-item">
                    <span class="info-label">Date:</span>
                    <span class="info-value">${formatDate(data.timestamp)}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Emails Processed:</span>
                    <span class="info-value">${data.email_count}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Categories:</span>
                    <span class="info-value">${data.categories.join(', ')}</span>
                </div>
            </div>

            <div class="context-summary">
                <h3>📋 Today's Email Context Summary</h3>
                <ul class="summary-bullets">
        `;

        data.elaborate_summary.forEach((bullet, idx) => {
            html += `<li class="summary-bullet">${bullet}</li>`;
        });

        html += `
                </ul>
            </div>
        `;

        content.innerHTML = html;

    } catch (error) {
        console.error('Error loading context memory:', error);
        content.innerHTML = `
            <div class="error-message-inline">
                <p>⚠️ Failed to load context memory</p>
                <p class="error-details">${error.message}</p>
            </div>
        `;
    }
}

/**
 * Format date for display
 */
function formatDate(isoString) {
    const date = new Date(isoString);
    return date.toLocaleDateString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

// ===== Additional Event Listeners =====

// Context Memory button click
const contextMemoryBtn = document.getElementById('contextMemoryBtn');
if (contextMemoryBtn) {
    contextMemoryBtn.addEventListener('click', openContextMemoryModal);
}

// Metrics button click
const metricsBtn = document.getElementById('metricsBtn');
if (metricsBtn) {
    metricsBtn.addEventListener('click', openMetricsModal);
}

// Close modal on background click
const metricsModal = document.getElementById('metricsModal');
if (metricsModal) {
    metricsModal.addEventListener('click', function(e) {
        if (e.target === this) {
            closeMetricsModal();
        }
    });
}

// Tab switching
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        loadMetrics(btn.dataset.tab);
    });
});

// Make functions globally accessible
window.closeMetricsModal = closeMetricsModal;
window.dismissErrors = dismissErrors;

// ===== Event Listeners =====
document.getElementById('themeToggleBtn').addEventListener('click', toggleTheme);
