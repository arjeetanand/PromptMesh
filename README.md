# PromptMesh

**PromptMesh** is a **model-agnostic prompt evaluation, comparison, and evolution platform** with a built-in **FastAPI backend and web UI**. It allows you to evaluate prompt versions across multiple LLMs, run controlled experiments, generate test cases, and evolve prompts using an automated feedback loop.

PromptMesh treats prompt engineering as a **system-level workflow** rather than ad-hoc trial and error.

---

## 🚀 Overview

PromptMesh provides a **production-ready prompt experimentation platform** with an integrated API server and web interface.

It enables:

* Programmatic prompt evaluation
* Multi-model benchmarking
* Automated test generation
* Prompt evolution with feedback loops
* Real-time job tracking and result inspection

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

Independent judge model scores outputs on:

* Accuracy
* Completeness
* Instruction adherence
* Hallucination risk

Features:

* Robust JSON extraction
* Graceful parsing fallback
* Structured score breakdowns

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

## 🧠 System Architecture

```
prompts/        → Versioned YAML prompt definitions
models/         → Model adapters and registry
core/           → Prompt rendering and execution engine
comparison/     → Prompt comparison logic
evaluation/     → Judge and scoring logic
optimization/   → Failure analysis and evolution engine
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

The redesigned UI provides model evaluation, two-prompt comparison, prompt
evolution, generated test cases, JSON result export, and local run summaries.
Prompt evolution edits instructions; it does not train model weights. LoRA or
other fine-tuning is not connected to the current API, and the UI labels that
boundary explicitly. A credible training extension should add a separate
dataset and training pipeline, then compare the adapter against the base model
on a held-out benchmark.

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
