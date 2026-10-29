const API_BASE = window.location.origin;
const HISTORY_KEY = "promptmesh.run-summaries.v1";
const state = {
  tasks: [],
  models: {},
  trainingDatasets: [],
  trainingRuntime: null,
  quantizationRuntime: null,
  reviewPacket: null,
  reviewPacketError: null,
  reviewPacketCurrentGroupId: null,
  reviewPacketYear: "all",
  reviewPacketDirty: false,
  reviewPacketSaving: false,
  reviewPacketExporting: false,
  trainedAdapters: [],
  activeAdapterModel: null,
  activeTab: "overview",
  pollingTimer: null,
  jobBusy: false,
  backgroundJob: null,
  apiKey: null,
  jobHistory: [],
  lastEvaluationResults: null,
  lastComparisonResults: null,
  lastEvolutionResults: null,
  lastPromptSelection: null,
  lastBenchmarkReport: null
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
  const [tasksResult, modelsResult, trainingResult, reviewPacketResult] = await Promise.allSettled([
    apiCall("tasks"), apiCall("models"), apiCall("training/datasets"), apiCall("training/review-packet")
  ]);
  if (tasksResult.status === "fulfilled") state.tasks = tasksResult.value.tasks || [];
  if (modelsResult.status === "fulfilled") state.models = modelsResult.value || {};
  if (trainingResult.status === "fulfilled") {
    state.trainingDatasets = trainingResult.value.datasets || [];
    state.trainingRuntime = trainingResult.value.runtime || null;
    state.quantizationRuntime = trainingResult.value.quantization || null;
  } else {
    state.trainingDatasets = [];
    state.trainingRuntime = null;
    state.quantizationRuntime = null;
  }
  if (reviewPacketResult.status === "fulfilled") {
    state.reviewPacket = reviewPacketResult.value;
    state.reviewPacketError = null;
  } else {
    state.reviewPacket = null;
    state.reviewPacketError = reviewPacketResult.reason?.message || "The local review packet could not be loaded.";
  }
  populateTaskDropdowns();
  populateModelSelectors();
  populateTrainingDatasets();
  renderCandidateReviewPacket();
  await loadSavedAdapters();
  populateModelSelectors();
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
  const modelLabel = (model) => state.trainedAdapters.some((adapter) =>
    adapter.id === model && adapter.dataset_id === "entity_extraction_demo"
  ) ? model + " · synthetic demo · workflow only" : model;
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
      name.textContent = modelLabel(model);
      label.append(input, name);
      container.append(label);
    });
  });
  const select = $("evolveModel");
  const prior = select.value;
  select.replaceChildren(new Option("Select a model", ""));
  (state.models.all || []).forEach((model) => select.add(new Option(modelLabel(model), model)));
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
    button.addEventListener("click", () => activateTab(button.dataset.tab, true, true));
  });
  document.querySelectorAll("[data-go]").forEach((button) => {
    button.addEventListener("click", () => activateTab(button.dataset.go, true, true));
  });
  window.addEventListener("hashchange", () => {
    const tab = window.location.hash.slice(1);
    if (tab !== "workspace") activateTab(validTab(tab) ? tab : "overview", false, true);
  });
  const initial = window.location.hash.slice(1);
  activateTab(validTab(initial) ? initial : "overview", false);
}

function validTab(tab) { return ["overview", "evaluate", "compare", "evolve", "finetune", "testcases", "history"].includes(tab); }
function canRunInBackground(type) { return ["training", "evolution", "promptSelection", "frozenBenchmark"].includes(type); }

function activateTab(tab, updateHash, moveFocus = false) {
  if (!validTab(tab)) tab = "overview";
  state.activeTab = tab;
  $("backToOverview").hidden = tab === "overview";
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
  const titleId = tab === "finetune" ? "fineTuneTitle" : tab + "Title";
  if (moveFocus) $(titleId).focus();
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
  $("reviewPacketForm").addEventListener("submit", handleSaveCandidateReview);
  $("reviewPacketYear").addEventListener("change", handleReviewYearChange);
  $("reviewPacketGroup").addEventListener("change", handleReviewGroupChange);
  $("reviewPacketPrevious").addEventListener("click", () => moveReviewGroup(-1));
  $("reviewPacketNext").addEventListener("click", moveToNextUnreviewedGroup);
  $("reviewPacketForm").addEventListener("input", () => {
    state.reviewPacketDirty = true;
    updateReviewExportControls();
  });
  $("reviewPacketForm").addEventListener("change", () => {
    state.reviewPacketDirty = true;
    updateReviewEvidenceField();
    updateReviewExportControls();
  });
  $("reviewExportButton").addEventListener("click", handleExportReviewedDataset);
  $("reviewExportDatasetId").addEventListener("input", () => updateReviewExportControls());
  $("reviewExportReviewerRole").addEventListener("input", () => updateReviewExportControls());
  $("reviewExportCohort").addEventListener("change", () => updateReviewExportControls());
  $("promptSelectionForm").addEventListener("submit", handlePromptSelection);
  $("benchmarkAdapter").addEventListener("change", updateBenchmarkControls);
  $("benchmarkCandidatePrompt").addEventListener("input", updateBenchmarkControls);
  $("runFrozenBenchmarkBtn").addEventListener("click", handleFrozenBenchmark);
  $("evaluateAdapterBtn").addEventListener("click", () => useAdapterInEvaluation(state.activeAdapterModel));
  $("savedAdapterList").addEventListener("click", (event) => {
    const button = event.target.closest("[data-model]");
    if (button) useAdapterInEvaluation(button.dataset.model);
  });
  $("connectApiBtn").addEventListener("click", connectAPI);
  $("refreshBtn").addEventListener("click", checkAPIHealth);
  $("clearHistoryBtn").addEventListener("click", clearHistory);
  $("progressBackgroundBtn").addEventListener("click", () => $("progressModal").close());
  $("backgroundJobStatus").addEventListener("click", openBackgroundJob);
  $("progressModal").addEventListener("cancel", (event) => {
    if (!(state.backgroundJob?.status === "running" && canRunInBackground(state.backgroundJob.type))) event.preventDefault();
  });
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

function renderCandidateReviewPacket() {
  const summary = $("candidateReviewSummary");
  const coverage = $("candidateReviewCoverage");
  const workspace = $("candidateReviewWorkspace");
  const message = $("candidateReviewMessage");
  const packet = state.reviewPacket;
  updateReviewExportControls(packet);
  if (!packet) {
    summary.textContent = "Local review unavailable";
    coverage.textContent = "";
    workspace.hidden = true;
    message.hidden = false;
    message.textContent = state.reviewPacketError === "The API request failed (404)."
      ? "The running API does not include the review endpoint yet. Restart PromptMesh on this machine and refresh."
      : state.reviewPacketError || "The private candidate review packet is unavailable.";
    return;
  }

  summary.textContent = `${packet.total_rows} rows · ${packet.total_groups} source groups · ${packet.reviewed_rows} labels reviewed · ${packet.excluded_rows || 0} variants excluded · ${packet.eligible_groups} export-eligible groups`;
  if (!packet.groups.length) {
    coverage.textContent = "";
    workspace.hidden = true;
    message.hidden = false;
    message.textContent = "The local review packet has no source groups.";
    return;
  }
  workspace.hidden = false;
  message.hidden = true;
  const selector = $("reviewPacketGroup");
  const yearFilter = $("reviewPacketYear");
  const prior = state.reviewPacketCurrentGroupId;
  const allGroups = interleaveCandidateReviewGroups(packet.groups);
  const years = [...new Set(allGroups.map(candidateReviewGroupYear))].sort((left, right) => {
    const leftYear = Number(left);
    const rightYear = Number(right);
    if (Number.isFinite(leftYear) && Number.isFinite(rightYear)) return leftYear - rightYear;
    if (Number.isFinite(leftYear)) return -1;
    if (Number.isFinite(rightYear)) return 1;
    return left.localeCompare(right);
  });
  const requestedYear = yearFilter.value || state.reviewPacketYear || "all";
  const selectedYear = requestedYear === "all" || years.includes(requestedYear) ? requestedYear : "all";
  yearFilter.replaceChildren();
  yearFilter.add(new Option("All years", "all"));
  years.forEach((year) => {
    const label = year === "undated" ? "Undated" : year === "mixed" ? "Mixed years" : year;
    yearFilter.add(new Option(label, year));
  });
  yearFilter.value = selectedYear;
  state.reviewPacketYear = selectedYear;
  const groups = selectedYear === "all"
    ? allGroups
    : allGroups.filter((group) => candidateReviewGroupYear(group) === selectedYear);
  coverage.textContent = candidateReviewCoverage(allGroups);
  const current = groups.find((group) => group.group_id === prior)
    || groups.find((group) => group.rows.some((row) => row.review_status !== "REVIEWED" && row.review_status !== "EXCLUDED"))
    || groups[0];
  state.reviewPacketCurrentGroupId = current.group_id;
  selector.replaceChildren(...groups.map((group) => {
    const label = `${group.source_title || group.group_id} · ${candidateReviewGroupYear(group)} · ${group.reviewed_rows} reviewed · ${group.excluded_rows || 0} excluded`;
    return new Option(label, group.group_id);
  }));
  selector.value = current.group_id;
  renderReviewGroup(current);
  state.reviewPacketDirty = false;
}

function updateReviewExportControls(packet = state.reviewPacket) {
  const button = $("reviewExportButton");
  const readiness = $("reviewExportReadiness");
  const cohortMode = $("reviewExportCohort").value || "all_eligible";
  const preview = cohortMode === "balanced_year_12"
    ? packet?.balanced_export_preview
    : packet?.export_preview;
  const datasetId = $("reviewExportDatasetId").value.trim();
  const reviewerRole = $("reviewExportReviewerRole").value.trim();
  const validDatasetId = /^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/.test(datasetId);
  button.disabled = !preview?.ready || !validDatasetId || !reviewerRole || state.reviewPacketDirty || state.reviewPacketSaving || state.reviewPacketExporting;
  if (!packet) {
    readiness.textContent = "The local review packet is unavailable.";
  } else if (preview?.ready) {
    const cohortLabel = cohortMode === "balanced_year_12"
      ? ` Host-diverse pilot: ${preview.groups_per_year} reviewed groups per year (2020–2025), seed 42; distinct normalized hosts selected by year: ${Object.entries(preview.selected_source_hosts_by_year || {}).map(([year, count]) => `${year} ${count}`).join(", ")}.`
      : " All eligible groups are included.";
    readiness.textContent = `${preview.examples} reviewed examples across ${preview.source_groups} groups.${cohortLabel} Validation: ${preview.validation_examples} examples / ${preview.validation_source_groups} groups. Final test: ${preview.final_test_examples} examples / ${preview.final_test_source_groups} groups.`;
  } else {
    readiness.textContent = preview?.reason || "Review labels and reuse evidence before exporting.";
  }
}

function candidateReviewGroupYear(group) {
  const years = [...new Set(group.rows.map((row) => String(row.proposed_year || "undated")))];
  return years.length === 1 ? years[0] : "mixed";
}

function interleaveCandidateReviewGroups(groups) {
  const buckets = new Map();
  for (const group of groups) {
    const year = candidateReviewGroupYear(group);
    if (!buckets.has(year)) buckets.set(year, []);
    buckets.get(year).push(group);
  }
  const years = [...buckets.keys()].sort((left, right) => {
    const leftYear = Number(left);
    const rightYear = Number(right);
    if (Number.isFinite(leftYear) && Number.isFinite(rightYear)) return leftYear - rightYear;
    if (Number.isFinite(leftYear)) return -1;
    if (Number.isFinite(rightYear)) return 1;
    return left.localeCompare(right);
  });
  const ordered = [];
  const longestBucket = Math.max(...[...buckets.values()].map((bucket) => bucket.length));
  for (let index = 0; index < longestBucket; index++) {
    for (const year of years) {
      if (buckets.get(year)[index]) ordered.push(buckets.get(year)[index]);
    }
  }
  return ordered;
}

function candidateReviewGroupsForYear(groups, year = "all") {
  const ordered = interleaveCandidateReviewGroups(groups);
  return year === "all" ? ordered : ordered.filter((group) => candidateReviewGroupYear(group) === year);
}

function candidateReviewCoverage(groups) {
  const years = new Map();
  const hosts = new Map();
  for (const group of groups) {
    const year = candidateReviewGroupYear(group);
    years.set(year, (years.get(year) || 0) + 1);
    const sourceUrl = safeHttpUrl(group.source_url);
    const host = sourceUrl ? new URL(sourceUrl).hostname.replace(/^www\./i, "") : "unknown host";
    hosts.set(host, (hosts.get(host) || 0) + 1);
  }
  const yearText = [...years.entries()]
    .sort(([left], [right]) => left === "undated" ? 1 : right === "undated" ? -1 : left.localeCompare(right, undefined, { numeric: true }))
    .map(([year, count]) => `${year} ${count}`)
    .join(" · ");
  const topHosts = [...hosts.entries()]
    .sort(([leftHost, leftCount], [rightHost, rightCount]) => rightCount - leftCount || leftHost.localeCompare(rightHost))
    .slice(0, 3)
    .map(([host, count]) => `${host} ${count}`)
    .join(", ");
  return `Draft coverage by proposed year (source groups): ${yearText}. ${hosts.size} source hosts; most common: ${topHosts}. This is not reviewed benchmark composition.`;
}

function renderReviewGroup(group) {
  const source = $("reviewPacketSource");
  source.replaceChildren();
  const title = document.createElement("h3");
  title.textContent = group.source_title || group.group_id;
  const meta = document.createElement("p");
  meta.textContent = `${group.group_id} · Source date ${group.source_date || "not listed"}`;
  const focus = document.createElement("p");
  focus.className = "review-source-focus";
  focus.textContent = group.review_focus || "Check the proposed labels against the linked source.";
  const url = safeHttpUrl(group.source_url);
  if (url) {
    const link = document.createElement("a");
    link.href = url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = "Open source page";
    source.append(title, meta, focus, link);
  } else {
    source.append(title, meta, focus);
  }

  const rows = $("reviewPacketRows");
  rows.replaceChildren(...group.rows.map((row, index) => renderReviewRow(row, index + 1, group.rows.length)));
  $("reviewSourceReuseStatus").value = reviewReuseStatus(group.reuse_status);
  $("reviewSourceEvidence").value = group.reuse_evidence || "";
  updateReviewEvidenceField();
  $("reviewPacketSaveStatus").textContent = `${group.reviewed_rows} reviewed · ${group.excluded_rows || 0} excluded of ${group.rows.length}. Saving never adds rows to training.`;
  updateReviewExportControls();
}

function renderReviewRow(row, ordinal, total) {
  const card = document.createElement("article");
  card.className = "review-row";
  card.dataset.rowIndex = String(row.row_index);
  const heading = document.createElement("div");
  heading.className = "review-row-heading";
  const title = document.createElement("h3");
  title.textContent = `Candidate ${ordinal} of ${total}`;
  const status = document.createElement("span");
  status.className = "review-row-status" + (row.review_status === "REVIEWED" ? " is-reviewed" : row.review_status === "EXCLUDED" ? " is-excluded" : " is-pending");
  status.textContent = row.review_status === "REVIEWED" ? "Reviewed" : row.review_status === "EXCLUDED" ? "Excluded" : "Needs review";
  heading.append(title, status);

  const input = document.createElement("blockquote");
  input.className = "review-candidate-text";
  input.textContent = row.input;
  const draft = document.createElement("p");
  draft.className = "review-draft-labels";
  draft.textContent = `Draft: ${row.proposed_organization || "—"} · ${row.proposed_year || "—"} · ${row.proposed_claim || "—"}`;

  const fields = document.createElement("div");
  fields.className = "review-fields";
  fields.append(
    reviewField("Organization (claim actor)", "text", row.reviewed_organization || row.proposed_organization || "", "organization", row.row_index),
    reviewField("Event year", "number", row.reviewed_year || row.proposed_year || "", "year", row.row_index),
    reviewField("Claim", "textarea", row.reviewed_claim || row.proposed_claim || "", "claim", row.row_index),
    reviewField("Review note or exclusion reason", "textarea", row.review_notes || "", "notes", row.row_index),
  );
  const decision = document.createElement("div");
  decision.className = "field review-decision";
  const label = document.createElement("label");
  const selectId = `reviewDecision-${row.row_index}`;
  label.htmlFor = selectId;
  label.textContent = "Label decision";
  const select = document.createElement("select");
  select.id = selectId;
  select.className = "review-status-select";
  select.dataset.rowField = "review_status";
  select.innerHTML = '<option value="NEEDS_HUMAN_REVIEW">Needs review</option><option value="REVIEWED">Labels checked against source</option><option value="EXCLUDED">Exclude this variant</option>';
  select.value = row.review_status || "NEEDS_HUMAN_REVIEW";
  decision.append(label, select);
  fields.append(decision);
  card.append(heading, input, draft, fields);
  return card;
}

function reviewField(labelText, type, value, field, rowIndex) {
  const wrapper = document.createElement("div");
  wrapper.className = "field" + ((field === "claim" || field === "notes") ? " review-field-wide" : "");
  const controlId = `review-${field}-${rowIndex}`;
  const label = document.createElement("label");
  label.htmlFor = controlId;
  label.textContent = labelText;
  const control = type === "textarea" ? document.createElement("textarea") : document.createElement("input");
  control.id = controlId;
  control.dataset.rowField = field;
  if (type !== "textarea") control.type = type;
  control.value = value;
  if (field === "year") {
    control.min = "1000";
    control.max = "9999";
    control.step = "1";
    control.placeholder = "Blank if unstated";
  } else if (field === "claim") {
    control.rows = 2;
  } else if (field === "notes") {
    control.rows = 2;
    control.placeholder = "Required when excluding a variant";
  }
  wrapper.append(label, control);
  return wrapper;
}

function reviewReuseStatus(value) {
  if (value === "permission_confirmed") return "permission_confirmed";
  if (value === "excluded") return "excluded";
  return "permission_unconfirmed";
}

function updateReviewEvidenceField() {
  const status = $("reviewSourceReuseStatus").value;
  const label = $("reviewSourceEvidenceLabel");
  const field = $("reviewSourceEvidence");
  const isRequired = status !== "permission_unconfirmed";
  label.textContent = status === "excluded" ? "Reason for excluding this source" : "Permission or license evidence";
  field.placeholder = status === "excluded" ? "Why this source cannot be reused" : "e.g. license name and source terms";
  field.required = isRequired;
}

function safeHttpUrl(value) {
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) ? url.href : "";
  } catch { return ""; }
}

function handleReviewGroupChange(event) {
  if (state.reviewPacketDirty && !window.confirm("Discard unsaved changes for this source group?")) {
    event.target.value = state.reviewPacketCurrentGroupId;
    return;
  }
  state.reviewPacketCurrentGroupId = event.target.value;
  state.reviewPacketDirty = false;
  const group = state.reviewPacket.groups.find((item) => item.group_id === event.target.value);
  if (group) renderReviewGroup(group);
}

function handleReviewYearChange(event) {
  if (state.reviewPacketDirty && !window.confirm("Discard unsaved changes for this source group?")) {
    event.target.value = state.reviewPacketYear;
    return;
  }
  state.reviewPacketYear = event.target.value || "all";
  state.reviewPacketDirty = false;
  renderCandidateReviewPacket();
}

function moveReviewGroup(offset) {
  if (state.reviewPacketDirty && !window.confirm("Discard unsaved changes for this source group?")) return;
  const groups = candidateReviewGroupsForYear(state.reviewPacket?.groups || [], state.reviewPacketYear);
  const index = groups.findIndex((group) => group.group_id === state.reviewPacketCurrentGroupId);
  const start = index < 0 ? 0 : index;
  const next = groups[(start + offset + groups.length) % groups.length];
  if (next) {
    state.reviewPacketCurrentGroupId = next.group_id;
    $("reviewPacketGroup").value = next.group_id;
    state.reviewPacketDirty = false;
    renderReviewGroup(next);
  }
}

function moveToNextUnreviewedGroup() {
  if (state.reviewPacketDirty && !window.confirm("Discard unsaved changes for this source group?")) return;
  const groups = candidateReviewGroupsForYear(state.reviewPacket?.groups || [], state.reviewPacketYear);
  if (!groups.length) return;
  const currentIndex = groups.findIndex((group) => group.group_id === state.reviewPacketCurrentGroupId);
  const ordered = currentIndex < 0
    ? groups
    : groups.slice(currentIndex + 1).concat(groups.slice(0, currentIndex + 1));
  const next = ordered.find((group) => group.rows.some((row) => row.review_status !== "REVIEWED" && row.review_status !== "EXCLUDED"));
  if (!next) {
    const scope = state.reviewPacketYear === "all" ? "Every candidate row" : "Every candidate row for " + state.reviewPacketYear;
    return showToast(scope + " has a label decision.", "info");
  }
  state.reviewPacketCurrentGroupId = next.group_id;
  $("reviewPacketGroup").value = next.group_id;
  state.reviewPacketDirty = false;
  renderReviewGroup(next);
}

async function handleSaveCandidateReview(event) {
  event.preventDefault();
  if (state.reviewPacketSaving) return;
  const group = state.reviewPacket?.groups.find((item) => item.group_id === state.reviewPacketCurrentGroupId);
  if (!group) return;
  const reuseStatus = $("reviewSourceReuseStatus").value;
  const reuseEvidence = $("reviewSourceEvidence").value.trim();
  if (reuseStatus !== "permission_unconfirmed" && !reuseEvidence) {
    $("reviewSourceEvidence").focus();
    return showToast("Add permission evidence or an exclusion reason.", "error");
  }
  const rows = [...$("reviewPacketRows").querySelectorAll(".review-row")].map((card) => {
    const field = (name) => card.querySelector(`[data-row-field="${name}"]`);
    const yearValue = field("year").value.trim();
    return {
      row_index: Number(card.dataset.rowIndex),
      review_status: field("review_status").value,
      reviewed_organization: field("organization").value.trim() || null,
      reviewed_year: yearValue ? Number(yearValue) : null,
      reviewed_claim: field("claim").value.trim() || null,
      review_notes: field("notes").value.trim(),
    };
  });
  if (rows.some((row) => row.review_status === "EXCLUDED" && !row.review_notes)) {
    return showToast("Add a reason before excluding a candidate variant.", "error");
  }

  state.reviewPacketSaving = true;
  $("reviewPacketSave").disabled = true;
  updateReviewExportControls();
  $("reviewPacketSaveStatus").textContent = "Saving review to this machine…";
  try {
    state.reviewPacket = await apiCall("training/review-packet", {
      method: "POST",
      body: JSON.stringify({
        group_id: group.group_id,
        rows,
        reuse_status: reuseStatus,
        reuse_evidence: reuseEvidence,
      }),
    });
    state.reviewPacketDirty = false;
    renderCandidateReviewPacket();
    showToast("Review saved to the local candidate packet.", "success");
  } catch (error) {
    $("reviewPacketSaveStatus").textContent = "Could not save: " + error.message;
    showToast("Could not save this source group: " + error.message, "error");
  } finally {
    state.reviewPacketSaving = false;
    $("reviewPacketSave").disabled = false;
    updateReviewExportControls();
  }
}

async function handleExportReviewedDataset() {
  if (state.reviewPacketDirty || state.reviewPacketSaving || state.reviewPacketExporting) {
    return showToast("Save the current source-group review before exporting.", "error");
  }
  const datasetId = $("reviewExportDatasetId").value.trim();
  const reviewerRole = $("reviewExportReviewerRole").value.trim();
  const cohortMode = $("reviewExportCohort").value || "all_eligible";
  if (!/^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/.test(datasetId)) {
    $("reviewExportDatasetId").focus();
    return showToast("Use a valid dataset ID.", "error");
  }
  if (!reviewerRole || reviewerRole.length > 128) {
    $("reviewExportReviewerRole").focus();
    return showToast("Enter the reviewer role, not a personal name.", "error");
  }

  state.reviewPacketExporting = true;
  $("reviewExportResult").textContent = "Checking reviewed rows, source permissions, and held-out split sizes…";
  updateReviewExportControls();
  try {
    const result = await apiCall("training/review-packet/export", {
      method: "POST",
      body: JSON.stringify({ dataset_id: datasetId, reviewer_role: reviewerRole, cohort_mode: cohortMode }),
    });
    await loadInitialData();
    $("fineTuneDataset").value = result.dataset_id;
    updateFineTuneDatasetNote();
    const validation = result.splits.validation;
    const finalTest = result.splits.test;
    const cohortSummary = result.cohort?.mode === "balanced_year_12"
      ? ` Year-balanced, host-diverse pilot selected ${Object.entries(result.cohort.selected_groups_by_year).map(([year, count]) => `${year}: ${count}`).join(", ")} source groups (seed ${result.cohort.selection_seed}). Distinct normalized source hosts by year: ${Object.entries(result.cohort.selected_source_hosts_by_year || {}).map(([year, count]) => `${year}: ${count}`).join(", ")}.`
      : " All eligible groups were included.";
    $("reviewExportResult").textContent = `Created private dataset ${result.dataset_id}: ${result.examples} examples / ${result.source_groups} groups.${cohortSummary} Validation ${validation.examples}/${validation.source_groups} groups; final test ${finalTest.examples}/${finalTest.source_groups} groups. The self-attested card is ready; no model was trained and the test set was not scored.`;
    showToast("Reviewed dataset and benchmark card created locally.", "success");
  } catch (error) {
    $("reviewExportResult").textContent = "Export not created: " + error.message;
    showToast("Could not export reviewed data: " + error.message, "error");
  } finally {
    state.reviewPacketExporting = false;
    updateReviewExportControls();
  }
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
  const benchmarkReady = Boolean(dataset.benchmark?.validation_ready && dataset.benchmark?.final_test_ready);
  status.className = "dataset-quality-status" + (dataset.error || !benchmarkReady ? " is-warning" : " is-ready");
  status.textContent = dataset.error ? "Needs repair" : benchmarkReady ? "Review card complete" : dataset.synthetic ? "Demo only" : dataset.benchmark?.card_ready ? "Split too small" : "Training ready";
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
  const splitMethod = dataset.split_strategy === "group-year-stratified-v1"
    ? "event-year stratified by source group"
    : "deterministic source-group split";
  validation.textContent = `Schema validated · ${splitMethod} · seed ${dataset.split_seed ?? 42}; source variants stay together`;
  container.append(validation);

  const benchmark = dataset.benchmark || {};
  const benchmarkNote = document.createElement("p");
  benchmarkNote.className = "dataset-validation-note";
  if (benchmark.card_ready && benchmark.validation_ready && benchmark.final_test_ready) {
    benchmarkNote.textContent = `Review metadata matches this dataset hash. Review is self-attested; PromptMesh cannot verify label quality. Validation: ${benchmark.validation_examples} examples / ${benchmark.validation_source_groups} groups. Final test: ${benchmark.final_test_examples} examples / ${benchmark.final_test_source_groups} groups.`;
  } else if (benchmark.card_ready) {
    benchmarkNote.textContent = `Review metadata matches this dataset hash, but selection and final scoring require at least ${benchmark.minimum_final_test_examples || 30} examples across ${benchmark.minimum_final_test_groups || 10} source groups in both validation and final test. Review is self-attested.`;
  } else {
    benchmarkNote.textContent = "Final benchmark unavailable · " + (benchmark.reason || "Add a matching review card; review status is self-attested.");
  }
  container.append(benchmarkNote);

  const splitList = document.createElement("div");
  splitList.className = "dataset-split-list";
  [["Train", splits.train], ["Validation", splits.validation], ["Final test (reserved)", splits.test]].forEach(([label, value]) => {
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
  updateBenchmarkControls();
}

function updateFineTuneSubmit() {
  const dataset = state.trainingDatasets.find((item) => item.id === $("fineTuneDataset").value);
  $("fineTuneSubmit").disabled = state.jobBusy || !state.trainingRuntime?.available || !dataset || Boolean(dataset.error);
  updateBenchmarkControls();
}

async function loadSavedAdapters() {
  try {
    const result = await apiCall("training/adapters");
    state.trainedAdapters = result.adapters || [];
    renderSavedAdapters();
  } catch {
    state.trainedAdapters = [];
    $("savedAdapters").hidden = true;
    updateBenchmarkControls();
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
    const metricLabel = adapter.metrics_split === "validation" ? "validation exact match " : "legacy test metric (previously exposed) ";
    const provenance = adapter.dataset_id === "entity_extraction_demo" ? " · synthetic demo · workflow only" : "";
    copy.innerHTML = "<strong>" + escapeHTML(adapter.dataset_id) + "</strong><span>" + escapeHTML(adapter.id + fingerprint) + " · " + metricLabel + formatPercent(adapter.metrics?.record_exact_match) + escapeHTML(provenance) + "</span>";
    const runtime = document.createElement("span");
    runtime.textContent = runtimeSummary(adapter.environment) || "Runtime versions not recorded (legacy run)";
    runtime.title = runtimeDetails(adapter.environment);
    copy.append(runtime);
    const configuration = document.createElement("div");
    configuration.innerHTML = trainingConfigurationMarkup(adapter.training_configuration)
      || '<p class="training-configuration-missing">Full trainer settings were not recorded for this run.</p>';
    copy.append(configuration);
    const button = document.createElement("button");
    button.className = "button button-secondary";
    button.type = "button";
    button.dataset.model = adapter.id;
    button.textContent = "Evaluate";
    row.append(copy, button);
    list.append(row);
  });
  updateBenchmarkControls();
}

function updateBenchmarkControls() {
  const select = $("benchmarkAdapter");
  if (!select) return;
  const dataset = state.trainingDatasets.find((item) => item.id === $("fineTuneDataset").value);
  const previous = select.value;
  select.replaceChildren(new Option("Select a validation adapter", ""));
  const compatible = state.trainedAdapters.filter((adapter) =>
    dataset && adapter.dataset_id === dataset.id && adapter.dataset_sha256 === dataset.sha256 && adapter.metrics_split === "validation" && adapter.benchmark_manifest_ready
  );
  compatible.forEach((adapter) => {
    const provenance = adapter.dataset_id === "entity_extraction_demo" ? " · synthetic demo · workflow only" : "";
    select.add(new Option(adapter.run_id + " · validation exact match " + formatPercent(adapter.metrics?.record_exact_match) + provenance, adapter.run_id));
  });
  if (compatible.some((adapter) => adapter.run_id === previous)) select.value = previous;
  else if (compatible.length === 1) select.value = compatible[0].run_id;
  select.disabled = !compatible.length || state.jobBusy;
  $("benchmarkCandidatePrompt").disabled = state.jobBusy;

  const note = $("benchmarkWorkflowNote");
  const candidate = $("benchmarkCandidatePrompt").value.trim();
  const cardReady = Boolean(dataset?.benchmark?.card_ready);
  const validationReady = Boolean(dataset?.benchmark?.validation_ready);
  const testReady = Boolean(dataset?.benchmark?.final_test_ready);
  const selectionMatches = Boolean(
    state.lastPromptSelection && dataset &&
    state.lastPromptSelection.dataset_id === dataset.id &&
    state.lastPromptSelection.dataset_sha256 === dataset.sha256 &&
    state.lastPromptSelection.adapter_run_id === select.value
  );
  if (!dataset) note.textContent = "Choose a local dataset to check benchmark readiness.";
  else if (dataset.synthetic) note.textContent = "Synthetic demo data cannot be used for prompt selection or a final benchmark.";
  else if (!cardReady) note.textContent = dataset.benchmark?.reason || "A matching review card is required; review status is self-attested.";
  else if (!validationReady || !testReady) note.textContent = "Validation selection and final scoring each require at least 30 examples across 10 source groups.";
  else if (!compatible.length) note.textContent = "Train a validation-scored LoRA adapter on this exact dataset fingerprint first.";
  else if (selectionMatches && state.lastBenchmarkReport?.dataset_sha256 === dataset.sha256) note.textContent = "A frozen report already exists for this dataset version; another test sweep is blocked.";
  else if (selectionMatches) note.textContent = "Prompt selected on validation. Run the frozen comparison once to score the reserved test set. Review metadata is self-attested.";
  else note.textContent = "Selection uses validation labels only; final-test results stay hidden until the frozen comparison. Review metadata is self-attested.";

  const promptValid = /\{\{\s*text\s*\}\}/.test(candidate);
  const finalAlreadyRun = state.lastBenchmarkReport?.dataset_sha256 === dataset?.sha256;
  const quantization = state.quantizationRuntime || {};
  const supportedMethods = new Set((quantization.methods || []).map((method) => method.id));
  document.querySelectorAll('input[name="quantizationMethods"]').forEach((input) => {
    input.disabled = state.jobBusy || finalAlreadyRun || !quantization.available || !supportedMethods.has(input.value);
  });
  const quantizationNote = $("quantizationRuntimeNote");
  if (!quantization.available) {
    quantizationNote.textContent = quantization.reason || "Optional local quantization backends are unavailable in this environment.";
  } else {
    const backends = Object.entries(quantization.backends || {})
      .map(([name, version]) => name + " " + version)
      .join(" · ") || ((quantization.backend || "Quantization backend") + " " + (quantization.version || ""));
    quantizationNote.textContent = backends + " · " + quantization.device + ". Select methods before the final test run.";
  }
  $("promptSelectionSubmit").disabled = state.jobBusy || !state.trainingRuntime?.available || !cardReady || !validationReady || !testReady || !compatible.length || !promptValid || finalAlreadyRun;
  $("runFrozenBenchmarkBtn").disabled = state.jobBusy || !state.trainingRuntime?.available || !selectionMatches || !validationReady || !testReady || finalAlreadyRun;
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

async function handlePromptSelection(event) {
  event.preventDefault();
  if (state.jobBusy) return showToast("Wait for the current local model run to finish.", "warning");
  const dataset = $("fineTuneDataset").value;
  const adapterRunId = $("benchmarkAdapter").value;
  const candidate = $("benchmarkCandidatePrompt").value.trim();
  if (!dataset || !adapterRunId) return showToast("Choose a reviewed dataset and matching validation adapter.", "error");
  if (!/\{\{\s*text\s*\}\}/.test(candidate)) return showToast("The candidate prompt must include {{text}}.", "error");
  state.jobBusy = true;
  setExperimentButtonsDisabled(true);
  try {
    const result = await apiCall("training/prompt-selections", {
      method: "POST",
      body: JSON.stringify({ dataset_id: dataset, adapter_run_id: adapterRunId, candidate_prompts: [candidate] })
    });
    if (!result.job_id) throw new Error("The API did not return a prompt-selection job ID.");
    startPolling(result.job_id, "promptSelection");
  } catch (error) {
    state.jobBusy = false;
    setExperimentButtonsDisabled(false);
    showToast("Could not start validation prompt selection: " + error.message, "error");
  }
}

async function handleFrozenBenchmark() {
  if (state.jobBusy) return showToast("Wait for the current local model run to finish.", "warning");
  if (!state.lastPromptSelection?.selection_id) return showToast("Select a prompt on validation first.", "error");
  state.jobBusy = true;
  setExperimentButtonsDisabled(true);
  try {
    const result = await apiCall("training/benchmarks", {
      method: "POST",
      body: JSON.stringify({
        selection_id: state.lastPromptSelection.selection_id,
        adapter_run_id: state.lastPromptSelection.adapter_run_id,
        quantization_methods: Array.from(document.querySelectorAll('input[name="quantizationMethods"]:checked'), (input) => input.value)
      })
    });
    if (!result.job_id) throw new Error("The API did not return a frozen benchmark job ID.");
    startPolling(result.job_id, "frozenBenchmark");
  } catch (error) {
    state.jobBusy = false;
    setExperimentButtonsDisabled(false);
    showToast("Could not start the frozen benchmark: " + error.message, "error");
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

function updateBackgroundJobStatus() {
  const job = state.backgroundJob;
  const button = $("backgroundJobStatus");
  if (!job || !canRunInBackground(job.type)) { button.hidden = true; return; }
  const label = ({ training: "LoRA", evolution: "Evolution", promptSelection: "Prompt selection", frozenBenchmark: "Benchmark" })[job.type] || "Model job";
  const descriptions = {
    running: [label + " " + Math.round(job.progress || 0) + "%", "in progress. Select to view progress."],
    paused: [label + " status paused", "updates paused. Select to retry."],
    completed: [label + " complete", "completed. Select to view results."],
    failed: [label + " failed", "failed. Select to view the error."]
  };
  const [text, detail] = descriptions[job.status] || descriptions.running;
  $("backgroundJobStatusText").textContent = text;
  button.dataset.status = job.status;
  button.setAttribute("aria-label", label + " " + detail);
  button.title = button.getAttribute("aria-label");
  button.hidden = false;
}

function setBackgroundJobStatus(type, status, message) {
  if (state.backgroundJob?.type !== type) return;
  state.backgroundJob.status = status;
  state.backgroundJob.message = message;
  updateBackgroundJobStatus();
}

function openBackgroundJob() {
  const job = state.backgroundJob;
  if (!job) return;
  if (job.status === "running") return showProgressModal(job.type);
  if (job.status === "paused") return startPolling(job.jobId, job.type);
  if (job.status === "failed") {
    state.backgroundJob = null;
    updateBackgroundJobStatus();
    showToast(job.message || "The background job failed.", "error");
    return;
  }
  const tab = ["training", "promptSelection", "frozenBenchmark"].includes(job.type) ? "finetune" : "evolve";
  state.backgroundJob = null;
  updateBackgroundJobStatus();
  activateTab(tab, true);
  const target = job.type === "promptSelection" ? "promptSelectionResults" : job.type === "frozenBenchmark" ? "frozenBenchmarkResults" : tab === "finetune" ? "fineTuneResults" : "evolveResults";
  $(target).scrollIntoView({ behavior: "smooth", block: "start" });
}

function startPolling(jobId, type) {
  clearInterval(state.pollingTimer);
  state.jobBusy = true;
  setExperimentButtonsDisabled(true);
  if (canRunInBackground(type)) {
    const previous = state.backgroundJob?.jobId === jobId ? state.backgroundJob : null;
    state.backgroundJob = { jobId, type, status: "running", progress: previous?.progress || 0, stage: previous?.stage || null, message: previous?.message || "" };
    updateBackgroundJobStatus();
  }
  showProgressModal(type);
  let polls = 0;
  const maxPolls = ["training", "promptSelection", "frozenBenchmark"].includes(type) ? 1800 : 150;
  state.pollingTimer = window.setInterval(async () => {
    polls += 1;
    if (polls > maxPolls) {
      setBackgroundJobStatus(type, "paused", "Progress updates timed out. Select the status chip to retry.");
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
            setBackgroundJobStatus(type, "failed", "Training completed without an adapter result.");
            showToast("Training completed without an adapter result.", "warning");
            return;
          }
          displayFineTuneRun(job.result);
          setBackgroundJobStatus(type, "completed", "Local adapter training completed.");
          await loadInitialData();
          showToast("Local LoRA training completed. Results are ready in Fine-tune.", "success");
          return;
        }
        if (type === "promptSelection") {
          if (!job.result?.selection_id) {
            setBackgroundJobStatus(type, "failed", "Prompt selection completed without a saved result.");
            showToast("Prompt selection completed without a saved result.", "warning");
            return;
          }
          displayPromptSelection(job.result);
          setBackgroundJobStatus(type, "completed", "Validation prompt selection completed.");
          showToast("Prompt selected using validation labels. The final test remains untouched.", "success");
          return;
        }
        if (type === "frozenBenchmark") {
          if (!job.result?.report) {
            setBackgroundJobStatus(type, "failed", "Benchmark completed without a report.");
            showToast("Benchmark completed without a report.", "warning");
            return;
          }
          displayFrozenBenchmark(job.result.report, job.result.created);
          setBackgroundJobStatus(type, "completed", "Frozen benchmark report saved.");
          showToast("Frozen benchmark report is ready in Fine-tune.", "success");
          return;
        }
        const hasResults = Array.isArray(job.results)
          ? job.results.length > 0
          : type === "evolution" && Array.isArray(job.results?.history) && job.results.history.length > 0;
        if (!hasResults) {
          setBackgroundJobStatus(type, "failed", "The job completed without results.");
          showToast("The job completed without results.", "warning");
          return;
        }
        handleJobResult(type, job.results, type !== "evolution");
        addToHistory(jobId, type, job);
        if (type === "evolution") {
          setBackgroundJobStatus(type, "completed", "Prompt evolution completed.");
          showToast("Prompt evolution completed. Results are ready in Prompt evolution.", "success");
        } else showToast("Run completed.", "success");
      } else if (job.status === "failed") {
        setBackgroundJobStatus(type, "failed", job.error || "The run failed.");
        stopPolling();
        showToast("The run failed: " + (job.error || "No error details were returned."), "error");
      }
    } catch (error) {
      setBackgroundJobStatus(type, "paused", "Progress could not be retrieved. Select the status chip to retry.");
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
  const labels = { evaluation: "Running model evaluation", comparison: "Comparing prompt versions", evolution: "Evolving the prompt", training: "Training a local LoRA adapter", promptSelection: "Selecting a prompt on validation", frozenBenchmark: "Running the frozen benchmark" };
  $("progressTitle").textContent = labels[type] || "Running your job";
  const backgroundJob = state.backgroundJob?.type === type && state.backgroundJob.status === "running" ? state.backgroundJob : null;
  $("progressText").textContent = backgroundJob?.message || (type === "training" ? "Loading the local base model and preparing validation metrics." : type === "promptSelection" ? "Comparing prompt candidates with gold labels on validation data." : type === "frozenBenchmark" ? "Scoring the untouched test split with the frozen configuration." : "The API is waiting for model responses.");
  $("progressFootnote").textContent = canRunInBackground(type) ? "You can navigate elsewhere in PromptMesh. Keep this browser tab open for progress updates." : "You can keep this tab open while the models respond.";
  $("progressFill").style.width = (backgroundJob?.progress || 0) + "%";
  $("progressBackgroundBtn").hidden = !canRunInBackground(type);
  if (!$("progressModal").open) $("progressModal").showModal();
}

function updateProgress(percent, status, stage) {
  const amount = Number(percent);
  const progress = Number.isFinite(amount) ? Math.max(0, Math.min(amount, 100)) : 0;
  $("progressFill").style.width = progress + "%";
  const labels = {
    loading_model: "Loading the base model on this machine.",
    evaluating_base: "Scoring the base model on validation examples.",
    training: "Training LoRA weights and measuring validation loss.",
    evaluating_adapter: "Scoring the adapter on the same validation examples.",
    loading_local_model: "Loading the cached local checkpoint; network downloads are disabled.",
    scoring_validation_prompt: "Scoring candidate prompts on validation labels only.",
    loading_local_base_model: "Loading the pinned local base checkpoint.",
    scoring_frozen_test: "Scoring the reserved test split with the frozen prompt.",
    scoring_frozen_adapter: "Scoring the same reserved examples with the selected LoRA adapter.",
    completed: "Training is complete; final-test examples remain reserved."
  };
  const message = labels[stage] || (status === "running" ? "Models are processing the selected inputs." : (status || "Working…"));
  $("progressText").textContent = message;
  if (state.backgroundJob?.status === "running") {
    state.backgroundJob.progress = progress;
    state.backgroundJob.stage = stage;
    state.backgroundJob.message = message;
    updateBackgroundJobStatus();
  }
}

function handleJobResult(type, results, navigate = true) {
  if (type === "evaluation") { state.lastEvaluationResults = results; displayEvaluation(results); activateTab("evaluate", true); }
  if (type === "comparison") { state.lastComparisonResults = results; displayComparison(results); activateTab("compare", true); }
  if (type === "evolution") { state.lastEvolutionResults = results; displayEvolution(results); if (navigate) activateTab("evolve", true); }
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
  $("evolutionStats").innerHTML = statMarkup("Optimization inputs", results.optimization_input_count ?? "—") + statMarkup("Iterations", Math.max(0, history.length - 1)) + statMarkup("Starting judge score", formatNumber(first)) + statMarkup("Judge score change", delta);
  $("evolutionTimeline").innerHTML = history.map((item, index) => "<article class=\"evolution-item\"><span>Iteration " + escapeHTML(item.iteration ?? index) + "</span><pre>" + escapeHTML(item.prompt || "No prompt text was returned.") + "</pre><strong>" + formatNumber(item.score) + "</strong></article>").join("");
}

function displayFineTuneRun(result) {
  state.activeAdapterModel = result.model_id;
  const splits = result.split_counts || {};
  const base = result.metrics?.base || {};
  const adapter = result.metrics?.adapter || {};
  const fingerprint = result.dataset_sha256 ? " · data " + result.dataset_sha256.slice(0, 12) : "";
  const provenance = result.dataset_id === "entity_extraction_demo" ? " · synthetic demo · workflow evidence only, not model-quality evidence" : "";
  $("fineTuneResults").hidden = false;
  $("fineTuneSummary").textContent = result.dataset_id + fingerprint + provenance + " · " + (splits.validation || 0) + " validation examples scored · final test reserved · " + (result.elapsed_seconds || 0) + " seconds";
  $("fineTuneStats").innerHTML = statMarkup("Base checkpoint", result.base_model)
    + statMarkup("Adapter", result.model_id)
    + statMarkup("Training examples", splits.train || 0)
    + statMarkup("Validation examples", splits.validation || 0)
    + statMarkup("Reserved final-test examples", splits.test || 0)
    + statMarkup("Device", result.device || "—");
  $("fineTuneConfiguration").innerHTML = trainingConfigurationMarkup(result.training_configuration);
  $("fineTuneMetrics").innerHTML = [
    trainingMetricMarkup("Record exact match", base.record_exact_match, adapter.record_exact_match),
    trainingMetricMarkup("Field accuracy", base.field_accuracy, adapter.field_accuracy),
    trainingMetricMarkup("Valid JSON", base.json_valid_rate, adapter.json_valid_rate),
    ...["organization", "year", "claim"].map((field) => trainingMetricMarkup(field + " exact", base.field_exact_match?.[field], adapter.field_exact_match?.[field]))
  ].join("");
  renderLossChart(result.training_loss || [], result.validation_loss || []);
}

function trainingConfigurationMarkup(configuration) {
  if (!configuration || configuration.schema_version !== 1
    || !configuration.trainer || !configuration.lora || !configuration.model_load) return "";
  const renderSection = (title, values) => {
    const rows = Object.entries(values).map(([key, value]) => {
      const label = key.replace(/_/g, " ").replace(/\b[a-z]/g, (letter) => letter.toUpperCase());
      const formatted = value === null ? "null"
        : (typeof value === "object" ? JSON.stringify(value) : String(value));
      return "<div><dt>" + escapeHTML(label) + "</dt><dd>" + escapeHTML(formatted) + "</dd></div>";
    }).join("");
    return "<section><h4>" + escapeHTML(title) + "</h4><dl>" + rows + "</dl></section>";
  };
  const loraRank = escapeHTML(configuration.lora.r ?? "—");
  const loraAlpha = escapeHTML(configuration.lora.lora_alpha ?? "—");
  return "<details class=\"training-configuration\"><summary>Reproducibility settings · LoRA rank "
    + loraRank + " · alpha " + loraAlpha + "</summary><div class=\"training-configuration-sections\">"
    + renderSection("Trainer", configuration.trainer)
    + renderSection("LoRA adapter", configuration.lora)
    + renderSection("Model loading", configuration.model_load)
    + "</div></details>";
}

function displayPromptSelection(result) {
  state.lastPromptSelection = result;
  $("promptSelectionResults").hidden = false;
  $("promptSelectionSummary").textContent = result.validation_examples + " validation examples · selected " + result.selected_prompt_id + " · final test not accessed";
  const runtime = $("promptSelectionEnvironment");
  runtime.textContent = "Validation selection: " + (runtimeSummary(result.environment) || "runtime versions not recorded.");
  runtime.title = runtimeDetails(result.environment);
  $("promptSelectionMetrics").innerHTML = (result.candidates || []).map((candidate) => {
    const metrics = candidate.metrics || {};
    return "<article class=\"training-metric\"><span>" + escapeHTML(candidate.id) + "</span><div><small>Record exact match</small><strong>" + formatPercent(metrics.record_exact_match) + "</strong></div><div><small>Field accuracy</small><strong>" + formatPercent(metrics.field_accuracy) + "</strong></div><b>" + formatPercent(metrics.json_valid_rate) + " valid JSON</b></article>";
  }).join("");
  updateBenchmarkControls();
}

function displayFrozenBenchmark(report, created = true) {
  state.lastBenchmarkReport = report;
  const fingerprint = report.dataset_sha256 ? report.dataset_sha256.slice(0, 12) : "—";
  $("frozenBenchmarkResults").hidden = false;
  $("frozenBenchmarkSummary").textContent = (created ? "Saved once" : "Loaded existing frozen report") + " · dataset " + fingerprint + " · selection and adapter were fixed before test scoring.";
  $("frozenBenchmarkStats").innerHTML = statMarkup("Test examples", report.test_examples)
    + statMarkup("Source groups", report.test_source_groups)
    + statMarkup("Pinned base revision", report.base_revision)
    + statMarkup("Device", report.hardware?.device)
    + statMarkup("LoRA adapter", report.adapter_run_id)
    + statMarkup("Dataset SHA-256", fingerprint);
  const runtime = $("frozenBenchmarkEnvironment");
  const environments = [
    ["Training adapter", report.adapter_environment],
    ["Validation selection", report.prompt_selection_environment],
    ["Frozen benchmark", report.environment]
  ];
  runtime.textContent = environments.map(([stage, environment]) => stage + ": " + (runtimeSummary(environment) || "runtime versions not recorded")).join(" · ");
  runtime.title = environments.map(([stage, environment]) => stage + ": " + (runtimeDetails(environment) || "runtime versions not recorded")).join("\n");
  $("frozenBenchmarkConfiguration").innerHTML = trainingConfigurationMarkup(report.adapter_training_configuration);
  const labels = [
    ["Base · extraction/v1", report.metrics?.base_initial_prompt],
    ["Base · validation-selected prompt", report.metrics?.base_validation_selected_prompt],
    ["LoRA · validation-selected prompt", report.metrics?.lora_validation_selected_prompt]
  ];
  const metricCards = labels.map(([label, metrics]) => {
    const exact = formatPercent(metrics?.record_exact_match);
    const interval = metrics?.record_exact_match_95ci;
    const ciText = interval ? formatPercent(interval.lower) + "–" + formatPercent(interval.upper) : "—";
    return "<article class=\"training-metric\"><span>" + escapeHTML(label) + "</span><div><small>Record exact match</small><strong>" + exact + "</strong></div><div><small>Field accuracy</small><strong>" + formatPercent(metrics?.field_accuracy) + "</strong></div><div><small>Valid JSON</small><strong>" + formatPercent(metrics?.json_valid_rate) + "</strong></div><b>95% grouped CI " + escapeHTML(ciText) + "</b>" + pairedDeltaMarkup(metrics) + goldYearSlicesMarkup(metrics?.by_gold_year) + failureAnalysisMarkup(metrics?.failure_analysis) + "</article>";
  }).join("");
  const timingMethod = report.performance?.timing_method || "Timing method not recorded in this report.";
  const timingNote = "<p class=\"benchmark-timing-note\">Timing: " + escapeHTML(timingMethod) + "</p>";
  const quantized = report.quantized_inference;
  if (quantized?.variants?.length) {
    const controlMetrics = report.metrics?.lora_validation_selected_prompt;
    const controlPerformance = report.performance?.lora_full_precision || {};
    const control = quantizationMetricCard("Full-precision LoRA control", controlMetrics, controlPerformance);
    const variants = quantized.variants.map((variant) => {
      const quantDetails = variant.id === "quanto_int8_w8a8"
        ? "8-bit activations · train-split calibration"
        : variant.id === "bnb_nf4" ? "double quantization" : "outlier threshold " + variant.llm_int8_threshold;
      return quantizationMetricCard(
      variant.label + " · " + variant.weight_bits + "-bit · " + quantDetails + " · " + variant.compute_dtype,
      variant.metrics,
      variant
      );
    }).join("");
    const calibration = quantized.calibration;
    const calibrationNote = calibration
      ? "Calibration: " + calibration.examples + " input-only examples from " + calibration.source_groups + " training groups; no labels, validation rows, or test rows were used."
      : "Calibration: not required for bitsandbytes INT8/NF4.";
    const backendVersions = Object.entries(quantized.backend_versions || {})
      .map(([name, version]) => name + " " + version)
      .join(" · ") || (quantized.backend + " " + (quantized.backend_version || ""));
    const memoryNote = report.performance?.memory_note || "Model footprint does not record runtime peak device memory.";
    const note = calibrationNote + " Adapter training: " + quantized.adapter_training_method + " Backends: " + backendVersions + ". " + memoryNote;
    $("frozenBenchmarkMetrics").innerHTML = metricCards
      + timingNote
      + "<div class=\"quantization-report-heading\"><h4>Quantized adapter inference</h4><p>Matched test quality with cold first-request and warm latency measurements. " + escapeHTML(note) + "</p></div>"
      + control + variants;
  } else {
    $("frozenBenchmarkMetrics").innerHTML = timingNote + metricCards;
  }
  updateBenchmarkControls();
}

function runtimeSummary(environment) {
  if (!environment) return "";
  const packages = environment.packages || {};
  const source = typeof environment.source_revision === "string" && environment.source_revision && "code " + environment.source_revision.slice(0, 8)
    + (typeof environment.source_dirty === "boolean" ? (environment.source_dirty ? " (dirty)" : " (clean)") : "");
  return [
    environment.device,
    environment.python_version && "Python " + environment.python_version,
    packages.torch && "torch " + packages.torch,
    packages.transformers && "transformers " + packages.transformers,
    packages.bitsandbytes && "bitsandbytes " + packages.bitsandbytes,
    source
  ].filter(Boolean).join(" · ");
}

function runtimeDetails(environment) {
  if (!environment) return "";
  const packages = Object.entries(environment.packages || {}).map(([name, version]) => name + " " + (version || "not installed"));
  const source = typeof environment.source_revision === "string" && environment.source_revision
    ? ["source revision " + environment.source_revision, typeof environment.source_dirty === "boolean" && "source tree " + (environment.source_dirty ? "dirty" : "clean")]
    : [];
  return [environment.platform, environment.machine, ...source, ...packages].filter(Boolean).join(" · ");
}

function formatDeltaPoints(value) {
  const points = Number(value) * 100;
  return Number.isFinite(points) ? (points > 0 ? "+" : "") + points.toFixed(1) + " pp" : "—";
}

function pairedDeltaMarkup(metrics) {
  const delta = metrics?.paired_record_exact_match_delta_95ci;
  if (!delta) return "";
  const interval = formatDeltaPoints(delta.lower) + " to " + formatDeltaPoints(delta.upper);
  return "<div><small>Paired source-group exact-match Δ vs " + escapeHTML(delta.reference || "reference") + " · 95% CI</small><strong>"
    + escapeHTML(formatDeltaPoints(delta.estimate)) + " (" + escapeHTML(interval) + ")</strong></div>";
}

function goldYearSlicesMarkup(slices) {
  const entries = Object.entries(slices || {}).sort(([left], [right]) => {
    if (left === "undated") return 1;
    if (right === "undated") return -1;
    return Number(left) - Number(right);
  });
  if (!entries.length) return "";
  const rows = entries.map(([year, metrics]) => {
    const interval = metrics.record_exact_match_95ci;
    const ciText = interval
      ? formatPercent(interval.lower) + "–" + formatPercent(interval.upper)
      : "unavailable (<2 groups)";
    const fields = metrics.field_exact_match || {};
    return "<div class=\"gold-year-slice\"><strong>" + escapeHTML(year) + "</strong><span>" + escapeHTML(metrics.source_groups) + " source groups · " + escapeHTML(metrics.examples) + " examples</span><span>Exact match " + formatPercent(metrics.record_exact_match) + " · 95% group CI " + escapeHTML(ciText) + "</span><span>Organization " + formatPercent(fields.organization) + " · Year " + formatPercent(fields.year) + " · Claim " + formatPercent(fields.claim) + "</span><span>Field accuracy " + formatPercent(metrics.field_accuracy) + " · Valid JSON " + formatPercent(metrics.json_valid_rate) + "</span></div>";
  }).join("");
  return "<details class=\"gold-year-slices\"><summary>Test results by gold year</summary><div class=\"gold-year-slice-list\"><p class=\"gold-year-slice-note\">Group counts are per year slice; a source with multiple event years may appear more than once.</p>" + rows + "</div></details>";
}

function failureAnalysisMarkup(analysis) {
  if (!analysis || !Number.isInteger(analysis.examples) || !Number.isInteger(analysis.failed_examples)) return "";
  const count = (value) => Number.isInteger(value) && value >= 0 ? String(value) : "—";
  const entries = Object.entries(analysis.by_gold_year || {}).sort(([left], [right]) => {
    if (left === "undated") return 1;
    if (right === "undated") return -1;
    return Number(left) - Number(right);
  });
  const rows = [["All years", analysis], ...entries];
  const tableRows = rows.map(([slice, values]) => {
    const fields = values.field_mismatch_examples || {};
    const label = slice === "All years" ? slice : "Gold year " + slice;
    return "<tr><th scope=\"row\">" + escapeHTML(label) + "</th><td>" + count(values.examples)
      + "</td><td>" + count(values.source_groups) + "</td><td>" + count(values.failed_examples)
      + "</td><td>" + count(values.failed_source_groups) + "</td><td>" + count(values.invalid_json_examples)
      + "</td><td>" + count(values.invalid_schema_examples) + "</td><td>" + count(fields.organization)
      + "</td><td>" + count(fields.year) + "</td><td>" + count(fields.claim) + "</td></tr>";
  }).join("");
  return "<details class=\"failure-analysis\"><summary>Failure analysis · " + count(analysis.failed_examples)
    + " of " + count(analysis.examples) + " examples with at least one error</summary>"
    + "<p class=\"failure-analysis-note\">Counts can overlap; invalid JSON or schema outputs count as mismatches for every field. Only aggregate counts are saved—source text and generated answers are not retained.</p>"
    + "<div class=\"failure-analysis-table-wrap\" role=\"region\" aria-label=\"Aggregate failure counts by gold year\" tabindex=\"0\">"
    + "<table class=\"failure-analysis-table\"><caption>Aggregate failure counts by gold year and total</caption>"
    + "<thead><tr><th scope=\"col\">Slice</th><th scope=\"col\">Examples</th><th scope=\"col\">Source groups</th>"
    + "<th scope=\"col\">Failed</th><th scope=\"col\">Groups with failures</th><th scope=\"col\">Invalid JSON</th>"
    + "<th scope=\"col\">Invalid schema</th><th scope=\"col\">Org mismatches</th>"
    + "<th scope=\"col\">Year mismatches</th><th scope=\"col\">Claim mismatches</th></tr></thead><tbody>"
    + tableRows + "</tbody></table></div></details>";
}

function quantizationMetricCard(label, metrics = {}, performance = {}) {
  const interval = metrics.record_exact_match_95ci;
  const ciText = interval ? formatPercent(interval.lower) + "–" + formatPercent(interval.upper) : "—";
  const footprint = Number.isFinite(Number(performance.model_footprint_bytes))
    ? (Number(performance.model_footprint_bytes) / (1024 ** 3)).toFixed(2) + " GiB"
    : "—";
  const seconds = (value) => Number.isFinite(Number(value)) ? Number(value).toFixed(2) + " s" : "—";
  const gibibytes = (value) => value != null && Number.isFinite(Number(value))
    ? (Number(value) / (1024 ** 3)).toFixed(2) + " GiB" : "—";
  const rate = Number.isFinite(Number(performance.tokens_per_second)) ? Number(performance.tokens_per_second).toFixed(2) + " tok/s" : "—";
  const latency = (label, value) => "<div><small>" + label + "</small><strong>"
    + (value != null && Number.isFinite(Number(value)) ? seconds(value) : "—") + "</strong></div>";
  const deviceMemory = performance.device_memory_status === "cuda_allocator_peak"
    ? "<div><small>CUDA peak allocated</small><strong>" + gibibytes(performance.peak_device_memory_allocated_bytes) + "</strong></div>"
      + "<div><small>CUDA peak reserved</small><strong>" + gibibytes(performance.peak_device_memory_reserved_bytes) + "</strong></div>"
    : performance.device_memory_status === "mps_driver_snapshot"
      ? "<div><small>MPS driver before</small><strong>" + gibibytes(performance.mps_driver_memory_before_bytes) + "</strong></div>"
        + "<div><small>MPS driver after</small><strong>" + gibibytes(performance.mps_driver_memory_after_bytes) + "</strong></div>"
      : "<div><small>Device memory</small><strong>" + (performance.device_memory_status ? "Unavailable" : "Not recorded") + "</strong>"
        + (performance.device_memory_note ? "<small>" + escapeHTML(performance.device_memory_note) + "</small>" : "") + "</div>";
  const calibration = Number.isFinite(performance.calibration_seconds)
    ? "<div><small>Calibration</small><strong>" + seconds(performance.calibration_seconds) + "</strong></div>"
    : "";
  const quantization = Number.isFinite(performance.quantization_seconds)
    ? "<div><small>Quantize + freeze</small><strong>" + seconds(performance.quantization_seconds) + "</strong></div>"
    : "";
  const quantizationTimingNote = quantization
    ? "<p class=\"quantization-timing-note\">Calibration and quantization durations are included in Load time; do not add them again.</p>"
    : "";
  return "<article class=\"training-metric\"><span>" + escapeHTML(label) + "</span>"
    + "<div><small>Record exact match</small><strong>" + formatPercent(metrics.record_exact_match) + "</strong></div>"
    + "<div><small>Field accuracy</small><strong>" + formatPercent(metrics.field_accuracy) + "</strong></div>"
    + "<div><small>Valid JSON</small><strong>" + formatPercent(metrics.json_valid_rate) + "</strong></div>"
    + "<div><small>95% grouped CI</small><strong>" + escapeHTML(ciText) + "</strong></div>"
    + pairedDeltaMarkup(metrics)
    + "<div><small>Load</small><strong>" + seconds(performance.load_seconds) + "</strong></div>"
    + "<div><small>Inference</small><strong>" + seconds(performance.inference_seconds) + "</strong></div>"
    + latency("Cold first request", performance.cold_first_request_seconds)
    + latency("Warm request p50", performance.warm_request_latency_p50_seconds)
    + latency("Warm request p90", performance.warm_request_latency_p90_seconds)
    + "<div><small>Warm requests</small><strong>" + (Number.isInteger(performance.warm_request_count) ? "n=" + performance.warm_request_count : "—") + "</strong></div>"
    + deviceMemory
    + calibration
    + quantization
    + "<div><small>Generation</small><strong>" + rate + "</strong></div>"
    + "<div><small>Model footprint</small><strong>" + footprint + "</strong></div>"
    + goldYearSlicesMarkup(metrics.by_gold_year)
    + failureAnalysisMarkup(metrics.failure_analysis)
    + quantizationTimingNote
    + "</article>";
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
function historyEmptyMarkup(title, description) {
  return '<div class="empty-inline empty-inline--illustrated"><img class="empty-inline__art" src="static/images/promptmesh-companion-thinking.webp" alt="" aria-hidden="true" width="1345" height="1169" loading="lazy"><div><strong>' + escapeHTML(title) + '</strong><p>' + escapeHTML(description) + '</p></div></div>';
}

function renderHistory() {
  const container = $("historyList");
  if (!state.jobHistory.length) {
    container.innerHTML = historyEmptyMarkup("No completed runs", "Evaluation, comparison, and evolution summaries will appear here.");
    return;
  }
  container.innerHTML = state.jobHistory.map((item) => "<div class=\"history-row\"><strong>" + escapeHTML(typeLabel(item.type)) + "</strong><span>" + escapeHTML(formatDate(item.completedAt)) + "</span><span>" + escapeHTML(String(item.count || 0)) + " result" + (item.count === 1 ? "" : "s") + "</span><span class=\"history-score\">" + (item.score === null ? "—" : formatNumber(item.score)) + "</span><button class=\"text-button\" type=\"button\" data-view-job=\"" + escapeHTML(item.id) + "\">Open</button></div>").join("");
  container.querySelectorAll("[data-view-job]").forEach((button) => button.addEventListener("click", () => openHistoryJob(button.dataset.viewJob)));
}

function renderOverviewHistory() {
  const container = $("overviewHistory");
  if (!state.jobHistory.length) {
    container.innerHTML = historyEmptyMarkup("No runs yet", "Your completed evaluations will appear here.");
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
