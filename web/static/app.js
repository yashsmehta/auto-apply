/**
 * Auto-Apply Web Interface
 * Enhanced with URL validation, copy-to-clipboard, export, and keyboard shortcuts
 */

// Global state
let currentResults = null;

// URL validation regex (matches server-side pattern)
const URL_REGEX = /^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$/;

// DOM Elements
const elements = {
    // Forms
    singleForm: document.getElementById('single-form'),
    csvForm: document.getElementById('csv-form'),
    
    // Inputs
    infoUrlInput: document.getElementById('info-url'),
    formUrlInput: document.getElementById('form-url'),
    csvFileInput: document.getElementById('csv-file'),
    
    // Error displays
    infoUrlError: document.getElementById('info-url-error'),
    formUrlError: document.getElementById('form-url-error'),
    csvError: document.getElementById('csv-error'),
    
    // Tabs
    tabButtons: document.querySelectorAll('.tab-button'),
    singleTab: document.getElementById('single-tab'),
    csvTab: document.getElementById('csv-tab'),
    
    // Results
    resultsSection: document.getElementById('results-section'),
    resultsContainer: document.getElementById('results-container'),
    
    // Actions
    copyAllBtn: document.getElementById('copy-all-btn'),
    exportJsonBtn: document.getElementById('export-json-btn'),
    exportMarkdownBtn: document.getElementById('export-markdown-btn'),
    clearResultsBtn: document.getElementById('clear-results-btn'),
    
    // Toast
    copyToast: document.getElementById('copy-toast')
};

// Initialize event listeners
function init() {
    // Tab switching
    elements.tabButtons.forEach(button => {
        button.addEventListener('click', () => switchTab(button.dataset.tab));
    });
    
    // Form submissions
    elements.singleForm.addEventListener('submit', handleSingleSubmit);
    elements.csvForm.addEventListener('submit', handleCsvSubmit);
    
    // URL validation on input
    elements.infoUrlInput.addEventListener('input', () => validateUrlInput(elements.infoUrlInput, elements.infoUrlError));
    elements.formUrlInput.addEventListener('input', () => validateUrlInput(elements.formUrlInput, elements.formUrlError));
    
    // URL validation on blur
    elements.infoUrlInput.addEventListener('blur', () => validateUrlInput(elements.infoUrlInput, elements.infoUrlError));
    elements.formUrlInput.addEventListener('blur', () => validateUrlInput(elements.formUrlInput, elements.formUrlError));
    
    // Action buttons
    elements.copyAllBtn.addEventListener('click', copyAllResults);
    elements.exportJsonBtn.addEventListener('click', () => exportResults('json'));
    elements.exportMarkdownBtn.addEventListener('click', () => exportResults('markdown'));
    elements.clearResultsBtn.addEventListener('click', clearResults);
    
    // Keyboard shortcuts
    document.addEventListener('keydown', handleKeyboardShortcuts);
    
    // Individual crawl buttons
    document.getElementById('crawl-info-btn')?.addEventListener('click', crawlInfo);
    document.getElementById('crawl-form-btn')?.addEventListener('click', crawlForm);
}

// Tab switching
function switchTab(tabName) {
    elements.tabButtons.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    
    elements.singleTab.classList.toggle('active', tabName === 'single');
    elements.csvTab.classList.toggle('active', tabName === 'csv');
}

// URL validation
function validateUrlInput(input, errorElement) {
    const url = input.value.trim();
    
    if (!url) {
        errorElement.textContent = '';
        input.classList.remove('invalid');
        return true;
    }
    
    if (!URL_REGEX.test(url)) {
        errorElement.textContent = 'Please enter a valid URL starting with http:// or https://';
        input.classList.add('invalid');
        return false;
    }
    
    // Additional server-side validation
    validateUrlServer(url).then(result => {
        if (!result.valid) {
            errorElement.textContent = result.error;
            input.classList.add('invalid');
        } else {
            errorElement.textContent = '';
            input.classList.remove('invalid');
        }
    });
    
    return true;
}

// Server-side URL validation
async function validateUrlServer(url) {
    try {
        const response = await fetch('/api/validate-url', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });
        
        return await response.json();
    } catch (error) {
        return { valid: false, error: 'Validation error' };
    }
}

// Crawl info URL only
async function crawlInfo() {
    const url = elements.infoUrlInput.value.trim();
    if (!url || !validateUrlInput(elements.infoUrlInput, elements.infoUrlError)) {
        return;
    }
    
    const button = document.getElementById('crawl-info-btn');
    setLoadingState(button, true);
    
    try {
        const response = await fetch('/crawl/info', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to crawl info URL');
        }
        
        // Display info results
        displayInfoResults(data);
        
    } catch (error) {
        showError('Error crawling info URL: ' + error.message);
    } finally {
        setLoadingState(button, false);
    }
}

// Crawl form URL only
async function crawlForm() {
    const url = elements.formUrlInput.value.trim();
    if (!url || !validateUrlInput(elements.formUrlInput, elements.formUrlError)) {
        return;
    }
    
    const button = document.getElementById('crawl-form-btn');
    setLoadingState(button, true);
    
    try {
        const response = await fetch('/crawl/form', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to crawl form URL');
        }
        
        // Display questions results
        displayQuestionsResults(data);
        
    } catch (error) {
        showError('Error crawling form URL: ' + error.message);
    } finally {
        setLoadingState(button, false);
    }
}

// Handle single application submission
async function handleSingleSubmit(e) {
    e.preventDefault();
    
    const infoUrl = elements.infoUrlInput.value.trim();
    const formUrl = elements.formUrlInput.value.trim();
    
    // Validate URLs
    const infoValid = validateUrlInput(elements.infoUrlInput, elements.infoUrlError);
    const formValid = validateUrlInput(elements.formUrlInput, elements.formUrlError);
    
    if (!infoValid || !formValid) {
        return;
    }
    
    // Show loading state
    const submitBtn = e.target.querySelector('button[type="submit"]');
    setLoadingState(submitBtn, true);
    
    try {
        const response = await fetch('/process', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ info_url: infoUrl, form_url: formUrl })
        });
        
        const data = await response.json();
        
        if (!response.ok && !data.partial_results) {
            throw new Error(data.error || 'Processing failed');
        }
        
        // Display results
        currentResults = data;
        displaySingleResult(data);
        
    } catch (error) {
        showError('Error processing application: ' + error.message);
    } finally {
        setLoadingState(submitBtn, false);
    }
}

// Handle CSV upload
async function handleCsvSubmit(e) {
    e.preventDefault();
    
    const file = elements.csvFileInput.files[0];
    if (!file) {
        elements.csvError.textContent = 'Please select a CSV file';
        return;
    }
    
    // Show loading state
    const submitBtn = e.target.querySelector('button[type="submit"]');
    setLoadingState(submitBtn, true);
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('/api/process-csv', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Processing failed');
        }
        
        // Display results
        currentResults = data.results;
        displayCsvResults(data.results);
        
    } catch (error) {
        elements.csvError.textContent = 'Error processing CSV: ' + error.message;
    } finally {
        setLoadingState(submitBtn, false);
    }
}

// Display info-only results
function displayInfoResults(data) {
    elements.resultsSection.style.display = 'block';
    
    const html = `
        <div class="result-item">
            <h3>Extracted Information</h3>
            <div class="result-section">
                <h4>URL: ${data.url}</h4>
                <pre>${JSON.stringify(data.info || data.extracted_info, null, 2)}</pre>
                <button class="btn-copy" onclick="copyText(${JSON.stringify(JSON.stringify(data.info || data.extracted_info, null, 2))})">Copy</button>
            </div>
        </div>
    `;
    
    elements.resultsContainer.innerHTML = html;
}

// Display questions-only results
function displayQuestionsResults(data) {
    elements.resultsSection.style.display = 'block';
    
    const questions = data.questions || [];
    const html = `
        <div class="result-item">
            <h3>Extracted Questions (${questions.length})</h3>
            <div class="result-section">
                <h4>URL: ${data.url}</h4>
                <div class="questions-list">
                    ${questions.map((q, idx) => `
                        <div class="qa-item">
                            <div class="question"><strong>${idx + 1}. ${q.question || q}</strong></div>
                            ${q.type ? `<div class="question-type">Type: ${q.type}</div>` : ''}
                            ${q.required ? `<div class="question-required">Required: Yes</div>` : ''}
                        </div>
                    `).join('')}
                </div>
            </div>
        </div>
    `;
    
    elements.resultsContainer.innerHTML = html;
}

// Display single result
function displaySingleResult(result) {
    elements.resultsSection.style.display = 'block';
    
    const html = `
        <div class="result-item">
            <h3>${result.name || 'Application'}</h3>
            ${result.error ? `<div class="error">Error: ${result.error}</div>` : ''}
            ${result.errors ? `<div class="error">Errors: ${result.errors.join(', ')}</div>` : ''}
            
            ${result.info ? `
                <div class="result-section">
                    <h4>Extracted Information</h4>
                    <pre>${JSON.stringify(result.info, null, 2)}</pre>
                    <button class="btn-copy" onclick="copyText(${JSON.stringify(JSON.stringify(result.info, null, 2))})">Copy Info</button>
                </div>
            ` : ''}
            
            ${result.questions && result.questions.length > 0 ? `
                <div class="result-section">
                    <h4>Questions (${result.questions.length})</h4>
                    <div class="questions-list">
                        ${result.questions.map((q, idx) => `
                            <div class="qa-item">
                                <div class="question"><strong>${idx + 1}. ${q.question || q}</strong></div>
                                ${q.type ? `<div class="question-type">Type: ${q.type}</div>` : ''}
                            </div>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
            
            ${result.answers && result.answers.length > 0 ? `
                <div class="result-section">
                    <h4>Generated Answers</h4>
                    <div class="answers-list">
                        ${result.answers.map((qa, idx) => `
                            <div class="qa-item">
                                <div class="question"><strong>Q:</strong> ${qa.question}</div>
                                <div class="answer"><strong>A:</strong> ${qa.answer}</div>
                                ${qa.confidence ? `<div class="confidence">Confidence: ${qa.confidence}</div>` : ''}
                                <button class="btn-copy-small" onclick="copyQA(${JSON.stringify(qa)})">Copy</button>
                            </div>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
        </div>
    `;
    
    elements.resultsContainer.innerHTML = html;
}

// Display CSV results
function displayCsvResults(results) {
    elements.resultsSection.style.display = 'block';
    
    const html = results.map(result => `
        <div class="result-item">
            <h3>${result.name}</h3>
            ${result.error ? `<div class="error">Error: ${result.error}</div>` : ''}
            
            ${result.answers && result.answers.length > 0 ? `
                <div class="result-section">
                    <h4>Answers</h4>
                    <div class="answers-list">
                        ${result.answers.map(qa => `
                            <div class="qa-item">
                                <div class="question"><strong>Q:</strong> ${qa.question}</div>
                                <div class="answer"><strong>A:</strong> ${qa.answer}</div>
                                <button class="btn-copy-small" onclick="copyQA(${JSON.stringify(qa)})">Copy</button>
                            </div>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
        </div>
    `).join('<hr>');
    
    elements.resultsContainer.innerHTML = html;
}

// Copy functions
function copyText(text) {
    navigator.clipboard.writeText(text).then(() => {
        showCopyToast();
    }).catch(err => {
        console.error('Copy failed:', err);
        alert('Copy failed. Please try again.');
    });
}

function copyQA(qa) {
    const text = `Q: ${qa.question}\nA: ${qa.answer}`;
    copyText(text);
}

function copyAllResults() {
    if (!currentResults) return;
    
    let text = '';
    
    if (Array.isArray(currentResults)) {
        // CSV results
        currentResults.forEach(result => {
            text += `## ${result.name}\n\n`;
            if (result.answers) {
                result.answers.forEach(qa => {
                    text += `Q: ${qa.question}\nA: ${qa.answer}\n\n`;
                });
            }
            text += '---\n\n';
        });
    } else {
        // Single result
        text = `## ${currentResults.name || 'Application'}\n\n`;
        if (currentResults.answers) {
            currentResults.answers.forEach(qa => {
                text += `Q: ${qa.question}\nA: ${qa.answer}\n\n`;
            });
        }
    }
    
    copyText(text);
}

// Export functions
async function exportResults(format) {
    if (!currentResults) return;
    
    try {
        const response = await fetch(`/api/export/${format}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(currentResults)
        });
        
        if (!response.ok) {
            throw new Error('Export failed');
        }
        
        // Download the file
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = response.headers.get('content-disposition')?.split('filename=')[1]?.replace(/['"]/g, '') || `export.${format}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
    } catch (error) {
        showError('Export failed: ' + error.message);
    }
}

// Clear results
function clearResults() {
    currentResults = null;
    elements.resultsSection.style.display = 'none';
    elements.resultsContainer.innerHTML = '';
}

// Keyboard shortcuts
function handleKeyboardShortcuts(e) {
    // Ctrl/Cmd + Enter to submit
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        
        // Submit the active form
        const activeTab = document.querySelector('.tab-content.active');
        const form = activeTab.querySelector('form');
        if (form) {
            form.dispatchEvent(new Event('submit', { cancelable: true }));
        }
    }
    
    // Escape to clear results
    if (e.key === 'Escape') {
        e.preventDefault();
        clearResults();
    }
}

// Utility functions
function setLoadingState(button, isLoading) {
    const textSpan = button.querySelector('.btn-text');
    const loadingSpan = button.querySelector('.btn-loading');
    
    button.disabled = isLoading;
    if (textSpan && loadingSpan) {
        textSpan.style.display = isLoading ? 'none' : 'inline';
        loadingSpan.style.display = isLoading ? 'inline' : 'none';
    } else {
        button.textContent = isLoading ? 'Processing...' : button.dataset.originalText || 'Submit';
        if (!button.dataset.originalText) {
            button.dataset.originalText = button.textContent;
        }
    }
}

function showCopyToast() {
    elements.copyToast.classList.add('show');
    setTimeout(() => {
        elements.copyToast.classList.remove('show');
    }, 2000);
}

function showError(message) {
    alert(message); // Simple error display for MVP
}

// Make functions available globally for onclick handlers
window.copyText = copyText;
window.copyQA = copyQA;

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', init);