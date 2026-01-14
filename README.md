# PromptMesh

**PromptMesh** is a **model-agnostic prompt evaluation and prompt evolution framework** that systematically compares, scores, and **iteratively improves prompts** across multiple Large Language Models (LLMs).

It treats prompt engineering as a **systems problem**, combining versioning, evaluation, LLM-as-a-Judge scoring, and convergence-controlled prompt evolution into a single platform.

---

## 🚀 Why PromptMesh?

In real-world GenAI systems:

* Small prompt changes can cause large behavioral shifts
* Prompt quality varies drastically across models
* Manual prompt iteration does not scale
* Hallucination control requires objective measurement

**PromptMesh turns prompt engineering into a measurable, repeatable, and evolvable process.**

---

## ✨ Core Capabilities

### Phase 1 — Prompt Evaluation & Comparison

Phase 1 establishes a rigorous evaluation baseline.

* **Prompt Versioning (YAML-first)**

  * Versioned prompts per task
  * Easy experimentation and rollback

* **Multi-Model Execution**

  * Execute the same prompt across heterogeneous backends:

    * OCI GenAI (Command‑A, Meta, Gemini, Grok)
    * Ollama (local models like Llama 3, Qwen)
    * Cohere / OpenAI (pluggable)

* **LLM-as-a-Judge Evaluation**

  * Independent judge model scores outputs on:

    * Accuracy
    * Completeness
    * Instruction adherence
    * Hallucination risk

* **Deterministic Scoring**

  * Weighted scoring formula
  * Hard rule checks + soft semantic judgment

---

### Phase 2 — Prompt Evolution Engine

Phase 2 upgrades PromptMesh from comparison to **self-improving prompt evolution**.

Instead of a single optimization step, prompts are **mutated, evaluated, selected, and evolved** until convergence.

#### What Phase 2 Adds

* **Prompt Mutation (`optimization/mutator.py`)**

  * Generates multiple candidate prompts per iteration
  * Each mutation targets a specific failure mode

* **Candidate Selection (`optimization/selector.py`)**

  * Executes all candidates
  * Scores each using the evaluation pipeline
  * Selects the highest‑performing prompt

* **Evolution Loop (`optimization/evolver.py`)**

  * Iteratively refines prompts over generations
  * Stops when improvement falls below a threshold
  * Enforces anti‑regression constraints (e.g. hallucination control)

* **Traceable Evolution History**

  * Stores prompt text, scores, and breakdowns per generation
  * Enables full auditability of prompt changes

This transforms PromptMesh into a **closed‑loop prompt evolution system**.

---

## 🧠 System Architecture

```
prompts/        → Versioned prompt definitions (YAML)
models/         → Model adapters & registries
core/           → Execution, prompt rendering
comparison/     → Prompt/model comparison orchestration
evaluation/     → Rules, judge, scoring logic
optimization/   → Prompt mutation, evolution & validation
main.py         → Experiment runner
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
├── main.py
└── README.md
```

---

## 🛠 Supported Models

### Local (Ollama)

* `llama3:latest`
* `llama3:8b`
* `qwen2.5:latest`
* `llava:latest`

### Cloud

* **OCI GenAI**

  * Command‑A (generation + judge)
  * Meta / Gemini / Grok (generic chat)
* **Cohere API**
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

### 2. Define Prompts

Create prompt versions under:

```
prompts/versions/<task>/<version>.yaml
```

Example:

```yaml
template: |
  Summarize the following text:

  {{text}}
```

---

### 3. Run Experiments

```bash
python main.py
```

Execution flow:

1. Load prompt versions
2. Render prompts with inputs
3. Execute across models
4. Evaluate outputs
5. Rank prompts
6. Evolve prompts (Phase 2)
7. Validate improvements

---

## 📊 Scoring Model

Final score is computed as:

```
0.4 × Accuracy
+ 0.3 × Completeness
+ 0.2 × Adherence
− 0.1 × Hallucination
```

Hallucination is explicitly penalized.

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
* Model comparison
* Prompt regression testing
* Hallucination reduction
* GenAI experimentation platforms
* Internal evaluation tooling

---

## 🧭 Roadmap

* Parallel execution engine
* Cost estimation per run
* Judge calibration & ensembles
* JSON‑schema output validation
* Prompt evolution visualizer
* Web UI / dashboard
* CI‑based prompt regression testing

---

## 📄 License

MIT License

---

## ✍️ Author

Built by **Arjeet Anand**
Focused on GenAI systems, prompt evaluation, and cloud‑scale LLM engineering.
