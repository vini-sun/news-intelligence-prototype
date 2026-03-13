// API Configuration
const API_BASE_URL = 'http://localhost:8000';

// Badge color classes (cycle through them for themes)
const BADGE_COLORS = ['badge-blue', 'badge-green', 'badge-purple', 'badge-orange', 'badge-teal'];

// Current page state
let currentPage = 'home';

// Current run ID for editing
let currentRunId = null;

// Original executive summary (for cancel functionality)
let originalExecutiveSummary = [];

// Current articles data (for sorting)
let currentArticles = [];

// Load dashboard data on page load (without running pipeline)
document.addEventListener('DOMContentLoaded', () => {
    loadDashboardDataOnly();
});

/**
 * Toggle sidebar collapsed/expanded state
 */
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('collapsed');

    // Close topic dropdown if open
    const topicDropdown = document.getElementById('topicDropdown');
    if (topicDropdown) {
        topicDropdown.style.display = 'none';
    }
}

/**
 * Toggle topic dropdown
 */
function toggleTopicDropdown() {
    const dropdown = document.getElementById('topicDropdown');
    const selector = document.querySelector('.topic-selector');

    if (dropdown.style.display === 'none' || !dropdown.style.display) {
        dropdown.style.display = 'block';
        selector.classList.add('open');
    } else {
        dropdown.style.display = 'none';
        selector.classList.remove('open');
    }
}

/**
 * Close topic dropdown when clicking outside
 */
document.addEventListener('click', function(event) {
    const dropdown = document.getElementById('topicDropdown');
    const selector = document.querySelector('.topic-selector');

    if (dropdown && selector) {
        if (!selector.contains(event.target) && !dropdown.contains(event.target)) {
            dropdown.style.display = 'none';
            selector.classList.remove('open');
        }
    }
});

/**
 * Open add topic modal
 */
function openAddTopicModal(event) {
    event.stopPropagation();

    // Close the topic dropdown
    const dropdown = document.getElementById('topicDropdown');
    const selector = document.querySelector('.topic-selector');
    if (dropdown) dropdown.style.display = 'none';
    if (selector) selector.classList.remove('open');

    // Open the modal
    const modal = document.getElementById('addTopicModal');
    if (modal) {
        modal.style.display = 'flex';

        // Clear form fields
        document.getElementById('topicTitle').value = '';
        document.getElementById('topicSubtopics').value = '';
        document.getElementById('topicAvoid').value = '';

        // Focus on title input
        setTimeout(() => {
            document.getElementById('topicTitle').focus();
        }, 100);
    }
}

/**
 * Close add topic modal
 */
function closeAddTopicModal(event) {
    if (event) {
        event.stopPropagation();
    }

    const modal = document.getElementById('addTopicModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

/**
 * Save new topic
 */
function saveNewTopic() {
    const title = document.getElementById('topicTitle').value.trim();
    const subtopics = document.getElementById('topicSubtopics').value.trim();
    const topicsToAvoid = document.getElementById('topicAvoid').value.trim();

    if (!title) {
        alert('Please enter a topic title');
        return;
    }

    // TODO: Save topic to backend/database
    console.log('New topic:', {
        title,
        subtopics,
        topicsToAvoid
    });

    // For now, just show a success message and close the modal
    alert(`Topic "${title}" created! (This feature will be fully implemented soon)`);
    closeAddTopicModal();
}

/**
 * Toggle profile panel
 */
function toggleProfilePanel() {
    const panel = document.getElementById('profilePanel');
    const overlay = document.getElementById('profilePanelOverlay');

    if (panel && overlay) {
        if (panel.classList.contains('open')) {
            // Close panel
            panel.classList.remove('open');
            overlay.style.display = 'none';
        } else {
            // Open panel
            panel.classList.add('open');
            overlay.style.display = 'block';
        }
    }
}

/**
 * Navigate to different pages
 */
function navigateTo(page) {
    // Hide all pages
    const pages = ['home', 'executive-summaries', 'theme-mapping', 'articles'];
    pages.forEach(p => {
        const pageElement = document.getElementById(p === 'home' ? 'homePage' :
            p === 'executive-summaries' ? 'executiveSummariesPage' :
            p === 'theme-mapping' ? 'themeMappingPage' : 'articlesPage');
        if (pageElement) {
            pageElement.style.display = 'none';
        }
    });

    // Show selected page
    const targetPage = page === 'home' ? 'homePage' :
        page === 'executive-summaries' ? 'executiveSummariesPage' :
        page === 'theme-mapping' ? 'themeMappingPage' : 'articlesPage';

    const pageElement = document.getElementById(targetPage);
    if (pageElement) {
        pageElement.style.display = 'block';
    }

    // Update active nav button
    const navButtons = document.querySelectorAll('.nav-button');
    navButtons.forEach((button, index) => {
        button.classList.remove('nav-button-active');
        if ((index === 0 && page === 'home') ||
            (index === 1 && page === 'executive-summaries') ||
            (index === 2 && page === 'theme-mapping') ||
            (index === 3 && page === 'articles')) {
            button.classList.add('nav-button-active');
        }
    });

    currentPage = page;
}

// Store loading interval
let loadingInterval = null;
let loadingStep = 0;

/**
 * Fetch and display dashboard data from API (page load - no pipeline execution)
 */
async function loadDashboardDataOnly() {
    try {
        showLoadingState('Loading dashboard data...');

        // Fetch data from API (GET endpoint - no pipeline execution)
        const response = await fetch(`${API_BASE_URL}/dashboard`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Store current run ID
        currentRunId = data.run_id;
        originalExecutiveSummary = data.executive_summary || [];

        // Populate UI with data
        populateExecutiveBrief(data.executive_summary || []);
        populateThemeSignals(data.themes || []);
        populateArticles(data.articles || []);
        updateLastUpdatedTime(data.last_updated);

    } catch (error) {
        console.error('Error loading dashboard data:', error);
        showError(error.message);
    }
}

/**
 * Run pipeline and fetch fresh dashboard data (refresh button click)
 */
async function loadDashboardData() {
    const refreshButton = document.getElementById('refreshButton');

    try {
        // Disable refresh button
        refreshButton.disabled = true;
        refreshButton.style.opacity = '0.6';
        refreshButton.style.cursor = 'not-allowed';

        // Start progressive loading animation
        startLoadingAnimation();

        // Fetch data from API (POST endpoint - runs pipeline)
        const response = await fetch(`${API_BASE_URL}/dashboard/refresh`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            stopLoadingAnimation();
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Stop loading animation
        stopLoadingAnimation();

        // Store current run ID
        currentRunId = data.run_id;
        originalExecutiveSummary = data.executive_summary || [];

        // Populate UI with data
        populateExecutiveBrief(data.executive_summary || []);
        populateThemeSignals(data.themes || []);
        populateArticles(data.articles || []);
        updateLastUpdatedTime(data.last_updated);

    } catch (error) {
        stopLoadingAnimation();
        console.error('Error loading dashboard data:', error);
        showError(error.message);
    } finally {
        // Re-enable refresh button
        refreshButton.disabled = false;
        refreshButton.style.opacity = '1';
        refreshButton.style.cursor = 'pointer';
    }
}

/**
 * Start loading animation that cycles through steps
 */
function startLoadingAnimation() {
    const steps = [
        'Analyzing latest articles...',
        'Detecting themes...',
        'Generating executive briefing...'
    ];

    loadingStep = 0;
    showLoadingState(steps[0]);

    // Cycle through loading messages every 8 seconds
    loadingInterval = setInterval(() => {
        loadingStep = (loadingStep + 1) % steps.length;
        showLoadingState(steps[loadingStep]);
    }, 8000);
}

/**
 * Stop loading animation
 */
function stopLoadingAnimation() {
    if (loadingInterval) {
        clearInterval(loadingInterval);
        loadingInterval = null;
    }
}

/**
 * Show loading state with custom message
 */
function showLoadingState(message) {
    const loadingHTML = `<li class="loading"><span class="loading-spinner"></span>${escapeHtml(message)}</li>`;
    const loadingCardHTML = `<div class="loading-card"><span class="loading-spinner"></span>${escapeHtml(message)}</div>`;

    document.getElementById('executiveBrief').innerHTML = loadingHTML;
    document.getElementById('themeSignals').innerHTML = loadingCardHTML;
    document.getElementById('articleFeed').innerHTML = loadingCardHTML;
    document.getElementById('lastUpdated').textContent = 'Loading...';
}

/**
 * Show error message
 */
function showError(message) {
    document.getElementById('executiveBrief').innerHTML = `<li class="loading">Error: ${message}</li>`;
    document.getElementById('themeSignals').innerHTML = `<div class="loading-card">Error loading themes</div>`;
    document.getElementById('articleFeed').innerHTML = `<div class="loading-card">Error loading articles</div>`;
}

/**
 * Populate executive brief section
 */
function populateExecutiveBrief(bullets) {
    const container = document.getElementById('executiveBrief');

    if (!bullets || bullets.length === 0) {
        container.innerHTML = '<li class="loading">No executive summary available</li>';
        return;
    }

    container.innerHTML = bullets.map(bullet => `<li>${escapeHtml(bullet)}</li>`).join('');
}

/**
 * Populate theme signals section
 */
function populateThemeSignals(themes) {
    const container = document.getElementById('themeSignals');

    if (!themes || themes.length === 0) {
        container.innerHTML = '<div class="loading-card">No themes available</div>';
        return;
    }

    container.innerHTML = themes.map((themeData, index) => {
        const colorClass = BADGE_COLORS[index % BADGE_COLORS.length];
        return `
            <div class="theme-card">
                <div class="theme-header">
                    <div class="theme-name">${escapeHtml(themeData.theme)}</div>
                    <div class="theme-icon">📊</div>
                </div>
                <div class="theme-count">${themeData.mentions}</div>
                <div class="theme-label">mentions</div>
            </div>
        `;
    }).join('');
}

/**
 * Populate articles section
 */
function populateArticles(articles) {
    const container = document.getElementById('articleFeed');

    if (!articles || articles.length === 0) {
        container.innerHTML = '<div class="loading-card">No articles available</div>';
        currentArticles = [];
        return;
    }

    // Store articles globally for sorting
    currentArticles = articles;

    container.innerHTML = articles.map((article, index) => {
        const colorClass = getThemeBadgeColor(article.theme, index);
        const formattedDate = formatDate(article.date);

        return `
            <div class="article-card-wrapper" onclick="flipCard(event, this)">
                <div class="article-card">
                    <!-- Front of card -->
                    <div class="article-card-front">
                        <div class="article-header">
                            <h4 class="article-title">${escapeHtml(article.title)}</h4>
                        </div>
                        ${article.theme ? `<span class="article-badge ${colorClass}">${escapeHtml(article.theme)}</span>` : ''}
                        <div class="article-meta">
                            <span>${escapeHtml(article.source)}</span>
                            <span class="article-meta-separator">•</span>
                            <span>${formattedDate}</span>
                        </div>
                        <a href="${escapeHtml(article.url)}" target="_blank" rel="noopener noreferrer" class="article-link" onclick="event.stopPropagation()">
                            Read Article →
                        </a>
                        <div class="flip-hint">Click to view summary</div>
                    </div>

                    <!-- Back of card -->
                    <div class="article-card-back">
                        <p class="article-summary">${escapeHtml(article.summary)}</p>
                        <a href="${escapeHtml(article.url)}" target="_blank" rel="noopener noreferrer" class="article-link" onclick="event.stopPropagation()">
                            Read Article →
                        </a>
                        <div class="flip-hint">Click to go back</div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * Flip article card to show summary
 */
function flipCard(event, cardWrapper) {
    // Don't flip if clicking on a link
    if (event.target.tagName === 'A') {
        return;
    }

    cardWrapper.classList.toggle('flipped');
}

/**
 * Sort articles based on selected option
 */
function sortArticles() {
    const sortSelect = document.getElementById('articleSortSelect');
    const sortValue = sortSelect.value;

    if (!currentArticles || currentArticles.length === 0) {
        return;
    }

    // Create a copy of the articles array to sort
    let sortedArticles = [...currentArticles];

    if (sortValue === 'newest') {
        // Sort by date descending (newest first)
        sortedArticles.sort((a, b) => {
            const dateA = a.date ? new Date(a.date) : new Date(0);
            const dateB = b.date ? new Date(b.date) : new Date(0);
            return dateB - dateA;
        });
    } else if (sortValue === 'oldest') {
        // Sort by date ascending (oldest first)
        sortedArticles.sort((a, b) => {
            const dateA = a.date ? new Date(a.date) : new Date(0);
            const dateB = b.date ? new Date(b.date) : new Date(0);
            return dateA - dateB;
        });
    }

    // Re-populate the articles with sorted data
    populateArticles(sortedArticles);
}

/**
 * Get badge color class for a theme (consistent colors for same themes)
 */
function getThemeBadgeColor(theme, fallbackIndex) {
    if (!theme) return BADGE_COLORS[0];

    // Use hash of theme name to get consistent color
    let hash = 0;
    for (let i = 0; i < theme.length; i++) {
        hash = theme.charCodeAt(i) + ((hash << 5) - hash);
    }

    const index = Math.abs(hash) % BADGE_COLORS.length;
    return BADGE_COLORS[index];
}

/**
 * Update last updated timestamp
 */
function updateLastUpdatedTime(isoTimestamp) {
    const element = document.getElementById('lastUpdated');

    if (!isoTimestamp) {
        element.textContent = 'Unknown';
        return;
    }

    try {
        const date = new Date(isoTimestamp);
        element.textContent = date.toLocaleString('en-US', {
            month: '2-digit',
            day: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: true
        });
    } catch (error) {
        element.textContent = 'Invalid date';
    }
}

/**
 * Format date for display
 */
function formatDate(dateString) {
    if (!dateString) return 'Unknown date';

    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        });
    } catch (error) {
        return dateString;
    }
}

/**
 * Truncate text to specified length
 */
function truncate(text, maxLength) {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength).trim() + '...';
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Enable edit mode for executive brief
 */
function enableEditMode() {
    const list = document.getElementById('executiveBrief');
    const editButton = document.getElementById('editBriefButton');
    const saveButton = document.getElementById('saveBriefButton');
    const cancelButton = document.getElementById('cancelBriefButton');

    // Add edit-mode class
    list.classList.add('edit-mode');

    // Get current bullets
    const bullets = [];
    const listItems = list.querySelectorAll('li');
    listItems.forEach(item => {
        const text = item.textContent.trim();
        if (text && !text.startsWith('Loading') && !text.startsWith('No executive')) {
            bullets.push(text);
        }
    });

    // Recreate list with editable inputs
    list.innerHTML = bullets.map((bullet, index) => `
        <li>
            <input type="text" value="${escapeHtml(bullet)}" data-index="${index}" />
            <button class="delete-bullet" onclick="deleteBulletPoint(${index})">✖</button>
        </li>
    `).join('');

    // Show/hide buttons
    editButton.style.display = 'none';
    saveButton.style.display = 'inline-block';
    cancelButton.style.display = 'inline-block';
}

/**
 * Cancel edit mode and restore original data
 */
function cancelEditMode() {
    const list = document.getElementById('executiveBrief');
    const editButton = document.getElementById('editBriefButton');
    const saveButton = document.getElementById('saveBriefButton');
    const cancelButton = document.getElementById('cancelBriefButton');

    // Remove edit-mode class
    list.classList.remove('edit-mode');

    // Restore original executive summary
    populateExecutiveBrief(originalExecutiveSummary);

    // Show/hide buttons
    editButton.style.display = 'inline-block';
    saveButton.style.display = 'none';
    cancelButton.style.display = 'none';
}

/**
 * Save edited executive brief
 */
async function saveExecutiveBrief() {
    const list = document.getElementById('executiveBrief');
    const editButton = document.getElementById('editBriefButton');
    const saveButton = document.getElementById('saveBriefButton');
    const cancelButton = document.getElementById('cancelBriefButton');

    // Collect all bullet points from inputs
    const inputs = list.querySelectorAll('input[type="text"]');
    const bullets = [];
    inputs.forEach(input => {
        const text = input.value.trim();
        if (text) {
            bullets.push(text);
        }
    });

    if (bullets.length === 0) {
        alert('Please add at least one bullet point');
        return;
    }

    if (!currentRunId) {
        alert('No run ID available. Please refresh the dashboard.');
        return;
    }

    try {
        // Disable save button
        saveButton.disabled = true;
        saveButton.textContent = '💾 Saving...';

        // Send update request
        const response = await fetch(`${API_BASE_URL}/dashboard/executive-summary`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                run_id: currentRunId,
                executive_summary: bullets
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();

        // Update original data
        originalExecutiveSummary = bullets;

        // Exit edit mode
        list.classList.remove('edit-mode');
        populateExecutiveBrief(bullets);

        // Show/hide buttons
        editButton.style.display = 'inline-block';
        saveButton.style.display = 'none';
        cancelButton.style.display = 'none';
        saveButton.disabled = false;
        saveButton.textContent = '💾 Save';

        // Show success message (optional)
        console.log('Executive summary updated successfully');

    } catch (error) {
        console.error('Error saving executive brief:', error);
        alert('Failed to save executive brief. Please try again.');
        saveButton.disabled = false;
        saveButton.textContent = '💾 Save';
    }
}

/**
 * Add a new bullet point
 */
function addBulletPoint() {
    const list = document.getElementById('executiveBrief');
    const newItem = document.createElement('li');
    const newIndex = list.querySelectorAll('li').length;

    newItem.innerHTML = `
        <input type="text" value="" placeholder="Enter new bullet point..." data-index="${newIndex}" />
        <button class="delete-bullet" onclick="deleteBulletPoint(${newIndex})">✖</button>
    `;

    list.appendChild(newItem);

    // Focus on the new input
    const newInput = newItem.querySelector('input');
    if (newInput) {
        newInput.focus();
    }
}

/**
 * Delete a bullet point
 */
function deleteBulletPoint(index) {
    const list = document.getElementById('executiveBrief');
    const listItems = list.querySelectorAll('li');

    if (listItems.length > 1) {
        listItems[index].remove();

        // Re-index remaining items
        const remainingItems = list.querySelectorAll('li');
        remainingItems.forEach((item, newIndex) => {
            const input = item.querySelector('input');
            const deleteBtn = item.querySelector('.delete-bullet');
            if (input) input.setAttribute('data-index', newIndex);
            if (deleteBtn) deleteBtn.setAttribute('onclick', `deleteBulletPoint(${newIndex})`);
        });
    } else {
        alert('You must have at least one bullet point');
    }
}
