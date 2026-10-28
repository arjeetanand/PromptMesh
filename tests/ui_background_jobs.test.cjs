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
      replaceChildren(...children) { this.children = children; this.options = []; },
      setAttribute(name, value) { this.attributes[name] = value; },
      getAttribute(name) { return this.attributes[name] ?? null; },
      showModal() { this.open = true; }, close() { this.open = false; }, scrollIntoView() { this.scrolled = true; },
      querySelector() { return element(id + "Submit"); }
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
    Option: function (text, value) { return { textContent: text, value }; },
    document: { getElementById: element, querySelectorAll() { return []; }, querySelector() { return null; }, addEventListener() {} },
    clearInterval(id) { timers.delete(id); },
    fetch: async () => ({ ok: true, json: async () => jobResponse })
  });
  const appPath = path.join(__dirname, "..", "static", "app.js");
  vm.runInContext(fs.readFileSync(appPath, "utf8"), context);
  vm.runInContext("setupForms()", context);
  return { context, elements, timers, setJobResponse(response) { jobResponse = response; } };
}

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

test("quantized benchmark cards show task metrics, resource measurements, and the calibration caveat", () => {
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
        paired_record_exact_match_delta_95ci: {
          reference: "Base · validation-selected prompt", estimate: 0.3, lower: 0.1, upper: 0.5
        }
      }
    },
    performance: { lora_full_precision: { load_seconds: 2, inference_seconds: 3, tokens_per_second: 12, model_footprint_bytes: 800000000 } },
    environment: { device: "mps", python_version: "3.12.1", platform: "macOS-test", machine: "arm64", packages: { torch: "2.14.1", transformers: "5.1.0", bitsandbytes: "0.50.0" } },
    quantized_inference: {
      backend: "bitsandbytes",
      backend_version: "0.50.0",
      adapter_training_method: "Full-precision LoRA + SFT; this inference comparison is not QLoRA training.",
      variants: [{
        id: "bnb_nf4", label: "bitsandbytes NF4", weight_bits: 4, compute_dtype: "float16",
        metrics: { record_exact_match: 0.4, field_accuracy: 0.6, json_valid_rate: 0.8,
          record_exact_match_95ci: { lower: 0.2, upper: 0.6 },
          paired_record_exact_match_delta_95ci: {
            reference: "Full-precision LoRA control", estimate: -0.1, lower: -0.3, upper: 0.1
          } },
        load_seconds: 1, inference_seconds: 4, tokens_per_second: 8, model_footprint_bytes: 400000000
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
  assert.match(html, /Paired source-group exact-match Δ vs Base · validation-selected prompt/);
  assert.match(html, /\+30\.0 pp \(\+10\.0 pp to \+50\.0 pp\)/);
  assert.match(html, /Paired source-group exact-match Δ vs Full-precision LoRA control/);
  assert.match(html, /-10\.0 pp \(-30\.0 pp to \+10\.0 pp\)/);
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

  assert.equal(measured, "mps · Python 3.12.1 · torch 2.14.1 · transformers 5.1.0");
  assert.equal(missing, "Runtime versions not recorded (legacy run)");
});
