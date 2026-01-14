# PromptMesh

**PromptMesh** is a **model-agnostic prompt evaluation, evolution, and persistence framework** that systematically compares, scores, stores, and **iteratively improves prompts** across multiple Large Language Models (LLMs).

It treats prompt engineering as a **systems and lifecycle problem**, combining prompt versioning, multi-model execution, LLM-as-a-Judge evaluation, controlled prompt evolution, and **experiment persistence** into a single platform.

---

## 🚀 Why PromptMesh?

In real-world GenAI systems:

* Small prompt changes can cause large behavioral shifts
* Prompt quality varies drastically across models
* Manual prompt iteration does not scale
* Hallucination control requires objective measurement
* Prompt experiments must be reproducible and auditable

**PromptMesh turns prompt engineering into a measurable, repeatable, evolvable, and trackable process.**

---

## ✨ Core Capabilities

### Phase 1 — Prompt Evaluation & Comparison

Phase 1 establishes a rigorous evaluation baseline.

* **Prompt Versioning (YAML-first)**

  * Versioned prompts per task
  * Easy experimentation, rollback, and comparison

* **Multi-Model Execution**

  * Execute the same prompt across heterogeneous backends:

    * **OCI GenAI** (Command-A, Meta, Gemini, Grok)
    * **Ollama** (local models like Llama 3, Qwen)
    * **Cohere / OpenAI** (pluggable APIs)

* **LLM-as-a-Judge Evaluation**

  * Independent judge model scores outputs on:

    * Accuracy
    * Completeness
    * Instruction adherence
    * Hallucination risk
  * Robust JSON extraction with graceful failure handling

* **Deterministic Scoring**

  * Weighted scoring formula
  * Hard rule checks + soft semantic judgment

---

### Phase 2 — Prompt Evolution Engine

Phase 2 upgrades PromptMesh from comparison to a **closed-loop prompt evolution system**.

Instead of a single optimization step, prompts are **mutated, evaluated, selected, validated, and evolved** until convergence.

#### What Phase 2 Adds

* **Prompt Mutation (`optimization/mutator.py`)**

  * Generates multiple candidate prompt variants per iteration
  * Each variant targets a specific failure mode (hallucination, accuracy loss, etc.)

* **Candidate Selection (`optimization/selector.py`)**

  * Executes all candidates on an evaluation model
  * Scores each using the evaluation pipeline
  * Selects the highest-performing prompt

* **Evolution Loop (`optimization/evolver.py`)**

  * Iteratively refines prompts over generations
  * Convergence checks based on score delta (`min_delta`)
  * Anti-regression constraints (e.g. hallucination must not increase)

* **Failure-Aware Evolution**

  * Automatic failure classification (hallucination, accuracy loss, completeness, adherence)
  * Evolution strategy adapts based on detected failure

* **Traceable Evolution History**

  * Stores prompt text, scores, and breakdowns per iteration
  * Enables full auditability of prompt changes

---

### Phase 3 — Experiment Persistence & Analysis

PromptMesh now persists all experiments for reproducibility and analysis.

* **SQLite-backed Storage (`storage/`)**

  * Stores prompts, runs, evaluations, and outputs
  * Enables longitudinal analysis of prompt evolution

* **Structured Experiment Tracking**

  * Prompt → Run → Evaluation hierarchy
  * Latency, scores, breakdowns, and raw outputs recorded

This elevates PromptMesh from an experimentation script to a **prompt engineering platform**.

---

## 🧠 System Architecture

```
prompts/        → Versioned prompt definitions (YAML)
models/         → Model adapters & registries
core/           → Execution, prompt rendering
comparison/     → Prompt/model comparison orchestration
evaluation/     → Rules, judge, scoring logic
optimization/   → Prompt mutation, evolution & validation
storage/        → Experiment persistence (SQLite)
main.py         → End-to-end experiment runner
```

---

## 📁 Project Structure

```
mcp/
├── prompts/
│   ├── registry.py
│   └── versions/
│       └── summarization/
│           ├── v1.yaml
│           └── v2.yaml
│
├── models/
│   ├── base.py
│   ├── registry.py
│   ├── constants.py
│   ├── oci_chat_model.py
│   ├── ollama_model.py
│   ├── cohere_model.py
│   └── openai_model.py
│
├── core/
│   ├── executor.py
│   ├── result.py
│   └── types.py
│
├── evaluation/
│   ├── rules.py
│   ├── judge.py
│   ├── scorer.py
│   └── types.py
│
├── comparison/
│   ├── runner.py
│   ├── ranker.py
│   └── types.py
│
├── optimization/
│   ├── failure_analysis.py
│   ├── mutator.py
│   ├── selector.py
│   ├── evolver.py
│   ├── meta_prompt.py
│   ├── optimizer.py
│   └── validator.py
│
├── storage/
│   ├── db.py
│   ├── init_db.py
│   └── repository.py
│
├── main.py
└── README.md
```

---

## 🧪 Test Case–Driven Evaluation

PromptMesh supports **explicit test scenarios** to stress prompts:

* `baseline`
* `hallucination_trap`
* `completeness_failure`
* `instruction_conflict`

Each test case exposes different failure modes and drives evolution decisions.

---

## 🛠 Supported Models

### Local (Ollama)

* `llama3`
* `llama3:8b`
* `qwen2.5:latest`
* `llava:latest`

### Cloud

* **OCI GenAI**

  * Command-A (generation + judge)
  * Meta / Gemini / Grok (generic chat)
* **Cohere Public API**
* **OpenAI API** (extensible)

---

## ▶️ Running PromptMesh

### 1. Environment Setup

```bash
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

Prerequisites:

* OCI credentials configured locally
* Ollama running for local inference

---

### 2. Initialize Storage

```bash
python storage/init_db.py
```

---

### 3. Run End-to-End Experiment

```bash
python main.py
```

Execution flow:

1. Initial prompt comparison across models
2. Best prompt selection
3. Failure analysis
4. Iterative prompt evolution
5. Final multi-model evaluation
6. Persistent storage of all results

---

## 📊 Scoring Model

Final score is computed as:

```
0.4 × Accuracy
+ 0.3 × Completeness
+ 0.2 × Adherence
− 0.1 × Hallucination
```

Hallucination is explicitly penalized and used as a hard stop during evolution.

---

## 🔐 Security

* No credentials are committed
* `.gitignore` excludes:

  * OCI config files
  * Virtual environments
  * Generated artifacts

---

## 🎯 Use Cases

* Prompt benchmarking
* Cross-model prompt validation
* Prompt regression testing
* Hallucination reduction
* GenAI experimentation platforms
* Internal evaluation and governance tooling

---

## 🧭 Roadmap

* Parallel execution engine
* Cost estimation per run
* Judge ensembles and calibration
* JSON-schema output validation
* Prompt evolution visualizer
* Web UI / dashboard
* CI-based prompt regression testing

---

## 📄 License

MIT License

---

## ✍️ Author

Built by **Arjeet Anand**
Focused on GenAI systems, prompt evaluation, and cloud-scale LLM engineering.
