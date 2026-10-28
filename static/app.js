const API_BASE = window.location.origin;
const HISTORY_KEY = "promptmesh.run-summaries.v1";
const state = {
  tasks: [],
  models: {},
  trainingDatasets: [],
  trainingRuntime: null,
  trainedAdapters: [],
  activeAdapterModel: null,
  activeTab: "overview",
  pollingTimer: null,
  jobBusy: false,
  apiKey: null,
  jobHistory: [],
  lastEvaluationResults: null,
  lastComparisonResults: null,
  lastEvolutionResults: null
};

const $ = (id) => document.getElementById(id);

window.addEventListener("DOMContentLoaded", initialize);

async function initialize() {
  loadJobHistory();
  setupNavigation();
  setupForms();
  setupPromptModes();
  setupMobileNavigation();
  renderHistory();
  renderOverviewHistory();
  await checkAPIHealth();
}

async function apiCall(endpoint, options = {}) {
  const path = String(endpoint).replace(/^\/+/, "");
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (state.apiKey) headers.Authorization = "Bearer " + state.apiKey;
  const response = await fetch(API_BASE + "/api/" + path, { ...options, headers });
  let data = {};
  try { data = await response.json(); } catch { data = {}; }
  if (!response.ok) throw new Error(data.detail || "The API request failed (" + response.status + ").");
  return data;
}

async function checkAPIHealth() {
  updateAPIStatus("checking", "Checking API");
  try {
    await apiCall("health");
    const session = await apiCall("session");
    if (session.auth_required && !session.authenticated) {
      $("apiAuth").hidden = false;
      updateAPIStatus("locked", "API key required");
      setOverviewStatus("Authentication required", "Enter the server API key to load tasks and models.");
      return;
    }
    $("apiAuth").hidden = true;
    updateAPIStatus("connected", "API connected");
    await loadInitialData();
  } catch (error) {
    updateAPIStatus("offline", "API unavailable");
    setOverviewStatus("API unavailable", "Start the local API, then refresh this connection.");
    setEmptySelectors("The API is offline. Start PromptMesh to load tasks and models.");
  }
}

function updateAPIStatus(kind, label) {
  const node = $("apiStatus");
  node.className = "api-status is-" + kind;
  node.replaceChildren();
  const dot = document.createElement("span");
  dot.className = "status-dot";
  dot.setAttribute("aria-hidden", "true");
  const text = document.createElement("span");
  text.textContent = label;
  node.append(dot, text);
  $("overviewApiState").textContent = label;
}

function setOverviewStatus(title, note) {
  $("overviewApiState").textContent = title;
  $("overviewStatusNote").textContent = note;
  $("overviewTaskCount").textContent = "—";
  $("overviewModelCount").textContent = "—";
}

function setEmptySelectors(message) {
  ["evalModels", "compareModels"].forEach((id) => {
    const container = $(id);
    container.replaceChildren();
    const note = document.createElement("p");
    note.className = "empty-options";
    note.textContent = message;
    container.append(note);
  });
}

async function loadInitialData() {
  const [tasksResult, modelsResult, trainingResult] = await Promise.allSettled([
    apiCall("tasks"), apiCall("models"), apiCall("training/datasets")
  ]);
  if (tasksResult.status === "fulfilled") state.tasks = tasksResult.value.tasks || [];
  if (modelsResult.status === "fulfilled") state.models = modelsResult.value || {};
  if (trainingResult.status === "fulfilled") {
    state.trainingDatasets = trainingResult.value.datasets || [];
    state.trainingRuntime = trainingResult.value.runtime || null;
  } else {
    state.trainingDatasets = [];
    state.trainingRuntime = null;
  }
  populateTaskDropdowns();
  populateModelSelectors();
  populateTrainingDatasets();
  await loadSavedAdapters();
  $("overviewTaskCount").textContent = String(state.tasks.length);
  $("overviewModelCount").textContent = String((state.models.all || []).length);
  const unavailable = [tasksResult, modelsResult].some((result) => result.status === "rejected");
  $("overviewStatusNote").textContent = unavailable
    ? "The API responded, but one registry could not be loaded. Refresh to retry."
    : state.tasks.length + " tasks and " + (state.models.all || []).length + " registered models are available.";
  if (unavailable) showToast("Some workspace data could not be loaded.", "warning");
}

function populateTaskDropdowns() {
  ["evalTask", "compareTask", "evolveTask"].forEach((id) => {
    const select = $(id);
    const prior = select.value;
    select.replaceChildren(new Option(state.tasks.length ? "Select a task" : "No tasks available", ""));
    state.tasks.forEach((task) => select.add(new Option(task, task)));
    if (state.tasks.includes(prior)) select.value = prior;
  });
}

function populateModelSelectors() {
  ["evalModels", "compareModels"].forEach((id) => {
    const container = $(id);
    const prior = new Set(Array.from(container.querySelectorAll("input:checked"), (input) => input.value));
    container.replaceChildren();
    const models = state.models.all || [];
    if (!models.length) {
      const note = document.createElement("p");
      note.className = "empty-options";
      note.textContent = "No models are registered. Add a model in models/registry.py.";
      container.append(note);
      return;
    }
    models.forEach((model) => {
      const label = document.createElement("label");
      const input = document.createElement("input");
      input.type = "checkbox";
      input.value = model;
      input.checked = prior.has(model) || (id === "evalModels" && !prior.size && (state.models.fast || []).includes(model));
      const name = document.createElement("span");
      name.className = "model-name";
      name.textContent = model;
      label.append(input, name);
      container.append(label);
    });
  });
  const select = $("evolveModel");
  const prior = select.value;
  select.replaceChildren(new Option("Select a model", ""));
  (state.models.all || []).forEach((model) => select.add(new Option(model, model)));
  if ((state.models.all || []).includes(prior)) select.value = prior;
}

async function loadVersionsForTask(task, targetId) {
  const select = targetId === "compareVersions" ? null : $(targetId);
  const container = targetId === "compareVersions" ? $(targetId) : null;
  if (select) select.replaceChildren(new Option("Loading versions…", ""));
  if (container) container.replaceChildren();
  try {
    const result = await apiCall("tasks/" + encodeURIComponent(task) + "/versions");
    const versions = result.versions || [];
    if (select) {
      select.replaceChildren(new Option(versions.length ? "Select a version" : "No versions available", ""));
      versions.forEach((version) => select.add(new Option(version, version)));
    }
    if (container) {
      if (!versions.length) {
        const note = document.createElement("p");
        note.className = "empty-options";
        note.textContent = "This task has no saved prompt versions yet.";
        container.append(note);
      }
      versions.forEach((version) => {
        const label = document.createElement("label");
        label.className = "version-option";
        const input = document.createElement("input");
        input.type = "checkbox";
        input.value = version;
        input.addEventListener("change", () => {
          if (container.querySelectorAll("input:checked").length > 2) {
            input.checked = false;
            showToast("Choose exactly two versions.", "warning");
          }
          updateVersionCount();
        });
        const text = document.createElement("span");
        text.textContent = version;
        label.append(input, text);
        container.append(label);
      });
      updateVersionCount();
    }
  } catch (error) {
    if (select) select.replaceChildren(new Option("Versions could not be loaded", ""));
    if (container) {
      const note = document.createElement("p");
      note.className = "empty-options";
      note.textContent = "Versions could not be loaded. Refresh the API connection and try again.";
      container.append(note);
    }
    showToast("Could not load prompt versions: " + error.message, "error");
  }
}

function setupNavigation() {
  document.querySelectorAll(".nav-btn[data-tab]").forEach((button) => {
    button.addEventListener("click", () => activateTab(button.dataset.tab, true));
  });
  document.querySelectorAll("[data-go]").forEach((button) => {
    button.addEventListener("click", () => activateTab(button.dataset.go, true));
  });
  window.addEventListener("hashchange", () => {
    const tab = window.location.hash.slice(1);
    activateTab(validTab(tab) ? tab : "overview", false);
  });
  const initial = window.location.hash.slice(1);
  activateTab(validTab(initial) ? initial : "overview", false);
}

function validTab(tab) { return ["overview", "evaluate", "compare", "evolve", "finetune", "testcases", "history"].includes(tab); }

function activateTab(tab, updateHash) {
  if (!validTab(tab)) tab = "overview";
  state.activeTab = tab;
  document.querySelectorAll(".tab-content").forEach((section) => {
    section.hidden = section.id !== tab + "-tab";
  });
  document.querySelectorAll(".nav-btn[data-tab]").forEach((button) => {
    const active = button.dataset.tab === tab;
    button.classList.toggle("active", active);
    if (active) button.setAttribute("aria-current", "page");
    else button.removeAttribute("aria-current");
  });
  const activeButton = document.querySelector('.nav-btn[data-tab="' + tab + '"]');
  $("breadcrumbTitle").textContent = activeButton ? activeButton.textContent.trim() : "Overview";
  closeMobileNavigation();
  if (updateHash && window.location.hash !== "#" + tab) window.history.replaceState(null, "", "#" + tab);
}

function setupMobileNavigation() {
  const frame = $("appFrame");
  const toggle = $("menuToggle");
  const scrim = $("mobileScrim");
  toggle.addEventListener("click", () => {
    const open = !frame.classList.contains("nav-open");
    frame.classList.toggle("nav-open", open);
    toggle.setAttribute("aria-expanded", String(open));
    toggle.setAttribute("aria-label", open ? "Close navigation" : "Open navigation");
    scrim.hidden = !open;
  });
  scrim.addEventListener("click", closeMobileNavigation);
  document.addEventListener("keydown", (event) => { if (event.key === "Escape") closeMobileNavigation(); });
}

function closeMobileNavigation() {
  $("appFrame").classList.remove("nav-open");
  $("menuToggle").setAttribute("aria-expanded", "false");
  $("menuToggle").setAttribute("aria-label", "Open navigation");
  $("mobileScrim").hidden = true;
}

function setupPromptModes() {
  $("evalUseCustomPrompt").addEventListener("change", (event) => {
    const custom = event.target.checked;
    $("evalYamlSection").hidden = custom;
    $("evalCustomPromptSection").hidden = !custom;
    $("evalTask").required = !custom;
    $("evalVersion").required = !custom;
    $("evalAutoGenerateOption").hidden = custom;
  });
  $("compareUseCustom").addEventListener("change", (event) => {
    const custom = event.target.checked;
    $("compareYamlSection").hidden = custom;
    $("compareCustomSection").hidden = !custom;
    $("compareTask").required = !custom;
  });
  $("evolveUseCustomPrompt").addEventListener("change", (event) => {
    const custom = event.target.checked;
    $("evolveYamlSection").hidden = custom;
    $("evolveCustomPromptSection").hidden = !custom;
    $("evolveTask").required = !custom;
    $("evolveVersion").required = !custom;
  });
  $("evalGenerateTests").addEventListener("change", (event) => { $("evalGenerateCount").hidden = !event.target.checked; });
}

function setupForms() {
  $("evalTask").addEventListener("change", (event) => { if (event.target.value) loadVersionsForTask(event.target.value, "evalVersion"); });
  $("compareTask").addEventListener("change", (event) => { if (event.target.value) loadVersionsForTask(event.target.value, "compareVersions"); });
  $("evolveTask").addEventListener("change", (event) => { if (event.target.value) loadVersionsForTask(event.target.value, "evolveVersion"); });
  $("evaluateForm").addEventListener("submit", handleEvaluate);
  $("compareForm").addEventListener("submit", handleCompare);
  $("evolveForm").addEventListener("submit", handleEvolve);
  $("testcasesForm").addEventListener("submit", handleTestcase);
  $("fineTuneForm").addEventListener("submit", handleFineTune);
  $("fineTuneDataset").addEventListener("change", updateFineTuneDatasetNote);
  $("evaluateAdapterBtn").addEventListener("click", () => useAdapterInEvaluation(state.activeAdapterModel));
  $("savedAdapterList").addEventListener("click", (event) => {
    const button = event.target.closest("[data-model]");
    if (button) useAdapterInEvaluation(button.dataset.model);
  });
  $("connectApiBtn").addEventListener("click", connectAPI);
  $("refreshBtn").addEventListener("click", checkAPIHealth);
  $("clearHistoryBtn").addEventListener("click", clearHistory);
  $("progressModal").addEventListener("cancel", (event) => event.preventDefault());
}

function populateTrainingDatasets() {
  const select = $("fineTuneDataset");
  const prior = select.value;
  select.replaceChildren(new Option("Select a local dataset", ""));
  state.trainingDatasets.forEach((dataset) => {
    const label = dataset.error
      ? dataset.id + " · invalid"
      : dataset.id + (dataset.synthetic ? " · synthetic demo" : "") + " · " + dataset.examples + " examples";
    const option = new Option(label, dataset.id);
    option.disabled = Boolean(dataset.error);
    select.add(option);
  });
  if (state.trainingDatasets.some((dataset) => dataset.id === prior && !dataset.error)) select.value = prior;
  else if (state.trainingDatasets.some((dataset) => dataset.id === "entity_extraction_demo" && !dataset.error)) select.value = "entity_extraction_demo";
  updateFineTuneDatasetNote();
  const runtime = state.trainingRuntime;
  const note = $("fineTuneRuntimeNote");
  if (!runtime) {
    note.textContent = "Local training runtime is unavailable.";
  } else if (!runtime.available) {
    note.textContent = "Install project dependencies to enable training.";
    note.title = "Missing packages: " + runtime.missing.join(", ");
  } else {
    note.textContent = runtime.device.toUpperCase() + " · " + runtime.base_model;
    note.title = "Training and evaluation run on this machine.";
  }
  updateFineTuneSubmit();
}

function updateFineTuneDatasetNote() {
  const dataset = state.trainingDatasets.find((item) => item.id === $("fineTuneDataset").value);
  const note = $("fineTuneDatasetNote");
  if (!dataset) {
    note.textContent = "Add reviewed JSONL examples under training/datasets/.";
  } else if (dataset.error) {
    note.textContent = dataset.error;
  } else if (dataset.synthetic) {
    note.textContent = "Synthetic demo only; it is not a model-quality benchmark.";
  } else {
    note.textContent = "Local JSONL dataset. Review labels before training.";
  }
  renderFineTuneDatasetReadiness(dataset);
  updateFineTuneSubmit();
}

function renderFineTuneDatasetReadiness(dataset) {
  const container = $("fineTuneDatasetReadiness");
  container.replaceChildren();
  container.hidden = !dataset;
  if (!dataset) return;

  const heading = document.createElement("div");
  heading.className = "dataset-quality-heading";
  const title = document.createElement("strong");
  title.textContent = "Dataset readiness";
  const status = document.createElement("span");
  status.className = "dataset-quality-status" + (dataset.error ? " is-warning" : " is-ready");
  status.textContent = dataset.error ? "Needs repair" : "Ready";
  heading.append(title, status);
  container.append(heading);

  if (dataset.error) {
    const error = document.createElement("p");
    error.className = "dataset-quality-error";
    error.textContent = dataset.error;
    container.append(error);
    return;
  }

  const splits = dataset.splits || {};
  const stats = document.createElement("dl");
  stats.className = "dataset-quality-stats";
  [["Examples", dataset.examples], ["Source groups", dataset.groups]].forEach(([label, value]) => {
    const item = document.createElement("div");
    const term = document.createElement("dt");
    term.textContent = label;
    const count = document.createElement("dd");
    count.textContent = value == null ? "—" : String(value);
    item.append(term, count);
    stats.append(item);
  });
  container.append(stats);

  const validation = document.createElement("p");
  validation.className = "dataset-validation-note";
  validation.textContent = "Schema validated · source groups stay together across splits";
  container.append(validation);

  const splitList = document.createElement("div");
  splitList.className = "dataset-split-list";
  [["Train", splits.train], ["Validation", splits.validation], ["Test", splits.test]].forEach(([label, value]) => {
    const item = document.createElement("div");
    item.className = "dataset-split-item";
    const term = document.createElement("span");
    term.textContent = label;
    const count = document.createElement("strong");
    count.textContent = value == null ? "—" : String(value);
    item.append(term, count);
    splitList.append(item);
  });
  container.append(splitList);

  const fingerprint = document.createElement("p");
  fingerprint.className = "dataset-fingerprint";
  const label = document.createElement("span");
  label.textContent = "Dataset version";
  const digest = document.createElement("code");
  digest.textContent = dataset.sha256 ? dataset.sha256.slice(0, 12) : "Unavailable";
  digest.title = dataset.sha256 || "Dataset fingerprint unavailable";
  fingerprint.append(label, digest);
  container.append(fingerprint);
}

function updateFineTuneSubmit() {
  const dataset = state.trainingDatasets.find((item) => item.id === $("fineTuneDataset").value);
  $("fineTuneSubmit").disabled = state.jobBusy || !state.trainingRuntime?.available || !dataset || Boolean(dataset.error);
}

async function loadSavedAdapters() {
  try {
    const result = await apiCall("training/adapters");
    state.trainedAdapters = result.adapters || [];
    renderSavedAdapters();
  } catch {
    state.trainedAdapters = [];
    $("savedAdapters").hidden = true;
  }
}

function renderSavedAdapters() {
  const section = $("savedAdapters");
  const list = $("savedAdapterList");
  section.hidden = state.trainedAdapters.length === 0;
  list.replaceChildren();
  state.trainedAdapters.forEach((adapter) => {
    const row = document.createElement("article");
    row.className = "adapter-row";
    const copy = document.createElement("div");
    const fingerprint = adapter.dataset_sha256 ? " · data " + adapter.dataset_sha256.slice(0, 12) : "";
    copy.innerHTML = "<strong>" + escapeHTML(adapter.dataset_id) + "</strong><span>" + escapeHTML(adapter.id + fingerprint) + " · held-out exact match " + formatPercent(adapter.metrics?.record_exact_match) + "</span>";
    const button = document.createElement("button");
    button.className = "button button-secondary";
    button.type = "button";
    button.dataset.model = adapter.id;
    button.textContent = "Evaluate";
    row.append(copy, button);
    list.append(row);
  });
}

async function connectAPI() {
  const key = $("apiKeyInput").value.trim();
  if (!key) return showToast("Enter the server API key to connect.", "error");
  const button = $("connectApiBtn");
  button.disabled = true;
  try {
    await apiCall("session", { method: "POST", body: JSON.stringify({ api_key: key }) });
    state.apiKey = key;
    $("apiKeyInput").value = "";
    $("apiAuth").hidden = true;
    updateAPIStatus("connected", "API connected");
    await loadInitialData();
  } catch (error) {
    showToast("Could not connect: " + error.message, "error");
  } finally { button.disabled = false; }
}

async function handleEvaluate(event) {
  event.preventDefault();
  const custom = $("evalUseCustomPrompt").checked;
  const inputs = readLines("evalTestInputs");
  if (!inputs.length) return showToast("Add at least one test input.", "error");
  const payload = { task: custom ? "custom" : $("evalTask").value, version: custom ? "v1" : $("evalVersion").value,
    models: getChecked("evalModels"), test_inputs: inputs, generate_test_cases: false };
  if (!custom && (!payload.task || !payload.version)) return showToast("Choose a task and prompt version.", "error");
  if (custom) {
    payload.custom_prompt = $("evalCustomPrompt").value.trim();
    if (!payload.custom_prompt) return showToast("Add a prompt template.", "error");
    payload.custom_constraints = { temperature: Number($("evalCustomTemp").value), max_tokens: Number($("evalCustomMaxTokens").value) };
  } else if ($("evalGenerateTests").checked) {
    payload.generate_test_cases = true;
    payload.test_case_count = Number($("evalTestCount").value);
  }
  if (!payload.models.length) return showToast("Select at least one model.", "error");
  await submitJob("/evaluate", payload, "evaluation");
}

async function handleCompare(event) {
  event.preventDefault();
  const custom = $("compareUseCustom").checked;
  const payload = { models: getChecked("compareModels"), test_input: $("compareTestInput").value.trim() };
  if (!payload.test_input) return showToast("Add the input both prompts should receive.", "error");
  if (custom) {
    const promptA = $("comparePromptA").value.trim();
    const promptB = $("comparePromptB").value.trim();
    if (!promptA || !promptB) return showToast("Write both prompt drafts.", "error");
    payload.task = "custom";
    payload.versions = ["Prompt A", "Prompt B"];
    payload.custom_prompts = { "Prompt A": promptA, "Prompt B": promptB };
  } else {
    payload.task = $("compareTask").value;
    payload.versions = getChecked("compareVersions");
    if (!payload.task) return showToast("Choose a task.", "error");
    if (payload.versions.length !== 2) return showToast("Choose exactly two prompt versions.", "error");
  }
  if (!payload.models.length) return showToast("Select at least one model.", "error");
  await submitJob("/compare", payload, "comparison");
}

async function handleEvolve(event) {
  event.preventDefault();
  const custom = $("evolveUseCustomPrompt").checked;
  const inputs = readLines("evolveTestInputs");
  if (!inputs.length) return showToast("Add at least one input for prompt evolution.", "error");
  const payload = { task: custom ? "custom" : $("evolveTask").value, version: custom ? "v1" : $("evolveVersion").value,
    model: $("evolveModel").value, optimizer_model: $("evolveOptimizer").value,
    max_iterations: Number($("evolveIterations").value), test_inputs: inputs };
  if (!custom && (!payload.task || !payload.version)) return showToast("Choose a task and prompt version.", "error");
  if (custom) {
    payload.custom_prompt = $("evolveCustomPrompt").value.trim();
    if (!payload.custom_prompt) return showToast("Add a starting prompt.", "error");
    payload.custom_constraints = { temperature: Number($("evolveCustomTemp").value), max_tokens: Number($("evolveCustomMaxTokens").value) };
  }
  if (!payload.model) return showToast("Choose the model that will run the prompt.", "error");
  await submitJob("/evolve", payload, "evolution");
}

async function handleTestcase(event) {
  event.preventDefault();
  const baseInputs = readLines("testcaseBase");
  if (!baseInputs.length) return showToast("Add at least one base input.", "error");
  const payload = { task_type: $("testcaseType").value, base_inputs: baseInputs, count: Number($("testcaseCount").value) };
  const button = event.submitter;
  if (button) button.disabled = true;
  try {
    const result = await apiCall("test-cases/generate", { method: "POST", body: JSON.stringify(payload) });
    displayTestCases(result.test_cases || []);
    showToast("Test cases generated. Review them before using as labels.", "success");
  } catch (error) { showToast("Could not generate cases: " + error.message, "error"); }
  finally { if (button) button.disabled = false; }
}

async function handleFineTune(event) {
  event.preventDefault();
  if (state.jobBusy) return showToast("Wait for the current model run to finish.", "warning");
  const payload = {
    dataset_id: $("fineTuneDataset").value,
    epochs: Number($("fineTuneEpochs").value),
    learning_rate: Number($("fineTuneLearningRate").value),
    lora_rank: Number($("fineTuneRank").value)
  };
  if (!payload.dataset_id) return showToast("Choose a local training dataset.", "error");
  state.jobBusy = true;
  setExperimentButtonsDisabled(true);
  try {
    const result = await apiCall("training/jobs", { method: "POST", body: JSON.stringify(payload) });
    if (!result.job_id) throw new Error("The API did not return a training job ID.");
    startPolling(result.job_id, "training");
  } catch (error) {
    state.jobBusy = false;
    setExperimentButtonsDisabled(false);
    showToast("Could not start local training: " + error.message, "error");
  }
}

async function submitJob(endpoint, payload, type) {
  if (state.jobBusy) return showToast("Wait for the current model run to finish.", "warning");
  state.jobBusy = true;
  setExperimentButtonsDisabled(true);
  try {
    const result = await apiCall(endpoint, { method: "POST", body: JSON.stringify(payload) });
    if (!result.job_id) throw new Error("The API did not return a job ID.");
    startPolling(result.job_id, type);
  } catch (error) {
    state.jobBusy = false;
    setExperimentButtonsDisabled(false);
    showToast("Could not start the run: " + error.message, "error");
  }
}

function setExperimentButtonsDisabled(disabled) {
  ["evaluateForm", "compareForm", "evolveForm"].forEach((id) => {
    const button = $(id).querySelector('button[type="submit"]');
    if (button) button.disabled = disabled;
  });
  updateFineTuneSubmit();
}

function startPolling(jobId, type) {
  clearInterval(state.pollingTimer);
  showProgressModal(type);
  let polls = 0;
  const maxPolls = type === "training" ? 1800 : 150;
  state.pollingTimer = window.setInterval(async () => {
    polls += 1;
    if (polls > maxPolls) {
      stopPolling();
      showToast("This job is taking longer than expected. Check API status and run history.", "warning");
      return;
    }
    try {
      const job = await apiCall("jobs/" + encodeURIComponent(jobId));
      updateProgress(job.progress, job.status, job.stage);
      if (job.status === "completed") {
        stopPolling();
        if (type === "training") {
          if (!job.result) {
            showToast("Training completed without an adapter result.", "warning");
            return;
          }
          displayFineTuneRun(job.result);
          await loadInitialData();
          showToast("Local adapter trained and saved.", "success");
          return;
        }
        const hasResults = Array.isArray(job.results)
          ? job.results.length > 0
          : type === "evolution" && Array.isArray(job.results?.history) && job.results.history.length > 0;
        if (!hasResults) {
          showToast("The job completed without results.", "warning");
          return;
        }
        handleJobResult(type, job.results);
        addToHistory(jobId, type, job);
        showToast("Run completed.", "success");
      } else if (job.status === "failed") {
        stopPolling();
        showToast("The run failed: " + (job.error || "No error details were returned."), "error");
      }
    } catch (error) {
      stopPolling();
      showToast("Could not retrieve the job: " + error.message, "error");
    }
  }, 2000);
}

function stopPolling() {
  clearInterval(state.pollingTimer);
  state.pollingTimer = null;
  state.jobBusy = false;
  setExperimentButtonsDisabled(false);
  if ($("progressModal").open) $("progressModal").close();
}

function showProgressModal(type) {
  const labels = { evaluation: "Running model evaluation", comparison: "Comparing prompt versions", evolution: "Evolving the prompt", training: "Training a local LoRA adapter" };
  $("progressTitle").textContent = labels[type] || "Running your job";
  $("progressText").textContent = type === "training" ? "Loading the local base model and preparing held-out evaluation." : "The API is waiting for model responses.";
  $("progressFootnote").textContent = type === "training" ? "The first run may download model weights. Keep this tab open while training runs." : "You can keep this tab open while the models respond.";
  $("progressFill").style.width = "0%";
  if (!$("progressModal").open) $("progressModal").showModal();
}

function updateProgress(percent, status, stage) {
  const amount = Number(percent);
  $("progressFill").style.width = (Number.isFinite(amount) ? Math.max(0, Math.min(amount, 100)) : 0) + "%";
  const labels = {
    loading_model: "Loading the base model on this machine.",
    evaluating_base: "Scoring the base model on held-out examples.",
    training: "Training LoRA weights and measuring validation loss.",
    evaluating_adapter: "Scoring the adapter on the same held-out examples.",
    completed: "Training and held-out evaluation are complete."
  };
  $("progressText").textContent = labels[stage] || (status === "running" ? "Models are processing the selected inputs." : (status || "Working…"));
}

function handleJobResult(type, results) {
  if (type === "evaluation") { state.lastEvaluationResults = results; displayEvaluation(results); activateTab("evaluate", true); }
  if (type === "comparison") { state.lastComparisonResults = results; displayComparison(results); activateTab("compare", true); }
  if (type === "evolution") { state.lastEvolutionResults = results; displayEvolution(results); activateTab("evolve", true); }
}

function displayEvaluation(results) {
  const rows = [];
  const scores = [];
  let cases = 0;
  results.forEach((model) => {
    const modelResults = model.results || [];
    cases = Math.max(cases, modelResults.length);
    if (model.average_score !== null && model.average_score !== undefined && Number.isFinite(Number(model.average_score))) scores.push(Number(model.average_score));
    modelResults.forEach((item) => {
      rows.push("<tr><td class=\"model-cell\">" + escapeHTML(model.model) + "</td><td>" + escapeHTML(item.input) + "</td><td class=\"number-cell\">" + formatNumber(item.score) + "</td><td>" + breakdownMarkup(item.breakdown) + "</td><td class=\"number-cell\">" + formatNumber(item.latency_ms, 0) + " ms</td><td class=\"number-cell\">" + formatNumber(item.tokens, 0) + "</td><td class=\"output-cell\">" + escapeHTML(item.output) + "</td></tr>");
    });
  });
  $("evaluateResults").hidden = false;
  $("evaluationSummary").textContent = results.length + " model" + (results.length === 1 ? "" : "s") + " · " + cases + " test input" + (cases === 1 ? "" : "s");
  const best = results[0];
  $("evaluationStats").innerHTML = statMarkup("Best model", best?.model || "—") + statMarkup("Best score", formatNumber(best?.average_score)) + statMarkup("Models", results.length) + statMarkup("Test inputs", cases) + statMarkup("Mean score", scores.length ? mean(scores).toFixed(2) : "—");
  $("evaluationModels").innerHTML = rows.length ? rows.join("") : '<tr><td colspan="7">No response rows were returned.</td></tr>';
}

function displayComparison(results) {
  $("compareResults").hidden = false;
  $("comparisonTableBody").innerHTML = results.map((row) => "<tr><td class=\"model-cell\">" + escapeHTML(row.prompt_version) + "</td><td>" + escapeHTML(row.model) + "</td><td class=\"number-cell\">" + formatNumber(row.score) + "</td><td>" + breakdownMarkup(row.breakdown) + "</td><td class=\"output-cell\">" + escapeHTML(row.output) + "</td></tr>").join("");
}

function displayEvolution(results) {
  $("evolveResults").hidden = false;
  const history = Array.isArray(results) ? results : (results.history || []);
  const first = results.initial_score ?? history[0]?.score;
  const last = results.final_score ?? history[history.length - 1]?.score;
  const change = results.improvement ?? (Number(last) - Number(first));
  const delta = Number.isFinite(Number(change)) ? (Number(change) >= 0 ? "+" : "") + Number(change).toFixed(2) : "—";
  $("evolutionStats").innerHTML = statMarkup("Iterations", Math.max(0, history.length - 1)) + statMarkup("Starting score", formatNumber(first)) + statMarkup("Change", delta);
  $("evolutionTimeline").innerHTML = history.map((item, index) => "<article class=\"evolution-item\"><span>Iteration " + escapeHTML(item.iteration ?? index) + "</span><pre>" + escapeHTML(item.prompt || "No prompt text was returned.") + "</pre><strong>" + formatNumber(item.score) + "</strong></article>").join("");
}

function displayFineTuneRun(result) {
  state.activeAdapterModel = result.model_id;
  const splits = result.split_counts || {};
  const base = result.metrics?.base || {};
  const adapter = result.metrics?.adapter || {};
  const fingerprint = result.dataset_sha256 ? " · data " + result.dataset_sha256.slice(0, 12) : "";
  $("fineTuneResults").hidden = false;
  $("fineTuneSummary").textContent = result.dataset_id + fingerprint + " · " + (splits.test || 0) + " held-out examples · " + (result.elapsed_seconds || 0) + " seconds";
  $("fineTuneStats").innerHTML = statMarkup("Base checkpoint", result.base_model)
    + statMarkup("Adapter", result.model_id)
    + statMarkup("Training examples", splits.train || 0)
    + statMarkup("Validation examples", splits.validation || 0)
    + statMarkup("Test examples", splits.test || 0)
    + statMarkup("Device", result.device || "—");
  $("fineTuneMetrics").innerHTML = [
    trainingMetricMarkup("Record exact match", base.record_exact_match, adapter.record_exact_match),
    trainingMetricMarkup("Field accuracy", base.field_accuracy, adapter.field_accuracy),
    trainingMetricMarkup("Valid JSON", base.json_valid_rate, adapter.json_valid_rate),
    ...["organization", "year", "claim"].map((field) => trainingMetricMarkup(field + " exact", base.field_exact_match?.[field], adapter.field_exact_match?.[field]))
  ].join("");
  renderLossChart(result.training_loss || [], result.validation_loss || []);
}

function trainingMetricMarkup(label, base, adapter) {
  const delta = (Number(adapter) - Number(base)) * 100;
  const change = Number.isFinite(delta) ? (delta > 0 ? "+" : "") + delta.toFixed(1) + " pp" : "—";
  return "<article class=\"training-metric\"><span>" + escapeHTML(label) + "</span><div><small>Base</small><strong>" + formatPercent(base) + "</strong></div><div><small>LoRA</small><strong>" + formatPercent(adapter) + "</strong></div><b>" + escapeHTML(change) + "</b></article>";
}

function renderLossChart(trainingLoss, validationLoss) {
  const series = [
    { label: "Training", values: trainingLoss, className: "loss-train" },
    { label: "Validation", values: validationLoss, className: "loss-validation" }
  ].map((item) => ({ ...item, values: item.values.map(Number).filter(Number.isFinite) })).filter((item) => item.values.length);
  const container = $("fineTuneLossChart");
  if (!series.length) {
    container.textContent = "Loss history was not returned.";
    return;
  }
  const values = series.flatMap((item) => item.values).map(Number).filter(Number.isFinite);
  const max = Math.max(...values, 0.01);
  const width = 540, height = 130, left = 30, top = 12, plotWidth = 495, plotHeight = 92;
  const polylines = series.map((item) => {
    const points = item.values.map((value, index) => {
      const x = left + (item.values.length === 1 ? 0 : index / (item.values.length - 1) * plotWidth);
      const y = top + plotHeight - (Math.max(0, Number(value)) / max * plotHeight);
      return x.toFixed(1) + "," + y.toFixed(1);
    }).join(" ");
    return "<polyline class=\"" + item.className + "\" points=\"" + points + "\"></polyline>";
  }).join("");
  const legend = series.map((item) => "<span class=\"" + item.className + "\">" + item.label + "</span>").join("");
  container.innerHTML = "<div class=\"loss-legend\">" + legend + "</div><svg viewBox=\"0 0 " + width + " " + height + "\" role=\"img\" aria-label=\"Training and validation loss trend\"><path class=\"loss-axis\" d=\"M" + left + " " + top + "V" + (top + plotHeight) + "H" + (left + plotWidth) + "\"></path>" + polylines + "<text x=\"" + left + "\" y=\"121\">start</text><text x=\"" + (left + plotWidth) + "\" y=\"121\" text-anchor=\"end\">progress</text></svg>";
}

async function useAdapterInEvaluation(modelId) {
  if (!modelId) return showToast("Train or select a saved adapter first.", "warning");
  try {
    state.models = await apiCall("models");
    populateModelSelectors();
    const modelInputs = Array.from($("evalModels").querySelectorAll("input"));
    const trainedModel = modelInputs.find((input) => input.value === modelId);
    if (!trainedModel) throw new Error("The trained adapter is no longer registered.");
    modelInputs.forEach((input) => { input.checked = input === trainedModel; });
    if (state.tasks.includes("extraction")) {
      $("evalTask").value = "extraction";
      await loadVersionsForTask("extraction", "evalVersion");
      if (Array.from($("evalVersion").options).some((option) => option.value === "v1")) $("evalVersion").value = "v1";
    }
    activateTab("evaluate", true);
    $("evalTestInputs").focus({ preventScroll: true });
    showToast("Adapter selected. Add a separate held-out input set before evaluating.", "success");
  } catch (error) {
    showToast("Could not select adapter: " + error.message, "error");
  }
}

function breakdownMarkup(breakdown) {
  const entries = Object.entries(breakdown || {});
  if (!entries.length) return "—";
  return "<details class=\"breakdown-details\"><summary>View detail</summary><dl>" + entries.map(([key, value]) => "<div><dt>" + escapeHTML(key.replaceAll("_", " ")) + "</dt><dd>" + escapeHTML(typeof value === "number" ? formatNumber(value) : String(value ?? "—")) + "</dd></div>").join("") + "</dl></details>";
}

function displayTestCases(cases) {
  $("testcasesResults").hidden = false;
  const list = $("testcasesResultsList");
  list.replaceChildren();
  if (!cases.length) {
    const item = document.createElement("li");
    item.textContent = "No test cases were returned.";
    list.append(item);
    return;
  }
  cases.forEach((text) => { const item = document.createElement("li"); item.textContent = text; list.append(item); });
}

function addToHistory(jobId, type, job) {
  const rows = type === "evolution" ? (job.results.history || []) : (job.results || []);
  let scores = [];
  if (type === "evaluation") scores = rows.map((item) => Number(item.average_score)).filter(Number.isFinite);
  if (type === "comparison") scores = rows.map((item) => Number(item.score)).filter(Number.isFinite);
  if (type === "evolution" && Number.isFinite(Number(job.results.final_score))) scores = [Number(job.results.final_score)];
  state.jobHistory.unshift({ id: jobId, type, completedAt: job.completed_at || new Date().toISOString(), count: rows.length, score: scores.length ? mean(scores) : null });
  state.jobHistory = state.jobHistory.slice(0, 30);
  try { localStorage.setItem(HISTORY_KEY, JSON.stringify(state.jobHistory)); } catch { showToast("Run completed, but browser storage is unavailable.", "warning"); }
  renderHistory();
  renderOverviewHistory();
}

function loadJobHistory() {
  try {
    const saved = JSON.parse(localStorage.getItem(HISTORY_KEY) || localStorage.getItem("jobHistory") || "[]");
    state.jobHistory = Array.isArray(saved) ? saved.filter((item) => item && typeof item.id === "string" && validJobType(item.type)).slice(0, 30) : [];
  } catch { state.jobHistory = []; }
}

function validJobType(type) { return ["evaluation", "comparison", "evolution"].includes(type); }
function typeLabel(type) { return ({ evaluation: "Evaluation", comparison: "Prompt comparison", evolution: "Prompt evolution" })[type] || "Model run"; }

function renderHistory() {
  const container = $("historyList");
  if (!state.jobHistory.length) {
    container.innerHTML = '<div class="empty-inline"><span class="empty-mark" aria-hidden="true">—</span><div><strong>No completed runs</strong><p>Evaluation, comparison, and evolution summaries will appear here.</p></div></div>';
    return;
  }
  container.innerHTML = state.jobHistory.map((item) => "<div class=\"history-row\"><strong>" + escapeHTML(typeLabel(item.type)) + "</strong><span>" + escapeHTML(formatDate(item.completedAt)) + "</span><span>" + escapeHTML(String(item.count || 0)) + " result" + (item.count === 1 ? "" : "s") + "</span><span class=\"history-score\">" + (item.score === null ? "—" : formatNumber(item.score)) + "</span><button class=\"text-button\" type=\"button\" data-view-job=\"" + escapeHTML(item.id) + "\">Open</button></div>").join("");
  container.querySelectorAll("[data-view-job]").forEach((button) => button.addEventListener("click", () => openHistoryJob(button.dataset.viewJob)));
}

function renderOverviewHistory() {
  const container = $("overviewHistory");
  if (!state.jobHistory.length) {
    container.innerHTML = '<div class="empty-inline"><span class="empty-mark" aria-hidden="true">—</span><div><strong>No runs yet</strong><p>Your completed evaluations will appear here.</p></div></div>';
    return;
  }
  container.innerHTML = state.jobHistory.slice(0, 4).map((item) => "<div class=\"recent-row\"><span class=\"recent-kind\">" + escapeHTML(typeLabel(item.type)) + "</span><span class=\"recent-meta\">" + escapeHTML(String(item.count || 0)) + " results</span><span class=\"recent-score\">" + (item.score === null ? "—" : formatNumber(item.score)) + "</span></div>").join("");
}

async function openHistoryJob(jobId) {
  try {
    const item = state.jobHistory.find((entry) => entry.id === jobId);
    if (!item) return;
    const job = await apiCall("jobs/" + encodeURIComponent(jobId));
    if (job.status !== "completed" || !job.results) throw new Error("The API no longer has this job's full results. Run it again to inspect the outputs.");
    if (item.type === "evaluation") state.lastEvaluationResults = job.results;
    if (item.type === "comparison") state.lastComparisonResults = job.results;
    if (item.type === "evolution") state.lastEvolutionResults = job.results;
    handleJobResult(item.type, job.results);
  } catch (error) { showToast(error.message, "error"); }
}

function clearHistory() {
  if (!state.jobHistory.length) return;
  if (!window.confirm("Clear the " + state.jobHistory.length + " run summaries saved in this browser? Full API jobs are unaffected.")) return;
  state.jobHistory = [];
  try { localStorage.removeItem(HISTORY_KEY); localStorage.removeItem("jobHistory"); }
  catch { showToast("Could not remove saved history from browser storage.", "warning"); }
  renderHistory();
  renderOverviewHistory();
}

function exportResults(type) {
  const results = ({ evaluation: state.lastEvaluationResults, comparison: state.lastComparisonResults, evolution: state.lastEvolutionResults })[type];
  if (!results) return showToast("There are no " + type + " results to export yet.", "warning");
  const blob = new Blob([JSON.stringify(results, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "promptmesh-" + type + "-" + new Date().toISOString().replace(/[:.]/g, "-") + ".json";
  link.click();
  URL.revokeObjectURL(url);
  showToast("Results exported as JSON.", "success");
}

function loadExamplePrompt(target) {
  const id = target === "comparePromptA" || target === "comparePromptB" ? target : target + "CustomPrompt";
  const input = $(id);
  if (!input) return;
  input.value = target === "comparePromptB"
    ? "Identify the key facts in the text, then provide a concise two-sentence summary:\n\n{text}"
    : target === "comparePromptA"
      ? "Summarize the following text in two sentences. Use only information stated in it:\n\n{text}"
      : "You are a careful information extractor. Return only the requested fields as valid JSON. Use null when a fact is missing.\n\nText: {{text}}";
  input.focus();
}

function loadExampleTestInputs(target) {
  const input = $(target === "eval" ? "evalTestInputs" : "evolveTestInputs");
  input.value = "Northstar opened a research studio in 2024.\nThe company did not disclose the opening date.\nTwo organizations, Northstar and Vale Labs, announced a joint project in 2023.";
  input.focus();
}

function updateVersionCount() {
  const count = $("compareVersions").querySelectorAll("input:checked").length;
  $("versionCount").textContent = count + " of 2 selected";
}

function getChecked(id) { return Array.from($(id).querySelectorAll("input:checked"), (input) => input.value); }
function readLines(id) { return $(id).value.split(/\r?\n/).map((line) => line.trim()).filter(Boolean); }
function statMarkup(label, value) { return "<div class=\"result-stat\"><span>" + escapeHTML(label) + "</span><strong>" + escapeHTML(String(value)) + "</strong></div>"; }
function mean(values) { return values.reduce((total, value) => total + value, 0) / values.length; }
function formatNumber(value, digits = 2) { const number = value === null || value === undefined || value === "" ? NaN : Number(value); return Number.isFinite(number) ? number.toFixed(digits) : "—"; }
function formatPercent(value) { const number = value === null || value === undefined || value === "" ? NaN : Number(value); return Number.isFinite(number) ? (number * 100).toFixed(1) + "%" : "—"; }
function formatDate(value) { const date = new Date(value); return Number.isNaN(date.getTime()) ? "Unknown time" : date.toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }); }
function escapeHTML(value) { return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" })[char]); }

function showToast(message, type = "info") {
  const toast = document.createElement("div");
  toast.className = "toast " + type;
  toast.textContent = message;
  $("toastContainer").append(toast);
  window.setTimeout(() => toast.remove(), 4500);
}
