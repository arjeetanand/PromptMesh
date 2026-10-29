# PromptMesh

**PromptMesh** is a **model-agnostic prompt evaluation, comparison, and evolution platform** with a built-in **FastAPI backend and web UI**. It allows you to evaluate prompt versions across multiple LLMs, run controlled experiments, generate test cases, and evolve prompts using an automated feedback loop.

PromptMesh treats prompt engineering as a **system-level workflow** rather than ad-hoc trial and error.

---

## 🚀 Overview

PromptMesh is a **portfolio-stage prompt experimentation workspace** with an integrated API server and web interface.

It enables:

* Programmatic prompt evaluation
* Same-input comparisons across configured models
* Automated test generation
* Prompt evolution with feedback loops
* Real-time job tracking and result inspection
* Local Qwen3-0.6B LoRA/SFT runs for structured entity extraction
* Local inference with saved LoRA adapters
* Keyboard-accessible workspace navigation with focus moved to each selected page heading

All long-running operations execute asynchronously with progress reporting and result persistence in memory.

---

## ✨ Core Capabilities

### 1. Prompt Versioning (YAML-first)

* Versioned prompt templates per task
* Metadata-driven configuration:

  * Input variables
  * Constraints
  * Task type
  * Schema fields

---

### 2. Multi-Model Prompt Evaluation

Evaluate the same prompt across multiple models:

* Local models (Ollama)
* Cloud models (OCI GenAI, Cohere)

Each run captures:

* Output text
* Token usage
* Latency
* Score breakdown

---

### 3. LLM-as-a-Judge Scoring Pipeline

The configured judge model provides heuristic scores for:

* Accuracy
* Completeness
* Instruction adherence
* Hallucination risk

Features:

* Robust JSON extraction
* Graceful parsing fallback
* Structured score breakdowns
* Failed judge requests fail the evaluation instead of receiving substitute scores

These scores are useful for reviewing prompt iterations, not a gold-label benchmark.
Classification and verification use task-specific weights; other task types use
the general completeness-weighted score. The bundled LoRA dataset is synthetic
workflow data. Optional bitsandbytes LLM.int8/NF4 and Quanto W8A8 are available
in the frozen inference comparison when their local runtimes support them.

---

### 4. Prompt Comparison Engine

Compare multiple prompt versions across multiple models:

* Side-by-side scoring
* Ranked leaderboard output
* Per-version performance analysis

---

### 5. Automated Prompt Evolution Engine

PromptMesh supports closed-loop prompt optimization:

* Failure-aware mutation
* Iterative improvement
* Score-based convergence control

Capabilities:

* Automatic failure detection
* Controlled evolution using optimizer model
* Improvement threshold (`min_delta`)
* Iteration limits

---

### 6. Test Case Generation

Automatically generate evaluation datasets:

* Distribution-aware test generation
* Schema-based generation support
* Custom base input expansion

---

## Making model-quality claims

The repository demonstrates prompt evaluation with an LLM judge, local LoRA/SFT
training, and local adapter inference. It does not yet establish model-quality
gains: the demo data is synthetic, and the general evaluation score is a model
judge heuristic. Prompt evolution currently selects revisions using the inputs
supplied to that run, so those inputs are not an independent final test set.
Each LoRA run resolves the cached Hub snapshot commit, loads the base model and
tokenizer in local-only mode at that revision, and records the pin in its
manifest.

The next experiments should use human-reviewed labels and grouped,
versioned train/validation/test splits. Use validation data for prompt evolution
and model selection, keep the final test untouched, and compare the base model,
prompt-only baseline, and LoRA adapter on identical test examples. Report task
metrics with uncertainty alongside latency and memory. A quantized-inference
comparison should use the same frozen test set and declare the hardware/backend.
The optional INT8/NF4/Quanto comparison records quality, calibration provenance
where applicable, latency, generated-token rate, and model footprint beside
the full-precision LoRA control. CUDA reports PyTorch allocator peak allocated
and reserved memory; allocations outside that allocator may be omitted. MPS
reports Metal-driver allocations before and after the pass, including cached
allocations, and labels them as snapshots rather than peaks. CPU has no device
memory measurement. Model footprint remains a separate model-size metric.
New reports synchronize MPS/CUDA around timed
generation and count the generated token IDs directly; CPU timing uses its
synchronous execution. Each freshly loaded model records one cold first request
on the first frozen test input, then one complete scored pass records per-request
warm latency. Reports show the cold request, median warm p50, nearest-rank p90,
and warm request count. The first input is generated twice, while only the
scored pass contributes task metrics. This is one scored pass, not repeated-run
throughput. Human-reviewed
benchmark data and a real quantized report are still required before making
quality or speed claims.
Frozen reports also include paired source-group bootstrap 95% intervals for
record exact-match differences: selected prompt vs. initial prompt, LoRA vs.
the validation-selected base prompt, and each quantized variant vs. full-
precision LoRA. Each resample uses the same sampled source groups in both arms;
the displayed delta is comparison minus reference in percentage points.
New frozen reports also show gold-year test slices for each arm, with example
and source-group counts, record exact match, per-field accuracy, JSON validity,
and source-group confidence intervals when a slice has at least two groups.
Single-group slices display their metrics without an interval. Group counts
are per slice, so a source with claims from multiple event years can appear in
more than one year.
Reports also include per-arm aggregate failure counts for invalid JSON, invalid
schema, and field mismatches, overall and by gold year. Invalid outputs count as
mismatches for every field, so counts can overlap. Reports retain these counts,
not source text or generated answers. Quanto calibration and quantization times
are components of its displayed load time and should not be added to it again.

A local, git-ignored public-source review packet has 423 unreviewed draft rows
in 141 source groups. Each group contains three phrasings of one source claim,
not three independent facts. Proposed years are 2020=14 groups, 2021=16,
2022=15, 2023=15, 2024=65, 2025=15, and one undated.
This is still not a representative benchmark. Every candidate label and reuse
decision remains pending human review, and the packet does not establish
model-quality gains. The current seed-42 draft split projects 297 training rows
across 99 groups and 63 rows across 21 groups in each held-out split. Each
held-out split has proposed-year counts of 2 groups from 2020, 3 from 2021, 2
from 2022, 2 from 2023, 10 from 2024, and 2 from 2025. These unreviewed years
must not be presented as benchmark composition; 2024 accounts for 10 of 21
groups in each held-out projection.

The export form now offers an explicit year-balanced pilot of 12 eligible
groups in each reviewed year from 2020–2025. It selects deterministically from
reviewed years with seed 42 and stores the candidate list and selection in a
schema-v2 benchmark card. With 72 groups and three variants per group, the
current split algorithm projects 150/33/33 rows across 50/11/11
train/validation/test groups. This projection says nothing about the pending
draft labels or reuse rights; the current packet cannot use this option until
each year has 12 fully reviewed, reuse-cleared groups. Year balance alone does
not establish label quality, reuse permission, or representativeness.

For datasets with at least 30 source groups, the split keeps each group intact
and stratifies by its event-year signature. Signatures with at least three
groups contribute one group to validation and one to test; remaining held-out
groups are allocated toward 15% per split. Sparse signatures remain in training.
Smaller datasets use the deterministic group-hash split. Both policies use seed
42 and are recorded in adapter, selection, and benchmark provenance. This
controls year coverage, not organization, topic, or source-type balance.

PromptMesh stores SHA-256 fingerprints of final-test source-group IDs and
normalized input text in a private local registry. Before training, validation
selection, or another final run, it blocks any previously tested identity from
entering train/validation or a later test set, even under a new dataset ID.
Keep source-group IDs stable across versions; whitespace- and case-normalized
exact input matches also catch re-exports with renamed groups. This does not
detect paraphrases whose IDs and wording both change. Older reservations are
indexed only when their original dataset snapshot still matches; otherwise the
gate fails closed.

Open **Fine-tune → Review source candidates** to review one source group at a
time. Compare every phrasing with its linked source, edit the labels, and record
reuse permission separately with its evidence. The queue is loopback-only and
saves reviews to the ignored local CSV. Once enough groups are fully resolved
and have confirmed reuse evidence, **Build a reviewed dataset** exports only
reviewed variants to an ignored JSONL and creates a matching, self-attested
benchmark card with source references. Both validation and final test must meet
the 30-example / 10-source-group floor. Export does not train a model or score
the test set; human label and rights review remain local self-attestations. The
queue summarizes draft year and source-host coverage to make packet imbalance
visible; those counts describe the candidate packet, not the final reviewed
dataset. The queue filters by proposed event year, and Previous/Next follow the
same interleaved order as the group selector. Export can include all eligible
groups or the explicit 12-per-year pilot based on reviewed years. The balanced
selection is deterministic, happens before splitting, and is recorded in the
benchmark card; it balances year counts only. `organization` means the named
actor performing the claim. Changing source groups announces the selected
source title and review guidance politely to assistive technology.

### Résumé and interview framing

A defensible current résumé line is:

> Built a local LLM evaluation and adaptation workspace with source-grouped splits, validation-only prompt selection, Qwen3-0.6B LoRA/SFT, reproducible trainer/adapter manifests, per-year failure analysis, frozen-test benchmark controls, and post-training INT8/NF4 plus optional W8A8 inference paths.

Pair it with this evidence qualifier until the real corpus is reviewed:

> Ran a one-epoch MPS LoRA smoke on 36 synthetic training rows and 6 validation rows; verified the schema-v5 configuration digest and live settings disclosure. A separate single-input MPS quantization canary is workflow evidence only; real-data quality and latency results await human label and reuse review.

In interviews, explain that source-related paraphrases stay together, prompt
and model selection use validation, and the final test is reserved for matched
arms. NF4 and INT8 are post-training inference paths; optional W8A8 activation
calibration uses label-free training inputs. QLoRA training is not implemented.
The single-input MPS quantization canary is not an accuracy or stable
throughput result; the one-epoch synthetic LoRA metrics are not model-quality
evidence.

## Quantization, calibration, and QLoRA

The frozen benchmark can compare a full-precision LoRA adapter with three
inference-only quantization choices. All selected variants use the same
validation-selected prompt and reserved test rows. Model revisions stay pinned
and load from the local cache. Install the optional backends in the project
environment with:

```bash
pip install -r requirements-quantization.txt
```

| Method | What is quantized | Calibration |
| --- | --- | --- |
| bitsandbytes LLM.int8 | 8-bit weights; outlier activations are handled at runtime | No offline calibration data |
| bitsandbytes NF4 | 4-bit NormalFloat weights with double quantization | No offline calibration data |
| Optimum Quanto W8A8 | 8-bit weights and activations after merging the LoRA adapter | One label-free input from each of up to 16 training source groups |

Quanto uses the direct library API because the Transformers integration only
supports weight-only quantization. PromptMesh loads the pinned adapter locally,
merges it into the base model, applies INT8 weight and activation quantization,
calibrates activation ranges on deterministic training-split inputs, then
freezes the quantized model. The report records the calibration input
fingerprint, prompt hash, split, group and example counts, package versions,
quantization time, and calibration time; the selected-input fingerprint also
participates in the frozen-run configuration hash. Validation and final-test
inputs and labels are excluded from calibration. MPS placement is supported by Quanto,
but optimized matrix kernels are CUDA-specific; the app measures MPS behavior
and does not promise a speedup. Quanto is in maintenance mode.

The adapter in this workflow is trained with full-precision LoRA/SFT. These
arms measure post-training quantized inference; they are not QLoRA training.
QLoRA would train the adapter while the frozen base is loaded in 4-bit NF4 and
is not implemented here. The tracked demo dataset is synthetic, so its output
is workflow evidence only and cannot support a model-quality claim. Fine-tune
results, saved adapter cards, and model selectors keep that synthetic status
beside the displayed metrics.

---

## 🧠 System Architecture

```
prompts/        → Versioned YAML prompt definitions
models/         → Model adapters and registry
core/           → Prompt rendering and execution engine
comparison/     → Prompt comparison logic
evaluation/     → Judge and scoring logic
optimization/   → Failure analysis and evolution engine
training/       → Grouped datasets, LoRA jobs, held-out metrics, local adapters
static/         → Frontend UI assets
app.py          → FastAPI backend server
main.py         → CLI experiment runner
```

---

## 📁 Updated Project Structure

```
PromptMesh/
├── app.py                  # FastAPI server
├── main.py                 # CLI pipeline runner
├── static/                 # Web UI (index.html, css, js)
│
├── prompts/
│   ├── registry.py
│   └── versions/
│       └── reasoning/
│           ├── v1.yaml
│           └── v2.yaml
│
├── models/
│   ├── base.py
│   ├── registry.py
│   ├── constants.py
│   ├── ollama_model.py
│   ├── cohere_model.py
│   └── oci_chat_model.py
│
├── core/
│   ├── executor.py
│   └── types.py
│
├── evaluation/
│   ├── judge.py
│   ├── scorer.py
│   └── rules.py
│
├── comparison/
│   └── runner.py
│
├── optimization/
│   ├── evolver.py
│   ├── failure_analysis.py
│   └── testcase_generator.py
│
├── diagnostic_test.py      # Judge and model diagnostics
├── combine_project_to_txt.py
└── README.md
```

---

## ▶️ Running PromptMesh (API + UI)

### 1. Environment Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

For the currently validated local LoRA/SFT and quantization environment on
Python 3.12 / Apple Silicon macOS, install the exact training dependency
snapshot with the app requirements:

```bash
pip install -r requirements.txt -r requirements-training-macos-arm64.lock
```

After installing, verify the environment with:

```bash
.venv/bin/python -m training.verify_lock
.venv/bin/python -m pip check
```

That lock pins the training and bitsandbytes dependency closure only. It is a
snapshot for macOS ARM64, not a cross-platform or full-application lock; the
general application dependencies in `requirements.txt` remain unpinned. The
standalone quantization install remains
`pip install -r requirements-quantization.txt` on other supported environments.
The verifier checks exact installed versions and refuses other Python/platform
targets; it does not replace a clean-environment install check.

On Windows, create the environment with `python -m venv .venv` and activate it
with `.venv\Scripts\activate` before installing requirements.

Prerequisites:

* Ollama running locally (for llama/qwen)
* OCI / Cohere credentials configured (if using cloud models)

---

### 2. Start the API and redesigned UI

```bash
./run.sh
```

The launcher safely restarts only a PromptMesh process it can identify by its
PID, command, and working directory. The main instance uses port `4004`:

```
http://127.0.0.1:4004
```

For isolated instances, `PROMPTMESH_PORT=5004 ./run.sh` starts a test instance;
`PROMPTMESH_PORT=6004 ./run.sh` starts a preview instance. The root endpoint
serves the UI and its API from the same process. `python app.py` remains
available on Windows and for the legacy port `8000` workflow.

The local workspace UI has been manually checked across its pages at widths
from 320px to 1440px. Keyboard users can skip the navigation and move focus to
the workspace while keeping the selected page. This covers navigation and
responsive layout, not a provider-backed end-to-end evaluation or a full
screen-reader/automated accessibility audit; see `HANDOFF.md` for the latest
verification scope.

The redesigned UI provides model evaluation, prompt comparison and evolution,
test-case generation, JSON export, local run summaries, and local LoRA/SFT
training. Prompt evolution edits instructions; fine-tuning changes adapter
weights. Prompt evolution selects revisions with LLM-judge heuristics on the
same supplied optimization inputs; it is not a gold-label benchmark. Training
compares the prompted Qwen3-0.6B base model and LoRA adapter on the same
deterministic, source-grouped validation examples using JSON validity, record
exact match, and field accuracy. These selection metrics are deterministic and
do not use PromptMesh's configured LLM judge. Training jobs leave the final-test
split unscored. The Fine-tune page can compare a candidate prompt on labeled
validation rows, then run a separate, single frozen test report for the base
model with the original prompt, the base model with the selected prompt, and
the matching LoRA adapter with that same selected prompt.

### Local LoRA/SFT workflow

Create a labeled JSONL file in `training/datasets/`; follow
[`training/datasets/README.md`](training/datasets/README.md). Each row needs a
`group_id`, `input`, and gold `output` object with `organization`, `year`, and
`claim`. Keep paraphrases or chunks from one source under the same group ID.
Start from the row example and benchmark-card template in
[`training/datasets/README.md`](training/datasets/README.md). Keep filled cards
and source data local. Follow the versioned
[entity-extraction annotation guide](training/datasets/ANNOTATION_GUIDE_v1.md)
when reviewing labels. Training is available for experimentation without a
review card; prompt selection and final benchmarking enforce its matching hash
and `human_reviewed` attestation.
The current extraction prompt definition treats `organization` as the actor
performing the claim, not its recipient.
PromptMesh assigns complete groups to deterministic train, validation, and
reserved final-test splits, requires at least 12 distinct groups, and records
the dataset SHA-256 with the adapter. Private dataset files and trained runs
are ignored by Git.

Open **Fine-tune** in the UI to choose a dataset, epoch count, LoRA rank, and
learning rate. The Qwen3-0.6B checkpoint must already be in the local Hugging
Face cache; training resolves its commit and uses local-only loading. Model
training and validation scoring run locally. The synthetic
`entity_extraction_demo` set checks the workflow only; it is not a benchmark or
résumé evidence. Use a reviewed, representative dataset and a fresh final-test
set before reporting any model improvement. Training is still
allowed for experimentation without a review card, but prompt selection and
final benchmarking require a matching card marked `human_reviewed`. PromptMesh
checks the card fields and exact data fingerprint; this local self-attestation
cannot independently prove that a human reviewed the labels. The UI states this
limit beside readiness and selection controls.

Schema-v5 adapter manifests, schema-v2 validation prompt-selection records,
and schema-v10 frozen benchmark reports record the Python, platform, machine,
device, and installed versions of the training and inference packages, plus
the PromptMesh Git revision and whether its working tree was dirty when each
stage finished. Adapter manifests also snapshot the effective TRL SFT settings,
PEFT LoRA settings, and float32 local-only model-loading configuration. Older
schema-v4 adapters remain loadable for inference, but cannot be selected for a
new frozen benchmark because their full training configuration was not saved.
Frozen reports carry the adapter configuration and include its digest in the
configuration fingerprint.
Both source fields are `null` when Git metadata is unavailable.
The Fine-tune page surfaces the training, selection, and benchmark environments
separately and labels legacy runs when their environment was not recorded. This
is run provenance, and the local training stack has an exact macOS ARM64 snapshot in
`requirements-training-macos-arm64.lock`. The rest of `requirements.txt` is
still unpinned, and the lock has not been validated by installing into a clean
environment. Run `python -m training.verify_lock` and `python -m pip check` to
confirm that an existing macOS ARM64 Python 3.12 environment matches the
snapshot; these checks do not prove a fresh installation succeeds.

After reviewing labels using the versioned annotation guide, fill
`training/datasets/<dataset_id>.card.json` from the template. Validation and
held-out test splits must each contain at least 30 examples across 10 source
groups. Select a validation-scored adapter and paste a candidate prompt
that includes `{{text}}`; PromptMesh compares it with `extraction/v1` using
record exact match, then field accuracy, then JSON-valid rate. Ties keep the
earlier prompt. This step only scores validation rows. The frozen action then
compares all three model/prompt arms on the same reserved test rows and saves a
report under ignored `training/benchmarks/<dataset_id>/<dataset_sha256>/`.
Reports include dataset/card/prompt/adapter fingerprints, pinned model and
tokenizer revisions, split and inference settings, hardware, aggregate task
metrics, and a deterministic source-group bootstrap interval. The same report
is returned on repeat requests; a private reservation prevents another test
inference for that dataset version, including after an interrupted run. A failed
run may have consumed the holdout, so create a new dataset version before
another final run.

Saved-adapter inference and both local benchmark endpoints use
`local_files_only`; benchmark runs also use the adapter's pinned checkpoint
revision. The model must already be cached. The benchmark endpoints do not send
dataset rows to a provider. Prompt evolution remains a separate LLM-judge
heuristic workflow; copy a candidate from it into the validation-selection form
to score it against gold labels.

Every workspace page includes a Back to overview control. While local LoRA
training or prompt evolution runs, choose **Run in background** to close the
progress dialog and keep working in PromptMesh. The top bar shows progress and
status; select it to reopen progress or view completed results. Keep the
browser tab open while the job runs. Run
`.venv/bin/python -m unittest discover -s tests -q` for the Python suite and
`node --test tests/ui_background_jobs.test.cjs` for the background-progress
regression checks.

The Fine-tune page shows schema readiness, example and source-group counts,
train/validation/reserved-test sizes, and a short SHA-256 dataset fingerprint.
Completed runs keep that fingerprint, prompt hash, and validation metric split with the
adapter. The UI shows aggregate plus per-field validation scores. Older
adapters display their test scores as legacy results because those scores were
exposed during iterative training. This covers the local dataset-validation
and evaluation parts of FineTuneDB's workflow; PromptMesh does not collect
production logs, support shared dataset editing, or host model training and
serving.

### Illustrations and motion

The overview hero and the empty run-history states use original transparent
PromptMesh companion artwork in `static/images/`. Its small float and thought
animations are decorative, and the shared reduced-motion rule disables them
for users who request less motion. Evaluate, Compare, Prompt evolution,
Fine-tune, Test cases, and Run history pair the companion with a small
task-specific SVG scene.

The API provides `GET /api/training/datasets`, `GET /api/training/adapters`,
`POST /api/training/jobs`, `POST /api/training/prompt-selections`, and
`POST /api/training/benchmarks`. These accept dataset, adapter, and prompt IDs
or text, not arbitrary file paths or uploaded corpus contents. Adapter files,
prompt-selection records, and frozen reports are stored locally under ignored
`training/runs/`, `training/selections/`, and `training/benchmarks/` paths.
PromptMesh's general Evaluate page uses the configured judge model, which may
be remote; use it only with data that may be sent to that provider.

---

## 🌐 Available API Endpoints

### Health

```
GET /api/health
```

---

### Task Discovery

```
GET /api/tasks
GET /api/tasks/{task}/versions
```

---

### Model Registry

```
GET /api/models
```

Local training datasets and saved adapters are listed by
`GET /api/training/datasets` and `GET /api/training/adapters`.

---

### Prompt Evaluation (Async Job)

```
POST /api/evaluate
```

Features:

* Background execution
* Multi-model evaluation
* Automatic test generation

---

### Prompt Comparison

```
POST /api/compare
```

---

### Prompt Evolution

```
POST /api/evolve
```

Runs automated optimization loop.

---

### Test Case Generation

```
POST /api/test-cases/generate
```

### Local fine-tuning

```text
POST /api/training/jobs
```

Starts one local LoRA/SFT job; poll its job ID through the existing
`GET /api/jobs/{job_id}` route. Training is disabled until the local training
dependencies are available. Only one training job can use the local model
resources at a time.

---

### Job Status Tracking

```
GET /api/jobs/{job_id}
```

Returns:

* Progress percentage
* Final results
* Error details (if any)

---

## API access and request limits

The default `python app.py` launcher listens only on `127.0.0.1`. When no API key
is configured, API requests are accepted only from a loopback address.

To expose the API on a network interface, set a private key of at least 32
characters and then bind Uvicorn to the required interface:

```bash
export PROMPTMESH_API_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
uvicorn app:app --host 0.0.0.0 --port 8000
```

The browser UI asks for this key when the server requires it. API clients must
send it as `Authorization: Bearer <key>`. Keep it private and use HTTPS for
remote deployments. Same-origin browser access needs no CORS configuration. If
the browser UI is hosted separately, set `PROMPTMESH_ALLOWED_ORIGINS` to a
comma-separated list of exact frontend origins; wildcard origins are not
accepted.

The API rejects request bodies over 128 KiB, limits each caller to 10 work
requests per minute and 2 active jobs, and allows at most 4 active model jobs
per server process. It retains at most 100 completed job records and expires
them after 30 minutes. Model/input counts and output tokens are bounded by the
API request schemas, and model-provider HTTP calls time out after 240 seconds.
Synchronous test-case generation runs in a worker thread and uses the same
active-work limits, so a slow provider call does not block the HTTP event loop.

Prompt templates support simple placeholders such as `{{text}}` or
`{{ text }}`. Jinja expressions, filters, calls, and control blocks are not
executed.

---

## ▶️ Running CLI Pipeline (Standalone Mode)

For debugging and batch experiments:

```bash
python main.py
```

Pipeline flow:

1. Load YAML prompt
2. Generate test cases
3. Evaluate across models
4. Rank models
5. Run failure analysis
6. Trigger prompt evolution
7. Final evaluation

---

## 📊 Scoring Formula

Final score computation:

```
0.4 × Accuracy
+ 0.3 × Completeness
+ 0.2 × Adherence
− 0.1 × Hallucination
```

Hallucination is explicitly penalized and monitored during evolution.

---

## 🧪 Diagnostics & Debugging

Use the built-in diagnostic script:

```bash
python diagnostic_test.py
```

It validates:

* Judge JSON extraction
* Judge scoring behavior
* Model connectivity
* Token and latency reporting

---

## 🎯 Use Cases

* Prompt benchmarking
* Model comparison
* Prompt regression testing
* Automated prompt optimization
* LLM evaluation research
* Internal GenAI tooling

---

## 🧭 Roadmap

Planned improvements:

* Persistent experiment storage
* Execution parallelization
* Cost tracking per run
* Prompt evolution visualization
* UI-based comparison dashboard
* CI/CD prompt regression testing

---

## 📄 License

MIT License

---

## ✍️ Author

Built by **Arjeet Anand**
Focused on GenAI systems, prompt evaluation, and automated LLM optimization.
