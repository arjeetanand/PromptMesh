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
// EVENTS
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

    document.getElementById("evalGenerateTests").addEventListener("change", e => {
        document.getElementById("manualTestsGroup").style.display =
            e.target.checked ? "none" : "block";
    });

    document.getElementById("evaluateForm").addEventListener("submit", handleEvaluate);
    document.getElementById("compareForm").addEventListener("submit", handleCompare);
    document.getElementById("evolveForm").addEventListener("submit", handleEvolve);
    document.getElementById("testcasesForm").addEventListener("submit", handleTestcase);

    document.getElementById("refreshBtn").addEventListener("click", () => location.reload());
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

async function handleEvaluate(e) {
    e.preventDefault();

    const payload = {
        task: evalTask.value,
        version: evalVersion.value,
        models: getChecked("evalModels"),
        generate_test_cases: evalGenerateTests.checked,
        test_case_count: Number(evalTestCount.value),
        test_inputs: evalGenerateTests.checked
            ? []
            : evalTestInputs.value.split("\n").filter(Boolean)
    };

    if (!payload.task || !payload.version || payload.models.length === 0) {
        return showToast("Missing required fields", "error");
    }

    const res = await apiCall("/evaluate", {
        method: "POST",
        body: JSON.stringify(payload)
    });

    startPolling(res.job_id, "evaluation");
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

async function handleEvolve(e) {
    e.preventDefault();

    const payload = {
        task: evolveTask.value,
        version: evolveVersion.value,
        model: evolveModel.value,
        optimizer_model: evolveOptimizer.value,
        max_iterations: Number(evolveIterations.value),
        test_case_count: Number(evolveTestCount.value)
    };

    if (!payload.task || !payload.version || !payload.model) {
        return showToast("Missing required fields", "error");
    }

    const res = await apiCall("/evolve", {
        method: "POST",
        body: JSON.stringify(payload)
    });

    startPolling(res.job_id, "evolution");
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

// ============================================================
// JOB POLLING
// ============================================================

function startPolling(jobId, type) {

    clearInterval(state.pollingTimer);

    showProgressModal(`Running ${type}...`);

    state.pollingTimer = setInterval(async () => {

        try {
            const job = await apiCall(`/jobs/${jobId}`);

            updateProgress(job.progress, job.status);

            if (job.status === "completed") {
                clearInterval(state.pollingTimer);
                hideProgressModal();
                handleJobResult(type, job.results);
                showToast("Job completed", "success");
            }

            if (job.status === "failed") {
                clearInterval(state.pollingTimer);
                hideProgressModal();
                showToast(job.error, "error");
            }

        } catch {
            clearInterval(state.pollingTimer);
            hideProgressModal();
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

function displayEvaluation(results) {
    evaluateResults.style.display = "block";
    evaluateResults.innerHTML = `<pre>${JSON.stringify(results, null, 2)}</pre>`;
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
