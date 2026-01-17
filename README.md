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
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

Prerequisites:

* Ollama running locally (for llama/qwen)
* OCI / Cohere credentials configured (if using cloud models)

---

### 2. Start FastAPI Server

```bash
python app.py
```

Server starts at:

```
http://localhost:8000
```

The root endpoint automatically serves the frontend UI.

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
