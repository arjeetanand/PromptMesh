// ============================================================
// CONFIG
// ============================================================

const API_BASE = window.location.origin;

// ============================================================
// STATE
// ============================================================

const state = {
    tasks: [],
    models: {},
    currentJob: null,
    jobHistory: [],
    activeTab: "evaluate",
    pollingTimer: null
};

// ============================================================
// INIT
// ============================================================

document.addEventListener("DOMContentLoaded", async () => {
    await checkAPIHealth();
    await loadInitialData();
    setupEventListeners();
    setupTabNavigation();
    loadJobHistory();
});

// ============================================================
// API CORE
// ============================================================

async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}/api${endpoint}`, {
            headers: {
                "Content-Type": "application/json",
                ...(options.headers || {})
            },
            ...options
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "API request failed");
        }

        return data;

    } catch (err) {
        console.error("API Error:", err);
        showToast(err.message, "error");
        throw err;
    }
}

// ============================================================
// HEALTH CHECK
// ============================================================

async function checkAPIHealth() {
    try {
        await apiCall("/health");
        updateAPIStatus(true);
    } catch {
        updateAPIStatus(false);
    }
}

function updateAPIStatus(isConnected) {
    const statusEl = document.getElementById("apiStatus");

    if (!statusEl) return;

    if (isConnected) {
        statusEl.innerHTML = `<span class="dot"></span> API Connected`;
        statusEl.querySelector(".dot").style.background = "var(--secondary)";
    } else {
        statusEl.innerHTML = `<span class="dot"></span> API Disconnected`;
        statusEl.querySelector(".dot").style.background = "var(--danger)";
    }
}

// ============================================================
// LOAD INITIAL DATA
// ============================================================

async function loadInitialData() {
    try {
        const tasksData = await apiCall("/tasks");
        const modelsData = await apiCall("/models");

        state.tasks = tasksData.tasks || [];
        state.models = modelsData || {};

        populateTaskDropdowns();
        populateModelSelectors();

    } catch {
        showToast("Failed to load initial data", "error");
    }
}

function populateTaskDropdowns() {
    ["evalTask", "compareTask", "evolveTask"].forEach(id => {
        const el = document.getElementById(id);
        el.innerHTML = `<option value="">Select task...</option>`;

        state.tasks.forEach(task => {
            const opt = document.createElement("option");
            opt.value = task;
            opt.textContent = task;
            el.appendChild(opt);
        });
    });
}

function populateModelSelectors() {

    // Evaluation + Comparison checkboxes
    ["evalModels", "compareModels"].forEach(containerId => {

        const container = document.getElementById(containerId);
        container.innerHTML = "";

        (state.models.all || []).forEach(model => {

            const label = document.createElement("label");
            const cb = document.createElement("input");

            cb.type = "checkbox";
            cb.value = model;

            if (containerId === "evalModels" &&
                (state.models.fast || []).includes(model)) {
                cb.checked = true;
            }

            label.appendChild(cb);
            label.append(model);

            container.appendChild(label);
        });
    });

    // Evolution model dropdown
    const evolveSelect = document.getElementById("evolveModel");
    evolveSelect.innerHTML = `<option value="">Select model...</option>`;

    (state.models.all || []).forEach(model => {
        const opt = document.createElement("option");
        opt.value = model;
        opt.textContent = model;
        evolveSelect.appendChild(opt);
    });
}

// ============================================================
// LOAD PROMPT VERSIONS
// ============================================================

async function loadVersionsForTask(task, targetId) {

    try {
        const data = await apiCall(`/tasks/${task}/versions`);
        const versions = data.versions || [];

        // Dropdown
        const select = document.getElementById(targetId);
        if (select && select.tagName === "SELECT") {

            select.innerHTML = `<option value="">Select version...</option>`;

            versions.forEach(v => {
                const opt = document.createElement("option");
                opt.value = v;
                opt.textContent = v;
                select.appendChild(opt);
            });
        }

        // Compare checkbox group
        if (targetId === "compareVersions") {

            const container = document.getElementById("compareVersions");
            container.innerHTML = "";

            versions.forEach(v => {
                const label = document.createElement("label");
                const cb = document.createElement("input");

                cb.type = "checkbox";
                cb.value = v;

                label.appendChild(cb);
                label.append(v);

                container.appendChild(label);
            });
        }

    } catch {
        showToast("Failed to load versions", "error");
    }
}

// ============================================================
// EVENT LISTENERS (UPDATED)
// ============================================================
// ============================================================
// EVENT LISTENERS (UPDATED)
// ============================================================
function setupEventListeners() {
    document.getElementById("evalTask").addEventListener("change", e => {
        if (e.target.value) {
            loadVersionsForTask(e.target.value, "evalVersion");
        }
    });

    document.getElementById("compareTask").addEventListener("change", e => {
        if (e.target.value) {
            loadVersionsForTask(e.target.value, "compareVersions");
        }
    });

    document.getElementById("evolveTask").addEventListener("change", e => {
        if (e.target.value) {
            loadVersionsForTask(e.target.value, "evolveVersion");
        }
    });

    // ✅ Custom prompt toggle for Evaluate
    document.getElementById("evalUseCustomPrompt").addEventListener("change", e => {
        const yamlSection = document.getElementById("evalYamlSection");
        const customSection = document.getElementById("evalCustomPromptSection");
        const autoGenOption = document.getElementById("evalAutoGenerateOption");
        const taskSelect = document.getElementById("evalTask");
        const versionSelect = document.getElementById("evalVersion");
        
        if (e.target.checked) {
            // Show custom prompt editor
            yamlSection.style.display = "none";
            customSection.style.display = "block";
            autoGenOption.style.display = "none"; // Hide auto-generation for custom
            taskSelect.required = false;
            versionSelect.required = false;
            
            // Clear and focus on test inputs
            document.getElementById("evalTestInputs").focus();
        } else {
            // Show YAML selection
            yamlSection.style.display = "block";
            customSection.style.display = "none";
            autoGenOption.style.display = "block";
            taskSelect.required = true;
            versionSelect.required = true;
        }
    });

    // ✅ Custom prompt toggle for Evolve
    document.getElementById("evolveUseCustomPrompt").addEventListener("change", e => {
        const yamlSection = document.getElementById("evolveYamlSection");
        const customSection = document.getElementById("evolveCustomPromptSection");
        const taskSelect = document.getElementById("evolveTask");
        const versionSelect = document.getElementById("evolveVersion");
        
        if (e.target.checked) {
            yamlSection.style.display = "none";
            customSection.style.display = "block";
            taskSelect.required = false;
            versionSelect.required = false;
            
            document.getElementById("evolveTestInputs").focus();
        } else {
            yamlSection.style.display = "block";
            customSection.style.display = "none";
            taskSelect.required = true;
            versionSelect.required = true;
        }
    });

    // ✅ Auto-generate test cases toggle
    document.getElementById("evalGenerateTests").addEventListener("change", e => {
        document.getElementById("evalGenerateCount").style.display = e.target.checked ? "block" : "none";
    });

    // ✅ Load prompt button (for editing existing)
    document.getElementById("evalVersion").addEventListener("change", e => {
        const useCustom = document.getElementById("evalUseCustomPrompt").checked;
        const task = document.getElementById("evalTask").value;
        if (useCustom && task && e.target.value) {
            loadPromptForEditing("eval", task, e.target.value);
        }
    });

    document.getElementById("evolveVersion").addEventListener("change", e => {
        const useCustom = document.getElementById("evolveUseCustomPrompt").checked;
        const task = document.getElementById("evolveTask").value;
        if (useCustom && task && e.target.value) {
            loadPromptForEditing("evolve", task, e.target.value);
        }
    });

    document.getElementById("evaluateForm").addEventListener("submit", handleEvaluate);
    document.getElementById("compareForm").addEventListener("submit", handleCompare);
    document.getElementById("evolveForm").addEventListener("submit", handleEvolve);
    document.getElementById("testcasesForm").addEventListener("submit", handleTestcase);
    document.getElementById("refreshBtn").addEventListener("click", () => location.reload());
}

// ✅ NEW: Load example prompt
function loadExamplePrompt(prefix) {
    const examplePrompt = `You are a sentiment classifier.

Classify the sentiment of the following text as Positive, Negative, or Neutral.

Text: {{text}}

Respond with ONLY one word: Positive, Negative, or Neutral.`;

    document.getElementById(`${prefix}CustomPrompt`).value = examplePrompt;
    showToast("Example prompt loaded", "success");
}

// ✅ NEW: Load example test inputs
function loadExampleTestInputs(prefix) {
    const exampleInputs = `This product is amazing! I love it and highly recommend it.
The service was terrible and the staff was rude.
The app works as expected, nothing special.
I'm extremely disappointed with this purchase.
Great value for money, very satisfied with my order.`;

    if (prefix === "eval") {
        document.getElementById("evalTestInputs").value = exampleInputs;
    } else if (prefix === "evolve") {
        document.getElementById("evolveTestInputs").value = exampleInputs;
    }
    
    showToast("Example test inputs loaded", "success");
}

// ============================================================
// TAB NAV
// ============================================================

function setupTabNavigation() {

    document.querySelectorAll(".nav-btn").forEach(btn => {

        btn.addEventListener("click", () => {

            const tab = btn.dataset.tab;

            document.querySelectorAll(".nav-btn")
                .forEach(b => b.classList.remove("active"));

            document.querySelectorAll(".tab-content")
                .forEach(c => c.classList.remove("active"));

            btn.classList.add("active");
            document.getElementById(`${tab}-tab`).classList.add("active");

            state.activeTab = tab;
        });
    });
}

// ============================================================
// FORM HANDLERS
// ============================================================

// ============================================================
// FORM HANDLERS (UPDATED)
// ============================================================
async function handleEvaluate(e) {
    e.preventDefault();

    const useCustom = document.getElementById("evalUseCustomPrompt").checked;
    
    // ✅ Get test inputs - ALWAYS from text area
    const testInputs = document.getElementById("evalTestInputs").value
        .split("\n")
        .map(line => line.trim())
        .filter(Boolean);

    if (testInputs.length === 0) {
        return showToast("Please provide at least one test input", "error");
    }

    const payload = {
        models: getChecked("evalModels"),
        test_inputs: testInputs,
        generate_test_cases: false  // We already have user inputs
    };

    // ✅ Handle custom vs YAML-based prompt
    if (useCustom) {
        const customPrompt = document.getElementById("evalCustomPrompt").value.trim();
        if (!customPrompt) {
            return showToast("Please enter a custom prompt", "error");
        }
        
        if (!customPrompt.includes("{{text}}")) {
            const confirm = window.confirm(
                "Your prompt doesn't contain {{text}} placeholder.\n\n" +
                "This means your test inputs won't be inserted into the prompt.\n\n" +
                "Continue anyway?"
            );
            if (!confirm) return;
        }
        
        payload.task = "custom";
        payload.version = "v1";
        payload.custom_prompt = customPrompt;
        payload.custom_constraints = {
            temperature: Number(document.getElementById("evalCustomTemp").value),
            max_tokens: Number(document.getElementById("evalCustomMaxTokens").value)
        };
    } else {
        payload.task = document.getElementById("evalTask").value;
        payload.version = document.getElementById("evalVersion").value;
        
        if (!payload.task || !payload.version) {
            return showToast("Please select task and version", "error");
        }

        // ✅ Check if auto-generate is enabled (only for YAML mode)
        const autoGenerate = document.getElementById("evalGenerateTests").checked;
        if (autoGenerate) {
            payload.generate_test_cases = true;
            payload.test_case_count = Number(document.getElementById("evalTestCount").value);
        }
    }

    if (payload.models.length === 0) {
        return showToast("Please select at least one model", "error");
    }

    try {
        const res = await apiCall("/evaluate", {
            method: "POST",
            body: JSON.stringify(payload)
        });
        startPolling(res.job_id, "evaluation");
    } catch (err) {
        showToast("Failed to start evaluation: " + err.message, "error");
    }
}

async function handleEvolve(e) {
    e.preventDefault();

    const useCustom = document.getElementById("evolveUseCustomPrompt").checked;

    // ✅ Get test inputs
    const testInputs = document.getElementById("evolveTestInputs").value
        .split("\n")
        .map(line => line.trim())
        .filter(Boolean);

    if (testInputs.length === 0) {
        return showToast("Please provide at least one test input for evolution", "error");
    }

    const payload = {
        model: document.getElementById("evolveModel").value,
        optimizer_model: document.getElementById("evolveOptimizer").value,
        max_iterations: Number(document.getElementById("evolveIterations").value),
        test_inputs: testInputs  // ✅ Pass user inputs
    };

    // ✅ Handle custom vs YAML-based prompt
    if (useCustom) {
        const customPrompt = document.getElementById("evolveCustomPrompt").value.trim();
        if (!customPrompt) {
            return showToast("Please enter a custom prompt", "error");
        }
        
        if (!customPrompt.includes("{{text}}")) {
            const confirm = window.confirm(
                "Your prompt doesn't contain {{text}} placeholder.\n\n" +
                "Continue anyway?"
            );
            if (!confirm) return;
        }
        
        payload.task = "custom";
        payload.version = "v1";
        payload.custom_prompt = customPrompt;
        payload.custom_constraints = {
            temperature: Number(document.getElementById("evolveCustomTemp").value),
            max_tokens: Number(document.getElementById("evolveCustomMaxTokens").value)
        };
    } else {
        payload.task = document.getElementById("evolveTask").value;
        payload.version = document.getElementById("evolveVersion").value;
        
        if (!payload.task || !payload.version) {
            return showToast("Please select task and version", "error");
        }
    }

    if (!payload.model) {
        return showToast("Please select execution model", "error");
    }

    try {
        const res = await apiCall("/evolve", {
            method: "POST",
            body: JSON.stringify(payload)
        });
        startPolling(res.job_id, "evolution");
    } catch (err) {
        showToast("Failed to start evolution: " + err.message, "error");
    }
}



async function handleCompare(e) {
    e.preventDefault();

    const payload = {
        task: compareTask.value,
        versions: getChecked("compareVersions"),
        models: getChecked("compareModels"),
        test_input: compareTestInput.value
    };

    if (!payload.task || payload.versions.length === 0 ||
        payload.models.length === 0 || !payload.test_input) {

        return showToast("Missing required fields", "error");
    }

    const res = await apiCall("/compare", {
        method: "POST",
        body: JSON.stringify(payload)
    });

    startPolling(res.job_id, "comparison");
}


async function handleTestcase(e) {
    e.preventDefault();

    const payload = {
        task_type: testcaseType.value,
        base_inputs: testcaseBase.value.split("\n").filter(Boolean),
        count: Number(testcaseCount.value)
    };

    const res = await apiCall("/test-cases/generate", {
        method: "POST",
        body: JSON.stringify(payload)
    });

    displayTestCases(res.test_cases);
}

// ✅ NEW: Export results function
function exportResults(type) {
    const resultsMap = {
        'evaluation': state.lastEvaluationResults,
        'comparison': state.lastComparisonResults,
        'evolution': state.lastEvolutionResults
    };
    
    const results = resultsMap[type];
    if (!results) {
        showToast("No results to export", "warning");
        return;
    }

    const dataStr = JSON.stringify(results, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `promptmesh-${type}-${new Date().toISOString()}.json`;
    link.click();
    URL.revokeObjectURL(url);
    
    showToast("Results exported successfully", "success");
}

// ============================================================
// JOB POLLING
// ============================================================


function startPolling(jobId, type) {
    clearInterval(state.pollingTimer);
    showProgressModal(`Running ${type}...`);

    let pollCount = 0;
    const MAX_POLLS = 60; // 2 minutes max

    state.pollingTimer = setInterval(async () => {
        try {
            pollCount++;
            
            // ✅ FIX: Timeout after max polls
            if (pollCount > MAX_POLLS) {
                clearInterval(state.pollingTimer);
                hideProgressModal();
                showToast("Job timed out. Please check backend logs.", "error");
                return;
            }

            const job = await apiCall(`/jobs/${jobId}`);
            updateProgress(job.progress, job.status);

            if (job.status === "completed") {
                clearInterval(state.pollingTimer);
                hideProgressModal();
                
                // ✅ FIX: Validate results exist
                if (!job.results || (Array.isArray(job.results) && job.results.length === 0)) {
                    showToast("Job completed but no results were generated", "warning");
                    return;
                }
                
                handleJobResult(type, job.results);
                addToHistory(jobId, type, job);
                showToast("Job completed successfully", "success");
            }

            if (job.status === "failed") {
                clearInterval(state.pollingTimer);
                hideProgressModal();
                showToast("Job failed: " + (job.error || "Unknown error"), "error");
            }
        } catch (err) {
            clearInterval(state.pollingTimer);
            hideProgressModal();
            showToast("Polling error: " + err.message, "error");
        }
    }, 2000);
}


// ============================================================
// RESULT ROUTER
// ============================================================

function handleJobResult(type, results) {

    if (type === "evaluation") displayEvaluation(results);
    if (type === "comparison") displayComparison(results);
    if (type === "evolution") displayEvolution(results);
}

// ============================================================
// HELPERS
// ============================================================

function getChecked(containerId) {
    return Array.from(document.querySelectorAll(`#${containerId} input:checked`))
        .map(cb => cb.value);
}

function escapeHTML(text) {
    const d = document.createElement("div");
    d.textContent = text;
    return d.innerHTML;
}

// ============================================================
// UI: MODAL + TOAST
// ============================================================

function showProgressModal(title) {
    progressModal.classList.add("active");
    progressTitle.textContent = title;
    progressFill.style.width = "0%";
    progressText.textContent = "Starting...";
}

function updateProgress(percent, text) {
    progressFill.style.width = `${percent}%`;
    progressText.textContent = text;
}

function hideProgressModal() {
    progressModal.classList.remove("active");
}

function showToast(msg, type = "info") {

    const el = document.createElement("div");
    el.className = `toast ${type}`;
    el.textContent = msg;

    toastContainer.appendChild(el);

    setTimeout(() => el.remove(), 4000);
}

// ============================================================
// RESULTS UI (Minimal Stable Rendering)
// ============================================================

// function displayEvaluation(results) {
//     evaluateResults.style.display = "block";
//     evaluateResults.innerHTML = `<pre>${JSON.stringify(results, null, 2)}</pre>`;
// }

function displayEvaluation(results) {
    const resultsEl = document.getElementById("evaluateResults");
    resultsEl.style.display = "block";

    // ✅ FIX: Handle empty results
    if (!results || results.length === 0) {
        resultsEl.innerHTML = `<div class="empty-state"><span class="icon">⚠️</span><p>No evaluation results available</p></div>`;
        return;
    }

    // Stats summary
    const statsEl = document.getElementById("evaluationStats");
    const bestModel = results[0];
    const avgScore = (results.reduce((sum, m) => sum + m.average_score, 0) / results.length).toFixed(2);

    statsEl.innerHTML = `
        <div class="stat-box">
            <div class="stat-label">Best Model</div>
            <div class="stat-value">${bestModel.model}</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">Best Score</div>
            <div class="stat-value">${bestModel.average_score}</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">Average Score</div>
            <div class="stat-value">${avgScore}</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">Models Evaluated</div>
            <div class="stat-value">${results.length}</div>
        </div>
    `;

    evaluateResults.style.display = "block";
    evaluateResults.innerHTML = `<pre>${JSON.stringify(results, null, 2)}</pre>`;
    // ... rest of the function
}


function displayComparison(results) {
    compareResults.style.display = "block";
    compareResults.innerHTML = `<pre>${JSON.stringify(results, null, 2)}</pre>`;
}

function displayEvolution(results) {
    evolveResults.style.display = "block";
    evolveResults.innerHTML = `<pre>${JSON.stringify(results, null, 2)}</pre>`;
}

function displayTestCases(data) {
    testcasesResults.style.display = "block";
    testcasesResults.innerHTML = data.map(t => `<div>${escapeHTML(t)}</div>`).join("");
}

// ============================================================
// HISTORY
// ============================================================

function loadJobHistory() {
    const saved = localStorage.getItem("jobHistory");
    if (saved) {
        state.jobHistory = JSON.parse(saved);
    }
}
