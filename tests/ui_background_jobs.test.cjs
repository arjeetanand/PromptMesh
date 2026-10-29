const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

function loadApp() {
  const elements = new Map();
  const timers = new Map();
  let nextTimer = 0;
  let jobResponse = {};
  function element(id) {
    if (!elements.has(id)) elements.set(id, {
      hidden: false, open: false, disabled: false, value: "", style: {}, dataset: {},
      textContent: "", title: "", attributes: {}, listeners: {},
      classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
      addEventListener(event, handler) { this.listeners[event] = handler; },
      add(option) { (this.options ||= []).push(option); },
      append(...children) { (this.children ||= []).push(...children); },
      replaceChildren(...children) { this.children = children; this.options = []; },
      setAttribute(name, value) { this.attributes[name] = value; },
      getAttribute(name) { return this.attributes[name] ?? null; },
      focus() { this.focused = true; },
      showModal() { this.open = true; }, close() { this.open = false; }, scrollIntoView() { this.scrolled = true; },
      querySelector() { return element(id + "Submit"); },
      querySelectorAll() { return []; }
    });
    return elements.get(id);
  }
  const window = {
    location: { origin: "http://localhost", hash: "#overview" },
    history: { replaceState(_state, _title, hash) { window.location.hash = hash; } },
    addEventListener() {},
    setInterval(callback) { const id = ++nextTimer; timers.set(id, callback); return id; },
    clearInterval(id) { timers.delete(id); }
  };
  const context = vm.createContext({
    window,
    URL,
    Option: function (text, value) { return { textContent: text, value }; },
    document: { getElementById: element, createElement(tag) { return { ...element("created-" + tag + "-" + elements.size), tagName: tag }; }, querySelectorAll() { return []; }, querySelector() { return null; }, addEventListener() {} },
    clearInterval(id) { timers.delete(id); },
    fetch: async () => ({ ok: true, json: async () => jobResponse })
  });
  const appPath = path.join(__dirname, "..", "static", "app.js");
  vm.runInContext(fs.readFileSync(appPath, "utf8"), context);
  vm.runInContext("setupForms()", context);
  return { context, elements, timers, setJobResponse(response) { jobResponse = response; } };
}

test("candidate source changes are announced to assistive technology", () => {
  const html = fs.readFileSync(path.join(__dirname, "..", "static", "index.html"), "utf8");
  const sourceRegion = html.match(/<div\b[^>]*id="reviewPacketSource"[^>]*>/)?.[0] || "";

  assert.match(sourceRegion, /aria-live="polite"/);
  assert.match(sourceRegion, /aria-atomic="true"/);
});

test("skip link reaches the workspace without redirecting the active app tab", () => {
  const html = fs.readFileSync(path.join(__dirname, "..", "static", "index.html"), "utf8");
  assert.match(html, /<a class="skip-link" href="#workspace">Skip to main content<\/a>/);
  assert.match(html, /<main class="workspace" id="workspace" tabindex="-1">/);

  const { context } = loadApp();
  const activations = [];
  let onHashChange;
  context.activateTab = (tab, updateHash) => activations.push([tab, updateHash]);
  context.window.location.hash = "#finetune";
  context.window.addEventListener = (event, handler) => {
    if (event === "hashchange") onHashChange = handler;
  };
  vm.runInContext("setupNavigation()", context);
  context.window.location.hash = "#workspace";
  onHashChange();

  assert.deepEqual(activations, [["finetune", false]], "an in-page fragment must not redirect to Overview");
  context.window.location.hash = "#evaluate";
  onHashChange();
  assert.deepEqual(activations, [["finetune", false], ["evaluate", false]]);
  context.window.location.hash = "#unknown";
  onHashChange();
  assert.deepEqual(activations, [["finetune", false], ["evaluate", false], ["overview", false]]);
});

test("workspace navigation focuses the selected page heading", () => {
  const html = fs.readFileSync(path.join(__dirname, "..", "static", "index.html"), "utf8");
  const css = fs.readFileSync(path.join(__dirname, "..", "static", "styles.css"), "utf8");
  for (const id of ["overviewTitle", "fineTuneTitle", "evaluateTitle", "compareTitle", "evolveTitle", "testcasesTitle", "historyTitle"]) {
    assert.match(html, new RegExp(`<h1 id="${id}" tabindex="-1">`));
  }
  assert.match(css, /h1\[tabindex="-1"\]:focus-visible/);

  const { context, elements } = loadApp();
  context.document.getElementById("overviewTitle");
  let hashChange;
  const button = {
    dataset: { tab: "finetune" }, textContent: "Fine-tune", listeners: {},
    classList: { toggle() {} },
    addEventListener(event, handler) { this.listeners[event] = handler; },
    setAttribute() {}, removeAttribute() {}
  };
  context.document.querySelectorAll = (selector) => selector === ".nav-btn[data-tab]" ? [button] : [];
  context.document.querySelector = (selector) => selector === '.nav-btn[data-tab="finetune"]' ? button : null;
  context.window.addEventListener = (event, handler) => { if (event === "hashchange") hashChange = handler; };

  vm.runInContext("setupNavigation()", context);
  assert.notEqual(elements.get("overviewTitle").focused, true, "initial route setup should not steal focus");
  button.listeners.click();
  assert.equal(elements.get("fineTuneTitle").focused, true);
  assert.equal(context.window.location.hash, "#finetune");

  context.window.location.hash = "#evaluate";
  hashChange();
  assert.equal(elements.get("evaluateTitle").focused, true, "browser route changes should announce the new page");
});

test("synthetic adapter metrics keep their workflow-only context", () => {
  const { context, elements } = loadApp();
  context.adapterData = JSON.stringify([{
    id: "trained:demo", dataset_id: "entity_extraction_demo", metrics_split: "validation",
    dataset_sha256: "demo-hash", benchmark_manifest_ready: true, run_id: "demo-run",
    metrics: { record_exact_match: 0.5 }
  }]);
  context.modelData = JSON.stringify({ all: ["trained:demo"], fast: [] });
  vm.runInContext("state.trainedAdapters = JSON.parse(adapterData); state.models = JSON.parse(modelData); populateModelSelectors(); renderSavedAdapters()", context);

  assert.match(elements.get("evalModels").children[0].children[1].textContent, /synthetic demo · workflow only/);
  assert.match(elements.get("evolveModel").options[0].textContent, /synthetic demo · workflow only/);
  assert.match(elements.get("savedAdapterList").children[0].children[0].innerHTML, /synthetic demo · workflow only/);
  context.datasetData = JSON.stringify([{ id: "entity_extraction_demo", sha256: "demo-hash", synthetic: true }]);
  vm.runInContext("state.trainingDatasets = JSON.parse(datasetData); $('fineTuneDataset').value = 'entity_extraction_demo'; updateBenchmarkControls()", context);
  assert.match(elements.get("benchmarkAdapter").options[0].textContent, /synthetic demo · workflow only/);

  vm.runInContext("renderLossChart = () => {}; displayFineTuneRun({dataset_id:'entity_extraction_demo', split_counts:{validation:6}, metrics:{}, elapsed_seconds:1})", context);
  assert.match(elements.get("fineTuneSummary").textContent, /synthetic demo · workflow evidence only, not model-quality evidence/);
});

test("candidate review coverage exposes draft year and source-host concentration", () => {
  const { context } = loadApp();
  const groups = [
    { source_url: "https://www.nasa.gov/one", rows: [{ proposed_year: 2024 }] },
    { source_url: "https://nasa.gov/two", rows: [{ proposed_year: 2024 }] },
    { source_url: "https://example.gov/three", rows: [{ proposed_year: 2020 }] },
    { source_url: "https://example.org/four", rows: [{ proposed_year: null }] }
  ];
  context.groups = JSON.stringify(groups);
  const summary = vm.runInContext("candidateReviewCoverage(JSON.parse(groups))", context);

  assert.match(summary, /2020 1 · 2024 2 · undated 1/);
  assert.match(summary, /3 source hosts; most common: nasa.gov 2, example.gov 1, example.org 1/);
  assert.match(summary, /not reviewed benchmark composition/);

  const ordered = [
    { group_id: "2024-a", rows: [{ proposed_year: 2024 }] },
    { group_id: "2024-b", rows: [{ proposed_year: 2024 }] },
    { group_id: "2020-a", rows: [{ proposed_year: 2020 }] },
    { group_id: "2025-a", rows: [{ proposed_year: 2025 }] },
    { group_id: "2021-a", rows: [{ proposed_year: 2021 }] },
    { group_id: "2024-c", rows: [{ proposed_year: 2024 }] }
  ];
  context.orderedGroups = JSON.stringify(ordered);
  const order = JSON.parse(vm.runInContext(
    "JSON.stringify(interleaveCandidateReviewGroups(JSON.parse(orderedGroups)).map((group) => group.group_id))",
    context
  ));
  assert.deepEqual(order, ["2020-a", "2021-a", "2024-a", "2025-a", "2024-b", "2024-c"]);
});

test("reviewed dataset export is gated by saved, benchmark-ready review data", () => {
  const { context, elements } = loadApp();
  context.packet = JSON.stringify({ export_preview: {
    ready: true, examples: 239, source_groups: 80,
    validation_examples: 35, validation_source_groups: 12,
    final_test_examples: 36, final_test_source_groups: 12
  } });
  vm.runInContext("state.reviewPacket = JSON.parse(packet); updateReviewExportControls()", context);

  assert.equal(elements.get("reviewExportButton").disabled, true, "reviewer role is required before export");
  elements.get("reviewExportDatasetId").value = "reviewed_sources_v1";
  elements.get("reviewExportReviewerRole").value = "project author";
  vm.runInContext("updateReviewExportControls()", context);
  assert.equal(elements.get("reviewExportButton").disabled, false);
  assert.match(elements.get("reviewExportReadiness").textContent, /Validation: 35 examples \/ 12 groups/);

  vm.runInContext("state.reviewPacketDirty = true; updateReviewExportControls()", context);
  assert.equal(elements.get("reviewExportButton").disabled, true, "unsaved decisions must not be exported");
});

test("reviewed dataset export creates a local dataset selection without starting a run", async () => {
  const { context, elements } = loadApp();
  elements.get("reviewExportDatasetId").value = "reviewed_sources_v1";
  elements.get("reviewExportReviewerRole").value = "project author";
  vm.runInContext("state.reviewPacket = {export_preview:{ready:true}}; state.reviewPacketDirty = false; loadInitialData = async () => {}; updateFineTuneDatasetNote = () => {}; showToast = () => {}", context);
  let request;
  context.apiCall = async (endpoint, options) => {
    request = { endpoint, options };
    return {
      dataset_id: "reviewed_sources_v1", examples: 239, source_groups: 80,
      splits: {
        validation: { examples: 35, source_groups: 12 },
        test: { examples: 36, source_groups: 12 }
      }
    };
  };

  await vm.runInContext("handleExportReviewedDataset()", context);

  assert.equal(request.endpoint, "training/review-packet/export");
  assert.deepEqual(JSON.parse(request.options.body), { dataset_id: "reviewed_sources_v1", reviewer_role: "project author" });
  assert.equal(elements.get("fineTuneDataset").value, "reviewed_sources_v1");
  assert.match(elements.get("reviewExportResult").textContent, /no model was trained and the test set was not scored/);
  assert.equal(vm.runInContext("state.reviewPacketExporting", context), false);
});

for (const [type, label] of [
  ["training", "LoRA"],
  ["evolution", "Evolution"],
  ["promptSelection", "Prompt selection"],
  ["frozenBenchmark", "Benchmark"]
]) {
  test(`${label} progress can close and reopen while polling stays active`, () => {
    const { context, elements, timers } = loadApp();
    vm.runInContext(`state.backgroundJob = { jobId: "job-1", type: "${type}", status: "paused", progress: 32 }; openBackgroundJob();`, context);
    assert.equal(vm.runInContext("state.jobBusy", context), true);
    assert.equal(elements.get("evaluateFormSubmit").disabled, true);
    assert.equal(elements.get("progressModal").open, true);
    assert.equal(elements.get("backgroundJobStatusText").textContent, `${label} 32%`);

    elements.get("progressBackgroundBtn").listeners.click();
    assert.equal(elements.get("progressModal").open, false);
    assert.equal(timers.size, 1, "closing progress must leave the poll running");

    elements.get("backgroundJobStatus").listeners.click();
    assert.equal(elements.get("progressModal").open, true, "the status button reopens progress");
    assert.equal(elements.get("progressFill").style.width, "32%");
    assert.equal(timers.size, 1, "reopening progress must not start another poll");
  });

  test(`${label} completion stays visible until its results are opened`, async () => {
    const { context, elements, timers, setJobResponse } = loadApp();
    const response = type === "training"
      ? { status: "completed", result: {} }
      : type === "evolution"
        ? { status: "completed", results: { history: [{ score: 1, prompt: "improved" }] } }
        : { status: "completed", result: type === "promptSelection" ? { selection_id: "selection-1" } : { report: { status: "completed" } } };
    setJobResponse(response);
    const setup = type === "training"
      ? "displayFineTuneRun = () => {}; loadInitialData = async () => {};"
      : type === "evolution"
        ? "displayEvolution = () => {}; addToHistory = () => {};"
        : type === "promptSelection" ? "displayPromptSelection = () => {};" : "displayFrozenBenchmark = () => {};";
    vm.runInContext(`showToast = () => {}; ${setup} startPolling("job-1", "${type}");`, context);
    elements.get("progressBackgroundBtn").listeners.click();
    await timers.values().next().value();

    assert.equal(vm.runInContext("state.activeTab", context), "overview", "completion must not change the active page");
    assert.equal(vm.runInContext("state.backgroundJob.status", context), "completed");
    assert.equal(elements.get("backgroundJobStatusText").textContent, `${label} complete`);
    elements.get("backgroundJobStatus").listeners.click();
    assert.equal(vm.runInContext("state.activeTab", context), ["training", "promptSelection", "frozenBenchmark"].includes(type) ? "finetune" : "evolve");
    const target = type === "promptSelection" ? "promptSelectionResults" : type === "frozenBenchmark" ? "frozenBenchmarkResults" : type === "training" ? "fineTuneResults" : "evolveResults";
    assert.equal(elements.get(target).scrolled, true);
  });
}

test("quantized benchmark cards show task metrics, cold/warm latency, and the calibration caveat", () => {
  const { context, elements } = loadApp();
  const report = {
    dataset_sha256: "a".repeat(64),
    test_examples: 30,
    test_source_groups: 10,
    base_revision: "pinned-revision",
    hardware: { device: "mps" },
    adapter_run_id: "adapter-run",
    adapter_environment: { device: "cpu", python_version: "3.11.9", packages: { torch: "2.0.0" } },
    prompt_selection_environment: { device: "cuda", python_version: "3.12.0", packages: { torch: "2.1.0" } },
    metrics: {
      base_initial_prompt: { record_exact_match: 0.1, field_accuracy: 0.2, json_valid_rate: 0.5 },
      base_validation_selected_prompt: {
        record_exact_match: 0.2, field_accuracy: 0.3, json_valid_rate: 0.6,
        paired_record_exact_match_delta_95ci: {
          reference: "Base · extraction/v1", estimate: 0.1, lower: 0.0, upper: 0.2
        }
      },
      lora_validation_selected_prompt: {
        record_exact_match: 0.5, field_accuracy: 0.7, json_valid_rate: 0.9,
        record_exact_match_95ci: { lower: 0.3, upper: 0.7 },
        by_gold_year: {
          "2024": {
            examples: 12, source_groups: 4, record_exact_match: 0.5,
            field_accuracy: 0.7, json_valid_rate: 0.9,
            field_exact_match: { organization: 0.5, year: 1, claim: 0.5 },
            record_exact_match_95ci: { lower: 0.2, upper: 0.8 }
          },
          undated: {
            examples: 1, source_groups: 1, record_exact_match: 0,
            field_accuracy: 0, json_valid_rate: 1, field_exact_match: { organization: 0, year: 0, claim: 0 }, record_exact_match_95ci: null
          }
        },
        paired_record_exact_match_delta_95ci: {
          reference: "Base · validation-selected prompt", estimate: 0.3, lower: 0.1, upper: 0.5
        }
      }
    },
    performance: {
      lora_full_precision: {
        load_seconds: 2, inference_seconds: 3, tokens_per_second: 12, model_footprint_bytes: 800000000,
        cold_first_request_seconds: 2.5, warm_request_latency_p50_seconds: 0.3,
        warm_request_latency_p90_seconds: 0.8, warm_request_count: 30
      },
      timing_method: "Synchronized wall-clock generation on MPS/CUDA; CPU generation is synchronous.",
    },
    environment: { device: "mps", python_version: "3.12.1", platform: "macOS-test", machine: "arm64", packages: { torch: "2.14.1", transformers: "5.1.0", bitsandbytes: "0.50.0" } },
    quantized_inference: {
      backend: "bitsandbytes",
      backend_version: "0.50.0",
      adapter_training_method: "Full-precision LoRA + SFT; this inference comparison is not QLoRA training.",
      variants: [{
        id: "bnb_nf4", label: "bitsandbytes NF4", weight_bits: 4, compute_dtype: "float16",
        metrics: {
          record_exact_match: 0.4, field_accuracy: 0.6, json_valid_rate: 0.8,
          by_gold_year: {
            "2024": { examples: 6, source_groups: 2, record_exact_match: 0.4, field_accuracy: 0.6, json_valid_rate: 0.8, field_exact_match: { organization: 0.3, year: 1, claim: 0.3 }, record_exact_match_95ci: { lower: 0.1, upper: 0.7 } }
          },
          record_exact_match_95ci: { lower: 0.2, upper: 0.6 },
          paired_record_exact_match_delta_95ci: {
            reference: "Full-precision LoRA control", estimate: -0.1, lower: -0.3, upper: 0.1
          } },
        load_seconds: 1, inference_seconds: 4, tokens_per_second: 8, model_footprint_bytes: 400000000,
        cold_first_request_seconds: 3.5, warm_request_latency_p50_seconds: 0.4,
        warm_request_latency_p90_seconds: 0.9, warm_request_count: 30
      }]
    }
  };
  context.report = JSON.stringify(report);
  vm.runInContext("displayFrozenBenchmark(JSON.parse(report))", context);

  const html = elements.get("frozenBenchmarkMetrics").innerHTML;
  assert.match(html, /Quantized adapter inference/);
  assert.match(html, /bitsandbytes NF4 · 4-bit/);
  assert.match(html, /Calibration: not required/);
  assert.match(html, /not QLoRA training/);
  assert.match(html, /Timing: Synchronized wall-clock generation on MPS\/CUDA/);
  assert.match(html, /Matched test quality with cold first-request and warm latency measurements/);
  assert.match(html, /Cold first request/);
  assert.match(html, /Warm request p50/);
  assert.match(html, /Warm request p90/);
  assert.match(html, /n=30/);
  assert.match(html, /3\.50 s/);
  assert.match(html, /0\.40 s/);
  assert.match(html, /0\.90 s/);
  assert.match(html, /Paired source-group exact-match Δ vs Base · validation-selected prompt/);
  assert.match(html, /\+30\.0 pp \(\+10\.0 pp to \+50\.0 pp\)/);
  assert.match(html, /Paired source-group exact-match Δ vs Full-precision LoRA control/);
  assert.match(html, /-10\.0 pp \(-30\.0 pp to \+10\.0 pp\)/);
  assert.match(html, /Test results by gold year/);
  assert.match(html, /4 source groups · 12 examples/);
  assert.match(html, /Organization 50\.0% · Year 100\.0% · Claim 50\.0%/);
  assert.match(html, /2 source groups · 6 examples/);
  assert.match(html, /Group counts are per year slice/);
  assert.match(html, /unavailable \(&lt;2 groups\)/);
  report.quantized_inference.backend = "mixed";
  report.quantized_inference.backend_version = null;
  report.quantized_inference.backend_versions = { bitsandbytes: "0.50.0", "optimum-quanto": "0.2.7" };
  report.quantized_inference.calibration_required = true;
  report.quantized_inference.calibration = { examples: 16, source_groups: 16, split: "train", input_only: true, labels_used: false };
  report.quantized_inference.variants.push({
    id: "quanto_int8_w8a8", label: "Quanto INT8 weights + INT8 activations", weight_bits: 8,
    activation_bits: 8, compute_dtype: "INT8 linear; FP32 remainder", calibration_required: true,
    calibration_seconds: 1.25, quantization_seconds: 0.5,
    metrics: { record_exact_match: 0.4, field_accuracy: 0.6, json_valid_rate: 0.8 },
    load_seconds: 2, inference_seconds: 4, tokens_per_second: 8, model_footprint_bytes: 400000000
  });
  context.report = JSON.stringify(report);
  vm.runInContext("displayFrozenBenchmark(JSON.parse(report))", context);
  const calibratedHtml = elements.get("frozenBenchmarkMetrics").innerHTML;
  assert.match(calibratedHtml, /Quanto INT8 weights \+ INT8 activations · 8-bit · 8-bit activations · train-split calibration/);
  assert.match(calibratedHtml, /Calibration: 16 input-only examples from 16 training groups/);
  assert.match(calibratedHtml, /Calibration<\/small><strong>1\.25 s/);
  assert.match(calibratedHtml, /optimum-quanto 0\.2\.7/);
  delete report.performance.timing_method;
  context.report = JSON.stringify(report);
  vm.runInContext("displayFrozenBenchmark(JSON.parse(report))", context);
  assert.match(elements.get("frozenBenchmarkMetrics").innerHTML, /Timing method not recorded in this report/);
  delete report.quantized_inference;
  context.report = JSON.stringify(report);
  vm.runInContext("displayFrozenBenchmark(JSON.parse(report))", context);
  assert.match(elements.get("frozenBenchmarkMetrics").innerHTML, /Timing method not recorded in this report/);
  assert.match(html, /0\.37 GiB/);
  assert.match(html, /8\.00 tok\/s/);
  assert.equal(vm.runInContext("pairedDeltaMarkup({})", context), "", "legacy reports render without a paired interval");
  assert.match(elements.get("frozenBenchmarkEnvironment").textContent, /Training adapter: cpu · Python 3\.11\.9/);
  assert.match(elements.get("frozenBenchmarkEnvironment").textContent, /Validation selection: cuda · Python 3\.12\.0/);
  assert.match(elements.get("frozenBenchmarkEnvironment").textContent, /Frozen benchmark: mps · Python 3\.12\.1/);
  assert.match(elements.get("frozenBenchmarkEnvironment").title, /macOS-test/);
});

test("prompt selection results show the validation runtime", () => {
  const { context, elements } = loadApp();
  vm.runInContext("displayPromptSelection({validation_examples:30, selected_prompt_id:'candidate-1', environment:{device:'mps',python_version:'3.12.1',packages:{torch:'2.14.1'}}})", context);

  assert.match(elements.get("promptSelectionEnvironment").textContent, /Validation selection: mps · Python 3\.12\.1 · torch 2\.14\.1/);
});

test("runtime labels distinguish missing metadata from measured environments", () => {
  const { context } = loadApp();
  const measured = vm.runInContext("runtimeSummary({device:'mps', python_version:'3.12.1', packages:{torch:'2.14.1', transformers:'5.1.0'}})", context);
  const missing = vm.runInContext("runtimeSummary(null) || 'Runtime versions not recorded (legacy run)'", context);
  const source = vm.runInContext("runtimeSummary({device:'mps', source_revision:'abcdef0123456789', source_dirty:true})", context);
  const details = vm.runInContext("runtimeDetails({platform:'macOS-test', source_revision:'abcdef0123456789', source_dirty:false})", context);

  assert.equal(measured, "mps · Python 3.12.1 · torch 2.14.1 · transformers 5.1.0");
  assert.equal(missing, "Runtime versions not recorded (legacy run)");
  assert.equal(source, "mps · code abcdef01 (dirty)");
  assert.match(details, /source revision abcdef0123456789 · source tree clean/);
});
