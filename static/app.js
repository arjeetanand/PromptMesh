// ============================================================
// STATE MANAGEMENT
// ============================================================

const state = {
    tasks: [],
    models: {},
    currentJob: null,
    jobHistory: [],
    activeTab: 'evaluate'
};

// ============================================================
// INITIALIZATION
// ============================================================

document.addEventListener('DOMContentLoaded', async () => {
    await checkAPIHealth();
    await loadInitialData();
    setupEventListeners();
    setupTabNavigation();
    loadJobHistory();
});

// ============================================================
// API FUNCTIONS
// ============================================================

async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(`/api${endpoint}`, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'API request failed');
        }

        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        showToast(error.message, 'error');
        throw error;
    }
}

async function checkAPIHealth() {
    try {
        await apiCall('/health');
        updateAPIStatus(true);
    } catch {
        updateAPIStatus(false);
    }
}

function updateAPIStatus(connected) {
    const statusEl = document.getElementById('apiStatus');
    const dot = statusEl.querySelector('.dot');
    
    if (connected) {
        statusEl.innerHTML = '<span class="dot"></span> API Connected';
        dot.style.background = 'var(--secondary)';
    } else {
        statusEl.innerHTML = '<span class="dot"></span> API Disconnected';
        dot.style.background = 'var(--danger)';
    }
}

// ============================================================
// DATA LOADING
// ============================================================

async function loadInitialData() {
    try {
        // Load tasks
        const tasksData = await apiCall('/tasks');
        state.tasks = tasksData.tasks;

        // Load models
        const modelsData = await apiCall('/models');
        state.models = modelsData;

        // Populate dropdowns
        populateTaskDropdowns();
        populateModelCheckboxes();
    } catch (error) {
        showToast('Failed to load initial data', 'error');
    }
}

function populateTaskDropdowns() {
    const taskSelects = ['evalTask', 'compareTask', 'evolveTask'];
    
    taskSelects.forEach(id => {
        const select = document.getElementById(id);
        select.innerHTML = '<option value="">Select a task...</option>';
        
        state.tasks.forEach(task => {
            const option = document.createElement('option');
            option.value = task;
            option.textContent = task.charAt(0).toUpperCase() + task.slice(1);
            select.appendChild(option);
        });
    });
}

function populateModelCheckboxes() {
    const modelGroups = ['evalModels', 'compareModels'];
    
    modelGroups.forEach(groupId => {
        const container = document.getElementById(groupId);
        container.innerHTML = '';
        
        state.models.all.forEach(model => {
            const label = document.createElement('label');
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.value = model;
            checkbox.name = 'model';
            
            // Check fast models by default for eval
            if (groupId === 'evalModels' && state.models.fast.includes(model)) {
                checkbox.checked = true;
            }
            
            label.appendChild(checkbox);
            label.appendChild(document.createTextNode(model));
            container.appendChild(label);
        });
    });

    // Populate evolution model dropdown
    const evolveModelSelect = document.getElementById('evolveModel');
    evolveModelSelect.innerHTML = '<option value="">Select model...</option>';
    state.models.all.forEach(model => {
        const option = document.createElement('option');
        option.value = model;
        option.textContent = model;
        evolveModelSelect.appendChild(option);
    });
}

async function loadVersionsForTask(task, targetSelectId) {
    try {
        const data = await apiCall(`/tasks/${task}/versions`);
        const select = document.getElementById(targetSelectId);
        select.innerHTML = '<option value="">Select version...</option>';
        
        data.versions.forEach(version => {
            const option = document.createElement('option');
            option.value = version;
            option.textContent = version;
            select.appendChild(option);
        });

        // For compare tab, also populate checkboxes
        if (targetSelectId === 'compareTask') {
            const container = document.getElementById('compareVersions');
            container.innerHTML = '';
            
            data.versions.forEach(version => {
                const label = document.createElement('label');
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.value = version;
                checkbox.name = 'version';
                
                label.appendChild(checkbox);
                label.appendChild(document.createTextNode(version));
                container.appendChild(label);
            });
        }
    } catch (error) {
        showToast('Failed to load versions', 'error');
    }
}

// ============================================================
// EVENT LISTENERS
// ============================================================

function setupEventListeners() {
    // Task selection change handlers
    document.getElementById('evalTask').addEventListener('change', (e) => {
        if (e.target.value) loadVersionsForTask(e.target.value, 'evalVersion');
    });

    document.getElementById('compareTask').addEventListener('change', (e) => {
        if (e.target.value) loadVersionsForTask(e.target.value, 'compareTask');
    });

    document.getElementById('evolveTask').addEventListener('change', (e) => {
        if (e.target.value) loadVersionsForTask(e.target.value, 'evolveVersion');
    });

    // Auto-generate test cases toggle
    document.getElementById('evalGenerateTests').addEventListener('change', (e) => {
        document.getElementById('manualTestsGroup').style.display = 
            e.target.checked ? 'none' : 'block';
    });

    // Form submissions
    document.getElementById('evaluateForm').addEventListener('submit', handleEvaluateSubmit);
    document.getElementById('compareForm').addEventListener('submit', handleCompareSubmit);
    document.getElementById('evolveForm').addEventListener('submit', handleEvolveSubmit);
    document.getElementById('testcasesForm').addEventListener('submit', handleTestCasesSubmit);

    // Refresh button
    document.getElementById('refreshBtn').addEventListener('click', () => {
        location.reload();
    });
}

function setupTabNavigation() {
    const navBtns = document.querySelectorAll('.nav-btn');
    
    navBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;
            
            // Update active states
            navBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // Show correct content
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            document.getElementById(`${tab}-tab`).classList.add('active');
            
            state.activeTab = tab;
        });
    });
}

// ============================================================
// FORM HANDLERS
// ============================================================

async function handleEvaluateSubmit(e) {
    e.preventDefault();
    
    const task = document.getElementById('evalTask').value;
    const version = document.getElementById('evalVersion').value;
    const models = getCheckedValues('evalModels input[name="model"]');
    const generateTests = document.getElementById('evalGenerateTests').checked;
    const testCount = parseInt(document.getElementById('evalTestCount').value);
    
    if (!task || !version || models.length === 0) {
        showToast('Please fill all required fields', 'error');
        return;
    }

    const testInputs = generateTests ? [] : 
        document.getElementById('evalTestInputs').value.split('\n').filter(s => s.trim());

    try {
        const response = await apiCall('/evaluate', {
            method: 'POST',
            body: JSON.stringify({
                task,
                version,
                models,
                test_inputs: testInputs,
                generate_test_cases: generateTests,
                test_case_count: testCount
            })
        });

        startJobPolling(response.job_id, 'evaluation');
        addToHistory('Evaluation', { task, version, models });
    } catch (error) {
        // Error already shown by apiCall
    }
}

async function handleCompareSubmit(e) {
    e.preventDefault();
    
    const task = document.getElementById('compareTask').value;
    const versions = getCheckedValues('compareVersions input[name="version"]');
    const models = getCheckedValues('compareModels input[name="model"]');
    const testInput = document.getElementById('compareTestInput').value;
    
    if (!task || versions.length === 0 || models.length === 0 || !testInput) {
        showToast('Please fill all required fields', 'error');
        return;
    }

    try {
        const response = await apiCall('/compare', {
            method: 'POST',
            body: JSON.stringify({
                task,
                versions,
                models,
                test_input: testInput
            })
        });

        startJobPolling(response.job_id, 'comparison');
        addToHistory('Comparison', { task, versions, models });
    } catch (error) {
        // Error already shown by apiCall
    }
}

async function handleEvolveSubmit(e) {
    e.preventDefault();
    
    const task = document.getElementById('evolveTask').value;
    const version = document.getElementById('evolveVersion').value;
    const model = document.getElementById('evolveModel').value;
    const optimizer = document.getElementById('evolveOptimizer').value;
    const iterations = parseInt(document.getElementById('evolveIterations').value);
    const testCount = parseInt(document.getElementById('evolveTestCount').value);
    
    if (!task || !version || !model) {
        showToast('Please fill all required fields', 'error');
        return;
    }

    try {
        const response = await apiCall('/evolve', {
            method: 'POST',
            body: JSON.stringify({
                task,
                version,
                model,
                optimizer_model: optimizer,
                max_iterations: iterations,
                test_case_count: testCount
            })
        });

        startJobPolling(response.job_id, 'evolution');
        addToHistory('Evolution', { task, version, model });
    } catch (error) {
        // Error already shown by apiCall
    }
}

async function handleTestCasesSubmit(e) {
    e.preventDefault();
    
    const taskType = document.getElementById('testcaseType').value;
    const baseInputs = document.getElementById('testcaseBase').value
        .split('\n').filter(s => s.trim());
    const count = parseInt(document.getElementById('testcaseCount').value);
    
    try {
        showToast('Generating test cases...', 'info');
        
        const response = await apiCall('/test-cases/generate', {
            method: 'POST',
            body: JSON.stringify({
                task_type: taskType,
                base_inputs: baseInputs,
                count
            })
        });

        displayTestCaseResults(response.test_cases);
        showToast('Test cases generated successfully', 'success');
    } catch (error) {
        // Error already shown by apiCall
    }
}

// ============================================================
// JOB POLLING
// ============================================================

async function startJobPolling(jobId, type) {
    state.currentJob = { id: jobId, type };
    
    showProgressModal(`Running ${type}...`);
    
    const pollInterval = setInterval(async () => {
        try {
            const status = await apiCall(`/jobs/${jobId}`);
            
            updateProgress(status.progress, status.status);
            
            if (status.status === 'completed') {
                clearInterval(pollInterval);
                hideProgressModal();
                handleJobComplete(type, status.results);
                showToast(`${type} completed successfully`, 'success');
            } else if (status.status === 'failed') {
                clearInterval(pollInterval);
                hideProgressModal();
                showToast(`${type} failed: ${status.error}`, 'error');
            }
        } catch (error) {
            clearInterval(pollInterval);
            hideProgressModal();
        }
    }, 2000);
}

function handleJobComplete(type, results) {
    switch(type) {
        case 'evaluation':
            displayEvaluationResults(results);
            break;
        case 'comparison':
            displayComparisonResults(results);
            break;
        case 'evolution':
            displayEvolutionResults(results);
            break;
    }
}

// ============================================================
// RESULTS DISPLAY
// ============================================================

function displayEvaluationResults(results) {
    const container = document.getElementById('evaluateResults');
    container.style.display = 'block';
    
    let html = '<div class="results-header"><h3>Evaluation Results</h3></div>';
    
    results.forEach((modelResult, index) => {
        const isWinner = index === 0;
        
        html += `
            <div class="model-card ${isWinner ? 'winner' : ''}">
                <div class="model-header">
                    <span class="model-name">
                        ${isWinner ? '🏆 ' : ''}${modelResult.model}
                    </span>
                    <span class="score-badge">${modelResult.average_score.toFixed(2)}</span>
                </div>
                
                ${modelResult.results.map(r => `
                    <div class="test-result">
                        <div class="test-input">
                            <div class="test-label">Input</div>
                            <div class="test-text">${escapeHtml(r.input)}</div>
                        </div>
                        <div class="test-output">
                            <div class="test-label">Output</div>
                            <div class="test-text">${escapeHtml(r.output)}</div>
                        </div>
                        <div class="breakdown-grid">
                            <div class="breakdown-item">
                                <div class="breakdown-label">Score</div>
                                <div class="breakdown-value">${r.score.toFixed(1)}</div>
                            </div>
                            <div class="breakdown-item">
                                <div class="breakdown-label">Accuracy</div>
                                <div class="breakdown-value">${r.breakdown.accuracy}</div>
                            </div>
                            <div class="breakdown-item">
                                <div class="breakdown-label">Complete</div>
                                <div class="breakdown-value">${r.breakdown.completeness}</div>
                            </div>
                            <div class="breakdown-item">
                                <div class="breakdown-label">Adherence</div>
                                <div class="breakdown-value">${r.breakdown.adherence}</div>
                            </div>
                            <div class="breakdown-item">
                                <div class="breakdown-label">Hallucination</div>
                                <div class="breakdown-value">${r.breakdown.hallucination}</div>
                            </div>
                        </div>
                        <div class="test-metrics">
                            <span>⚡ ${r.latency_ms}ms</span>
                            <span>🎯 ${r.tokens} tokens</span>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    });
    
    container.innerHTML = html;
}

function displayComparisonResults(results) {
    const container = document.getElementById('compareResults');
    container.style.display = 'block';
    
    // Group by version
    const byVersion = {};
    results.forEach(r => {
        if (!byVersion[r.prompt_version]) {
            byVersion[r.prompt_version] = [];
        }
        byVersion[r.prompt_version].push(r);
    });
    
    let html = '<div class="results-header"><h3>Comparison Results</h3></div>';
    
    Object.entries(byVersion).forEach(([version, versionResults]) => {
        const avgScore = versionResults.reduce((sum, r) => sum + r.score, 0) / versionResults.length;
        
        html += `
            <div class="model-card">
                <div class="model-header">
                    <span class="model-name">Version: ${version}</span>
                    <span class="score-badge">${avgScore.toFixed(2)}</span>
                </div>
                ${versionResults.map(r => `
                    <div class="test-result">
                        <div class="test-label">Model: ${r.model}</div>
                        <div class="test-output">
                            <div class="test-text">${escapeHtml(r.output)}</div>
                        </div>
                        <div class="breakdown-grid">
                            <div class="breakdown-item">
                                <div class="breakdown-label">Accuracy</div>
                                <div class="breakdown-value">${r.breakdown.accuracy}</div>
                            </div>
                            <div class="breakdown-item">
                                <div class="breakdown-label">Complete</div>
                                <div class="breakdown-value">${r.breakdown.completeness}</div>
                            </div>
                            <div class="breakdown-item">
                                <div class="breakdown-label">Adherence</div>
                                <div class="breakdown-value">${r.breakdown.adherence}</div>
                            </div>
                            <div class="breakdown-item">
                                <div class="breakdown-label">Hallucination</div>
                                <div class="breakdown-value">${r.breakdown.hallucination}</div>
                            </div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    });
    
    container.innerHTML = html;
}

function displayEvolutionResults(results) {
    const container = document.getElementById('evolveResults');
    container.style.display = 'block';
    
    let html = `
        <div class="results-header">
            <h3>Evolution Results</h3>
        </div>
        <div class="breakdown-grid" style="margin-bottom: 24px;">
            <div class="breakdown-item">
                <div class="breakdown-label">Initial Score</div>
                <div class="breakdown-value">${results.initial_score.toFixed(2)}</div>
            </div>
            <div class="breakdown-item">
                <div class="breakdown-label">Final Score</div>
                <div class="breakdown-value">${results.final_score.toFixed(2)}</div>
            </div>
            <div class="breakdown-item">
                <div class="breakdown-label">Improvement</div>
                <div class="breakdown-value" style="color: var(--secondary);">
                    +${results.improvement.toFixed(2)}
                </div>
            </div>
        </div>
        <div class="evolution-timeline">
    `;
    
    results.history.forEach((step, index) => {
        const isFinal = index === results.history.length - 1;
        html += `
            <div class="evolution-step ${isFinal ? 'final' : ''}">
                <div class="step-header">
                    <span class="step-title">
                        ${index === 0 ? 'Initial' : `Iteration ${index}`}
                        ${isFinal ? ' (Final)' : ''}
                    </span>
                    <span class="step-score">${step.score.toFixed(2)}</span>
                </div>
                <div class="prompt-diff">${escapeHtml(step.prompt)}</div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

function displayTestCaseResults(testCases) {
    const container = document.getElementById('testcasesResults');
    container.style.display = 'block';
    
    let html = `
        <div class="results-header">
            <h3>Generated Test Cases (${testCases.length})</h3>
        </div>
    `;
    
    testCases.forEach((testCase, index) => {
        html += `
            <div class="test-result">
                <div class="test-label">Test Case ${index + 1}</div>
                <div class="test-text">${escapeHtml(testCase)}</div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// ============================================================
// PROGRESS MODAL
// ============================================================

function showProgressModal(title) {
    const modal = document.getElementById('progressModal');
    document.getElementById('progressTitle').textContent = title;
    document.getElementById('progressText').textContent = 'Initializing...';
    document.getElementById('progressFill').style.width = '0%';
    modal.classList.add('active');
}

function updateProgress(progress, status) {
    document.getElementById('progressFill').style.width = `${progress}%`;
    document.getElementById('progressText').textContent = status;
}

function hideProgressModal() {
    document.getElementById('progressModal').classList.remove('active');
}

// ============================================================
// TOAST NOTIFICATIONS
// ============================================================

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icons = {
        success: '✓',
        error: '✗',
        info: 'ℹ'
    };
    
    toast.innerHTML = `
        <span class="toast-icon">${icons[type]}</span>
        <span class="toast-message">${message}</span>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s reverse';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ============================================================
// HISTORY
// ============================================================

function addToHistory(type, details) {
    const historyItem = {
        id: Date.now(),
        type,
        details,
        timestamp: new Date().toISOString()
    };
    
    state.jobHistory.unshift(historyItem);
    localStorage.setItem('jobHistory', JSON.stringify(state.jobHistory));
    updateHistoryDisplay();
}

function loadJobHistory() {
    const saved = localStorage.getItem('jobHistory');
    if (saved) {
        state.jobHistory = JSON.parse(saved);
        updateHistoryDisplay();
    }
}

function updateHistoryDisplay() {
    const container = document.getElementById('historyList');
    
    if (state.jobHistory.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <span class="icon">📋</span>
                <p>No jobs in history yet</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    state.jobHistory.forEach(item => {
        const date = new Date(item.timestamp);
        const timeStr = date.toLocaleString();
        
        html += `
            <div class="history-item">
                <div class="history-header">
                    <span class="history-type">${item.type}</span>
                    <span class="history-time">${timeStr}</span>
                </div>
                <div class="history-details">
                    ${JSON.stringify(item.details)}
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// ============================================================
// UTILITY FUNCTIONS
// ============================================================

function getCheckedValues(selector) {
    return Array.from(document.querySelectorAll(selector))
        .filter(cb => cb.checked)
        .map(cb => cb.value);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}