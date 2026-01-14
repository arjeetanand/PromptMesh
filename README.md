# PromptForge

**PromptForge** is a **model-agnostic prompt evaluation and optimization framework** that lets you compare prompt versions across multiple LLMs, score outputs using **LLM-as-a-Judge**, and automatically generate improved prompts based on observed failures.

It is designed as a **Model Comparison Platform (MCP)** for serious prompt engineering, evaluation, and experimentation.

---

## 🚀 Why PromptForge?

When building GenAI systems:

* Small prompt changes can lead to large output differences
* Comparing prompts across models is manual and error-prone
* Evaluating “quality” is subjective without structure
* Improving prompts often relies on intuition, not data

**PromptForge solves this by turning prompt engineering into a measurable, repeatable system.**

---

## ✨ Key Features

* **Prompt Versioning (YAML-based)**

  * Maintain multiple prompt versions per task
  * Easy diffing and iteration

* **Multi-Model Execution**

  * Run the same prompt against:

    * OCI GenAI (Command-A, Meta, Gemini, Grok, etc.)
    * Ollama (local models like Llama 3, Qwen)
    * Cohere / OpenAI (extensible)

* **LLM-as-a-Judge Evaluation**

  * Uses a judge model to score outputs on:

    * Accuracy
    * Completeness
    * Instruction adherence
    * Hallucination risk

* **Deterministic Scoring**

  * Weighted scoring function
  * Hard rule checks + soft LLM judgment

* **Automated Prompt Optimization**

  * Detects failure types (hallucination, accuracy loss, etc.)
  * Generates improved prompts automatically
  * Validates improvements before acceptance

* **Model-Agnostic Architecture**

  * All models conform to a single interface
  * Easy to add new providers

---

## 🧠 Architecture Overview

```
prompts/        → Prompt definitions & versions (YAML)
models/         → LLM adapters (OCI, Ollama, Cohere, OpenAI)
core/           → Execution & prompt rendering
evaluation/     → Rules, judge, scoring logic
comparison/     → Prompt & model comparison orchestration
optimization/   → Failure analysis & prompt refinement
main.py         → Entry point / experiment runner
```

---

## 📁 Folder Structure

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
│   ├── meta_prompt.py
│   ├── optimizer.py
│   └── validator.py
│
├── main.py
└── README.md
```

---

## 🛠 Supported Models

### Local (via Ollama)

* `llama3`
* `llama3:8b`
* `qwen2.5`
* `llava`

### Cloud

* **OCI GenAI**

  * Command-A (judge + generation)
  * Meta / Gemini / Grok (generic chat)
* **Cohere (Public API)**
* **OpenAI** (extensible)

---

## ▶️ Running PromptForge

### 1. Setup environment

```bash
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

Ensure:

* OCI config is set up locally
* Ollama is running for local models

---

### 2. Define prompts

Create YAML files in:

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

### 3. Run experiments

```bash
python main.py
```

This will:

1. Load prompt versions
2. Render prompts with inputs
3. Run them across selected models
4. Evaluate outputs
5. Rank prompts
6. Suggest improved prompts if failures are detected

---

## 📊 Example Output

```
PROMPT VERSION: v1
MODEL: command-a
SCORE: 6.8
BREAKDOWN: {accuracy: 8, completeness: 7, adherence: 7, hallucination: 2}

PROMPT VERSION: v2
MODEL: command-a
SCORE: 7.5
BREAKDOWN: {accuracy: 9, completeness: 8, adherence: 8, hallucination: 1}
```

---

## 🔍 Evaluation Logic

Final score is computed as:

```
0.4 × Accuracy
+ 0.3 × Completeness
+ 0.2 × Adherence
− 0.1 × Hallucination
```

This makes hallucination **explicitly penalized**.

---

## 🧪 Prompt Optimization Loop

1. Detect failure type
2. Generate revised prompt using optimizer LLM
3. Re-evaluate outputs
4. Accept improvement only if score improves

This enables **self-improving prompts**.

---

## 🔐 Security

* OCI credentials are **never committed**
* `.gitignore` excludes:

  * `ociConfig/`
  * virtual environments
  * generated artifacts

---

## 🎯 Use Cases

* Prompt benchmarking
* Model comparison
* Regression testing prompts
* Reducing hallucinations
* GenAI experimentation platforms
* Research & internal tooling

---

## 🧭 Roadmap

* Parallel execution
* Cost estimation per run
* Judge calibration
* JSON-schema output validation
* Web UI / dashboard
* CI-based prompt regression testing

---

## 📄 License

MIT License (recommended for open experimentation).

---

## ✍️ Author

Built by **Arjeet Anand**
Focused on GenAI systems, evaluation, and cloud-scale LLM engineering.
