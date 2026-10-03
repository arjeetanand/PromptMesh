# Security Review: PromptMesh

## Scope

Static security review of all 50 tracked files in PromptMesh at commit 5c51333fe4cbfc3f2ac5b3271ad3766ffc68e8ab.

- Scan mode: repository
- Target kind: git_revision
- Target ID: target_sha256_3c300149b2c8f5b6671c399eef5753232a3e396ad068321825b28013af403590
- Revision: 5c51333fe4cbfc3f2ac5b3271ad3766ffc68e8ab
- Inventory strategy: repository
- Included paths: .
- Excluded paths: none
- Artifacts reviewed: All 50 tracked repository files, Threat model, SQLite prompt databases inspected read-only
- Scan context: FastAPI prompt evaluation/evolution service: browser requests load prompt YAML, render templates, call model adapters, store jobs in memory, and return results.

Limitations and exclusions:
- Deployment reachability and upstream authentication are unknown.
- Active provider credentials, quotas, and external resource limits were not inspected.
- No live requests or model-provider calls were made.
- The Jinja runtime proof could not execute because Jinja2 was unavailable in the review Python environment.

### Scan Summary

| Field | Value |
| --- | --- |
| Scan outcome | completed |
| Reportable findings | 3 |
| Severity mix | critical: 1, high: 1, medium: 1 |
| Confidence mix | high: 3 |
| Coverage | complete |
| Validation mode | Static source trace, read-only SQLite inspection, and safe standard-library path-composition check. |

Canonical artifacts: `scan-manifest.json`, `findings.json`, and `coverage.json`. This report is a deterministic projection of those files.

## Threat Model

A caller able to reach the FastAPI service can submit prompt/evolution JSON, task/version values, model selections, and unbounded work requests; handlers render templates, load YAML, call models, retain jobs, and return results.

### Assets

- Server process and its reachable files/credentials
- Prompt definitions and evaluation data
- Model-provider quota/cost
- API availability and in-memory job results

### Trust Boundaries

- Unauthenticated HTTP clients to FastAPI
- Caller-controlled prompt text to Jinja
- Caller-controlled task/version values to registry file reads
- Requests to model adapters
- Job results to browser output

### Attacker Capabilities

- Submit JSON requests if network-reachable
- Select prompt/model inputs and task/version values
- Poll a job ID returned to the caller

### Security Objectives

- Keep caller prompt text inert
- Confine YAML reads to the registry directory
- Bound model work and retained job state

### Assumptions

- Review covers immutable commit 5c51333fe4cbfc3f2ac5b3271ad3766ffc68e8ab only.
- Production exposure, upstream controls, credentials, and quotas are unknown.

## Findings

| Finding | Severity | Confidence | Detailed write-up |
| --- | --- | --- | --- |
| [Client-supplied prompt templates can execute code in the server process](#finding-1) | critical | high | inline below |
| [Unauthenticated callers can queue unbounded model work and retain results](#finding-2) | high | high | inline below |
| [Prompt registry accepts paths outside its versions directory](#finding-3) | medium | high | inline below |

### Confidence Scale

| Label | Meaning |
| --- | --- |
| high | Direct evidence supports the finding with no material unresolved blocker. |
| medium | Evidence supports a plausible issue, but material runtime or reachability proof remains. |
| low | Evidence is incomplete and the item is retained only for explicit follow-up. |

<a id="finding-1"></a>

### [1] Client-supplied prompt templates can execute code in the server process

| Field | Value |
| --- | --- |
| Severity | critical |
| Confidence | high |
| Confidence rationale | Direct source trace connects request input to Jinja Template construction and rendering; dynamic execution was not observed because Jinja2 was unavailable in the review Python environment. |
| Category | server-side-template-injection |
| CWE | CWE-1336, CWE-94 |
| Affected lines | app.py:95-105, app.py:406-415, core/types.py:3-5 |

#### Summary

An unauthenticated `/api/evolve` request can place attacker-controlled text in `custom_prompt`; the evolution path sends it to the shared `render_prompt()` helper, which compiles it with default unsandboxed Jinja `Template`. A crafted template can reach server-side code execution. The direct app entrypoint binds to all interfaces, though deployment reachability is unknown.

#### Root Cause

API-supplied prompt text must remain data. Instead, the handler copies it unchanged into `base_prompt`, the evolver forwards it to `render_prompt()`, and that helper compiles it with default Jinja `Template` before rendering; no sandbox or allowlist separates caller syntax from Python objects.

**Evolution request accepts custom prompt** — `app.py:95-105`

`custom_prompt` is caller-controlled text.

```python
class EvolutionRequest(BaseModel):
    task: str
    version: str
    model: str
    optimizer_model: str = "command-a-03-2025"
    max_iterations: int = 3
    test_case_count: int = 3
    min_delta: float = 0.25
    custom_prompt: Optional[str] = None
    custom_constraints: Optional[dict] = None
    test_inputs: Optional[List[str]] = None
```

**Evolution route queues caller request** — `app.py:211-222`

The route accepts the model directly and has no route-level authentication dependency.

```python
@app.post("/api/evolve")
async def evolve_prompt_api(request: EvolutionRequest, bg: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "running",
        "progress": 0,
        "results": None,
        "error": None,
        "started_at": datetime.utcnow().isoformat()
    }
    bg.add_task(run_evolution_job, job_id, request)
    return {"job_id": job_id, "status": "started"}
```

**Custom prompt becomes base template** — `app.py:406-415`

The request string is copied unchanged into `base_prompt`.

```python
if request.custom_prompt:
    base_prompt = request.custom_prompt
    constraints = request.custom_constraints or {"temperature": 0.0, "max_tokens": 256}
    task_type = "generation"
    input_vars = ["text"]
else:
    meta = registry.load_with_metadata(request.task, request.version)
    base_prompt = meta["template"]
```

**Evolution passes template to renderer** — `optimization/evolver.py:16-22`

The request-derived prompt reaches the shared renderer.

```python
for text in task_inputs:
    rendered = render_prompt(
        prompt_template,
        {input_var: text}
    )

    result = model.run(rendered, constraints)
```

**Renderer compiles and evaluates Jinja template** — `core/types.py:1-5`

The default `Template` evaluates expressions without a sandbox.

```python
from jinja2 import Template

def render_prompt(prompt_template: str, variables: dict) -> str:
    template = Template(prompt_template)
    return template.render(**variables)
```

#### Validation

The route-to-render path is direct in source. A dynamic template-expression check could not run because Jinja2 was unavailable in the review Python environment.

Validation method: Static source trace; dynamic reproduction unavailable

**Evolution request accepts custom prompt** — `app.py:95-105`

`custom_prompt` is caller-controlled text.

```python
class EvolutionRequest(BaseModel):
    task: str
    version: str
    model: str
    optimizer_model: str = "command-a-03-2025"
    max_iterations: int = 3
    test_case_count: int = 3
    min_delta: float = 0.25
    custom_prompt: Optional[str] = None
    custom_constraints: Optional[dict] = None
    test_inputs: Optional[List[str]] = None
```

**Evolution route queues caller request** — `app.py:211-222`

The route accepts the model directly and has no route-level authentication dependency.

```python
@app.post("/api/evolve")
async def evolve_prompt_api(request: EvolutionRequest, bg: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "running",
        "progress": 0,
        "results": None,
        "error": None,
        "started_at": datetime.utcnow().isoformat()
    }
    bg.add_task(run_evolution_job, job_id, request)
    return {"job_id": job_id, "status": "started"}
```

**Custom prompt becomes base template** — `app.py:406-415`

The request string is copied unchanged into `base_prompt`.

```python
if request.custom_prompt:
    base_prompt = request.custom_prompt
    constraints = request.custom_constraints or {"temperature": 0.0, "max_tokens": 256}
    task_type = "generation"
    input_vars = ["text"]
else:
    meta = registry.load_with_metadata(request.task, request.version)
    base_prompt = meta["template"]
```

**Evolution passes template to renderer** — `optimization/evolver.py:16-22`

The request-derived prompt reaches the shared renderer.

```python
for text in task_inputs:
    rendered = render_prompt(
        prompt_template,
        {input_var: text}
    )

    result = model.run(rendered, constraints)
```

**Renderer compiles and evaluates Jinja template** — `core/types.py:1-5`

The default `Template` evaluates expressions without a sandbox.

```python
from jinja2 import Template

def render_prompt(prompt_template: str, variables: dict) -> str:
    template = Template(prompt_template)
    return template.render(**variables)
```

Assertions:
- `custom_prompt` becomes `base_prompt` without sanitization.
- `render_prompt()` constructs `jinja2.Template` and calls `render()`.
- The route has no route-level authentication dependency.

Limitations:
- No live service or upstream authentication boundary was tested.
- Dynamic execution was not observed because Jinja2 was unavailable in the review environment.

#### Dataflow

`custom_prompt` -\> `run_evolution_job()` -\> `evolve_prompt()` -\> `render_prompt()` -\> Jinja render

- **Source:** Caller-controlled prompt string

- **Sink:** `jinja2.Template(...).render()`

- **Outcome:** Template expression execution in API process

**Evolution route queues caller request** — `app.py:211-222`

The route accepts the model directly and has no route-level authentication dependency.

```python
@app.post("/api/evolve")
async def evolve_prompt_api(request: EvolutionRequest, bg: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "running",
        "progress": 0,
        "results": None,
        "error": None,
        "started_at": datetime.utcnow().isoformat()
    }
    bg.add_task(run_evolution_job, job_id, request)
    return {"job_id": job_id, "status": "started"}
```

**Custom prompt becomes base template** — `app.py:406-415`

The request string is copied unchanged into `base_prompt`.

```python
if request.custom_prompt:
    base_prompt = request.custom_prompt
    constraints = request.custom_constraints or {"temperature": 0.0, "max_tokens": 256}
    task_type = "generation"
    input_vars = ["text"]
else:
    meta = registry.load_with_metadata(request.task, request.version)
    base_prompt = meta["template"]
```

**Evolution passes template to renderer** — `optimization/evolver.py:16-22`

The request-derived prompt reaches the shared renderer.

```python
for text in task_inputs:
    rendered = render_prompt(
        prompt_template,
        {input_var: text}
    )

    result = model.run(rendered, constraints)
```

**Renderer compiles and evaluates Jinja template** — `core/types.py:1-5`

The default `Template` evaluates expressions without a sandbox.

```python
from jinja2 import Template

def render_prompt(prompt_template: str, variables: dict) -> str:
    template = Template(prompt_template)
    return template.render(**variables)
```

**Evolution request accepts custom prompt** — `app.py:95-105`

`custom_prompt` is caller-controlled text.

```python
class EvolutionRequest(BaseModel):
    task: str
    version: str
    model: str
    optimizer_model: str = "command-a-03-2025"
    max_iterations: int = 3
    test_case_count: int = 3
    min_delta: float = 0.25
    custom_prompt: Optional[str] = None
    custom_constraints: Optional[dict] = None
    test_inputs: Optional[List[str]] = None
```

#### Reachability

Source has no route-level authentication; exploitation requires deployed reachability and no effective upstream authentication.

- **Attacker:** Unauthenticated network caller

- **Entry point:** POST `/api/evolve`

- **Outcome:** Template evaluation with API process privileges

Preconditions:
- Service is reachable by attacker.
- Jinja dependency is installed in runtime.

Limitations:
- Production network boundary and runtime configuration were not inspected.

#### Severity

**Critical** — If reachable without upstream access control, a remote unauthenticated caller can execute template expressions in the Python process.

Lower if deployment evidence shows the service is unreachable to untrusted callers or protected by effective upstream authentication.

Impact assessment:
- **Level:** critical
- **Why:** Successful template escape can run code with the service process's file, environment, and provider-credential access.

Likelihood assessment:
- **Level:** high
- **Why:** Request-to-render flow is direct; deployment exposure remains unknown.

#### Remediation

Do not compile caller-controlled prompts with default Jinja `Template`; use a constrained sandbox with a strict allowlist, or treat custom prompt text as literal content.

Tests:
- Submit a template expression that traverses Python objects and assert it is rejected or remains literal.
- Verify `/api/evaluate` and `/api/evolve` share the constrained rendering policy.

Preventive controls:
- Require authentication and authorization for exposed prompt-execution routes.
- Apply request-size limits and structured template validation.

<a id="finding-2"></a>

### [2] Unauthenticated callers can queue unbounded model work and retain results

| Field | Value |
| --- | --- |
| Severity | high |
| Confidence | high |
| Confidence rationale | Source directly shows unbounded request dimensions, per-request background tasks, nested model/input loops, and global job retention; live impact was not measured. |
| Category | uncontrolled-resource-consumption |
| CWE | CWE-400 |
| Affected lines | app.py:76-84, app.py:183-194, app.py:63-64 |

#### Summary

Evaluation/evolution requests accept unbounded collections and numeric work limits, then enqueue model calls as background tasks without route-level authentication, rate limits, or visible concurrency bounds. Jobs and outputs are held in a process-global map with no cleanup path found. A reachable attacker can consume service resources and, if credentials are enabled, model quota or spend.

#### Root Cause

The API accepts arrays and numeric work limits without bounds, schedules a background task for each request, and runs nested loops that call model adapters. There is no visible authentication, quota, or bounded worker queue in these handlers. Job records and results are stored in global `jobs`, and repository-wide search found no cleanup path.

**Evaluation request has unbounded arrays and count** — `app.py:76-84`

`models`, `test_inputs`, and `test_case_count` have no maximum bounds.

```python
class EvaluationRequest(BaseModel):
    task: str
    version: str
    models: List[str]
    test_inputs: Optional[List[str]] = None
    generate_test_cases: bool = True
    test_case_count: int = 3
    custom_prompt: Optional[str] = None
    custom_constraints: Optional[dict] = None
```

**Evolution request has unbounded limits and inputs** — `app.py:95-105`

The caller controls iteration/count values and an optional input list without enforced bounds.

```python
class EvolutionRequest(BaseModel):
    task: str
    version: str
    model: str
    optimizer_model: str = "command-a-03-2025"
    max_iterations: int = 3
    test_case_count: int = 3
    min_delta: float = 0.25
    custom_prompt: Optional[str] = None
    custom_constraints: Optional[dict] = None
    test_inputs: Optional[List[str]] = None
```

**Each evaluation request allocates and queues a job** — `app.py:183-194`

Each accepted request allocates memory and schedules work without a visible handler-level queue or quota check.

```python
@app.post("/api/evaluate")
async def evaluate_prompt(request: EvaluationRequest, bg: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "running",
        "progress": 0,
        "results": None,
        "error": None,
        "started_at": datetime.utcnow().isoformat()
    }
    bg.add_task(run_evaluation_job, job_id, request)
    return {"job_id": job_id, "status": "started"}
```

**Work scales across request-selected models and inputs** — `app.py:289-318`

Each model/input pair triggers a provider call and stores an output.

```python
results = []
total = len(request.models)

for i, model_name in enumerate(request.models):
    model = get_model(model_name)
    model_outputs = []

    for text in inputs:
        rendered = render_prompt(base_prompt, {input_var: text})
        raw = model.run(rendered, constraints)
        score = evaluate(raw["output"], constraints, text, task_type)

        model_outputs.append({
            "input": text,
            "output": raw["output"],
            "score": score.score,
            "breakdown": score.breakdown,
            "tokens": raw["tokens"],
            "latency_ms": raw["latency_ms"]
        })
```

**Job state is held in a process-global map** — `app.py:60-65`

Jobs and completed results are written to `jobs`; repository-wide search found no eviction/deletion path.

```python
# GLOBAL STATE
jobs = {}
registry = PromptRegistry()
executor = PromptExecutor()
```

**Job endpoint returns stored result** — `app.py:175-180`

The requestor receives the returned job ID and can poll the stored data.

```python
@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
```

#### Validation

Review connected unbounded request dimensions to per-model/per-input provider calls and persistent in-memory job results. Search found initialization and access of `jobs` but no deletion/eviction operation.

Validation method: Static source trace and repository-wide reference search

**Evaluation request has unbounded arrays and count** — `app.py:76-84`

`models`, `test_inputs`, and `test_case_count` have no maximum bounds.

```python
class EvaluationRequest(BaseModel):
    task: str
    version: str
    models: List[str]
    test_inputs: Optional[List[str]] = None
    generate_test_cases: bool = True
    test_case_count: int = 3
    custom_prompt: Optional[str] = None
    custom_constraints: Optional[dict] = None
```

**Evolution request has unbounded limits and inputs** — `app.py:95-105`

The caller controls iteration/count values and an optional input list without enforced bounds.

```python
class EvolutionRequest(BaseModel):
    task: str
    version: str
    model: str
    optimizer_model: str = "command-a-03-2025"
    max_iterations: int = 3
    test_case_count: int = 3
    min_delta: float = 0.25
    custom_prompt: Optional[str] = None
    custom_constraints: Optional[dict] = None
    test_inputs: Optional[List[str]] = None
```

**Each evaluation request allocates and queues a job** — `app.py:183-194`

Each accepted request allocates memory and schedules work without a visible handler-level queue or quota check.

```python
@app.post("/api/evaluate")
async def evaluate_prompt(request: EvaluationRequest, bg: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "running",
        "progress": 0,
        "results": None,
        "error": None,
        "started_at": datetime.utcnow().isoformat()
    }
    bg.add_task(run_evaluation_job, job_id, request)
    return {"job_id": job_id, "status": "started"}
```

**Work scales across request-selected models and inputs** — `app.py:289-318`

Each model/input pair triggers a provider call and stores an output.

```python
results = []
total = len(request.models)

for i, model_name in enumerate(request.models):
    model = get_model(model_name)
    model_outputs = []

    for text in inputs:
        rendered = render_prompt(base_prompt, {input_var: text})
        raw = model.run(rendered, constraints)
        score = evaluate(raw["output"], constraints, text, task_type)

        model_outputs.append({
            "input": text,
            "output": raw["output"],
            "score": score.score,
            "breakdown": score.breakdown,
            "tokens": raw["tokens"],
            "latency_ms": raw["latency_ms"]
        })
```

**Job state is held in a process-global map** — `app.py:60-65`

Jobs and completed results are written to `jobs`; repository-wide search found no eviction/deletion path.

```python
# GLOBAL STATE
jobs = {}
registry = PromptRegistry()
executor = PromptExecutor()
```

**Job endpoint returns stored result** — `app.py:175-180`

The requestor receives the returned job ID and can poll the stored data.

```python
@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
```

Assertions:
- Request model arrays and work-count integers have no maximum bounds.
- The evaluation loop calls `model.run()` per model/input pair.
- Each accepted request allocates state and queues background work.
- No job cleanup path was found.

Limitations:
- Live availability impact and upstream request controls were not measured.
- Active provider credentials and quotas are unknown.

#### Dataflow

Unbounded JSON fields -\> job allocation -\> nested model/input work -\> retained job outputs

- **Source:** Request arrays and integer work limits

- **Sink:** Model adapter calls, process CPU/memory, and global job storage

- **Outcome:** Availability degradation and possible provider quota/spend exhaustion

**Evaluation request has unbounded arrays and count** — `app.py:76-84`

`models`, `test_inputs`, and `test_case_count` have no maximum bounds.

```python
class EvaluationRequest(BaseModel):
    task: str
    version: str
    models: List[str]
    test_inputs: Optional[List[str]] = None
    generate_test_cases: bool = True
    test_case_count: int = 3
    custom_prompt: Optional[str] = None
    custom_constraints: Optional[dict] = None
```

**Each evaluation request allocates and queues a job** — `app.py:183-194`

Each accepted request allocates memory and schedules work without a visible handler-level queue or quota check.

```python
@app.post("/api/evaluate")
async def evaluate_prompt(request: EvaluationRequest, bg: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "running",
        "progress": 0,
        "results": None,
        "error": None,
        "started_at": datetime.utcnow().isoformat()
    }
    bg.add_task(run_evaluation_job, job_id, request)
    return {"job_id": job_id, "status": "started"}
```

**Work scales across request-selected models and inputs** — `app.py:289-318`

Each model/input pair triggers a provider call and stores an output.

```python
results = []
total = len(request.models)

for i, model_name in enumerate(request.models):
    model = get_model(model_name)
    model_outputs = []

    for text in inputs:
        rendered = render_prompt(base_prompt, {input_var: text})
        raw = model.run(rendered, constraints)
        score = evaluate(raw["output"], constraints, text, task_type)

        model_outputs.append({
            "input": text,
            "output": raw["output"],
            "score": score.score,
            "breakdown": score.breakdown,
            "tokens": raw["tokens"],
            "latency_ms": raw["latency_ms"]
        })
```

**Job state is held in a process-global map** — `app.py:60-65`

Jobs and completed results are written to `jobs`; repository-wide search found no eviction/deletion path.

```python
# GLOBAL STATE
jobs = {}
registry = PromptRegistry()
executor = PromptExecutor()
```

**Job endpoint returns stored result** — `app.py:175-180`

The requestor receives the returned job ID and can poll the stored data.

```python
@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
```

**Evolution request has unbounded limits and inputs** — `app.py:95-105`

The caller controls iteration/count values and an optional input list without enforced bounds.

```python
class EvolutionRequest(BaseModel):
    task: str
    version: str
    model: str
    optimizer_model: str = "command-a-03-2025"
    max_iterations: int = 3
    test_case_count: int = 3
    min_delta: float = 0.25
    custom_prompt: Optional[str] = None
    custom_constraints: Optional[dict] = None
    test_inputs: Optional[List[str]] = None
```

#### Reachability

No in-handler authentication or quota is present in reviewed routes; exposure and upstream protections are unknown.

- **Attacker:** Unauthenticated network caller

- **Entry point:** POST `/api/evaluate`, `/api/compare`, `/api/evolve`, or `/api/test-cases/generate`

- **Outcome:** Unbounded background work and retained result growth

Preconditions:
- Service is reachable by attacker.
- No upstream access, body-size, rate, or concurrency control caps the workload.

Limitations:
- Provider-cost impact is conditional on active credentials and billing configuration.

#### Severity

**High** — Repeated requests can multiply model/input loops and grow retained state, affecting service availability; provider spend is conditional on configured credentials and quotas.

Lower if effective upstream authentication, request limits, concurrency controls, quotas, and job expiry exist in deployment.

Impact assessment:
- **Level:** high
- **Why:** Repeated requests can consume shared server resources; configured external model credentials may also incur cost or exhaust quota.

Likelihood assessment:
- **Level:** medium
- **Why:** The code accepts and schedules unbounded work, but deployed request controls and credentials are unknown.

#### Remediation

Require authentication and per-caller quotas, bound request sizes and numeric work fields, run jobs through a bounded queue with concurrency/time limits, and expire completed job records and outputs.

Tests:
- Reject arrays and iteration/test-case counts above explicit limits before queuing.
- Verify concurrent submissions are bounded.
- Verify completed jobs and outputs expire after the configured retention window.

Preventive controls:
- Alert on provider spend and per-caller job volume.
- Use provider quotas and a circuit breaker for model calls.

<a id="finding-3"></a>

### [3] Prompt registry accepts paths outside its versions directory

| Field | Value |
| --- | --- |
| Severity | medium |
| Confidence | high |
| Confidence rationale | Path construction and file open are explicit; harmless stdlib path composition confirmed escape is possible. Actual sensitive file contents and deployment reachability are unknown. |
| Category | path-traversal |
| CWE | CWE-22 |
| Affected lines | app.py:95-105, prompts/registry.py:10-20, prompts/registry.py:25-38 |

#### Summary

An unauthenticated evolution request controls `task` and `version`; `PromptRegistry.load()` joins them into a filesystem path without canonical containment validation. Traversal can make the service load a compatible YAML file outside `prompts/versions`; selected template metadata can then appear in the evolution result. No sensitive external file was read during review.

#### Root Cause

`PromptRegistry.load()` treats caller-controlled `task` and `version` as path components, opens the joined path without canonicalizing or checking that it stays under the registry root, and returns selected YAML fields to evolution. Results expose the prompt history.

**Request accepts task and version strings** — `app.py:95-105`

The request model does not constrain `task` or `version` to registered identifiers.

```python
class EvolutionRequest(BaseModel):
    task: str
    version: str
    model: str
    optimizer_model: str = "command-a-03-2025"
    max_iterations: int = 3
    test_case_count: int = 3
    min_delta: float = 0.25
    custom_prompt: Optional[str] = None
    custom_constraints: Optional[dict] = None
    test_inputs: Optional[List[str]] = None
```

**Evolution uses request values for registry load** — `app.py:406-415`

Without `custom_prompt`, caller values reach `load_with_metadata()`.

```python
if request.custom_prompt:
    base_prompt = request.custom_prompt
    constraints = request.custom_constraints or {"temperature": 0.0, "max_tokens": 256}
    task_type = "generation"
    input_vars = ["text"]
else:
    meta = registry.load_with_metadata(request.task, request.version)
    base_prompt = meta["template"]
```

**Registry joins values and opens resulting file** — `prompts/registry.py:10-23`

The path is opened without resolving it against the registry root or checking containment.

```python
def load(self, task: str, version: str):
    key = f"{task}:{version}"
    if key in self._cache:
        return self._cache[key]

    path = PROMPT_BASE_PATH / task / f"{version}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")

    with open(path, "r") as f:
        prompt = yaml.safe_load(f)

    self._cache[key] = prompt
    return prompt
```

**Loaded YAML template is copied into metadata** — `prompts/registry.py:25-40`

Selected fields, including `template`, flow into the evolution job.

```python
def load_with_metadata(self, task: str, version: str) -> dict:
    prompt_def = self.load(task, version)

    metadata = {
        "task": prompt_def.get("task"),
        "task_type": prompt_def.get("task_type"),
        "input_variables": prompt_def.get("input_variables", []),
        "schema_fields": (
            prompt_def.get("output_schema", {})
            .get("fields", [])
        ),
        "constraints": prompt_def.get("constraints", {}),
        "template": prompt_def.get("template")
    }

    return metadata
```

**Evolution result contains prompt history** — `app.py:454-463`

The requestor can retrieve the job ID returned by the route and receive prompt history.

```python
jobs[job_id].update({
    "status": "completed",
    "progress": 100,
    "results": {
        "history": history,
        "initial_score": history[0]["score"],
        "final_score": history[-1]["score"],
        "improvement": history[-1]["score"] - history[0]["score"],
        "final_prompt": history[-1]["prompt"]
    },
```

#### Validation

Source confirms request-controlled components reach `open()` without containment validation. A standard-library path composition check showed traversal can escape; no external file was opened or disclosed.

Validation method: Static source trace and harmless path composition

**Request accepts task and version strings** — `app.py:95-105`

The request model does not constrain `task` or `version` to registered identifiers.

```python
class EvolutionRequest(BaseModel):
    task: str
    version: str
    model: str
    optimizer_model: str = "command-a-03-2025"
    max_iterations: int = 3
    test_case_count: int = 3
    min_delta: float = 0.25
    custom_prompt: Optional[str] = None
    custom_constraints: Optional[dict] = None
    test_inputs: Optional[List[str]] = None
```

**Evolution uses request values for registry load** — `app.py:406-415`

Without `custom_prompt`, caller values reach `load_with_metadata()`.

```python
if request.custom_prompt:
    base_prompt = request.custom_prompt
    constraints = request.custom_constraints or {"temperature": 0.0, "max_tokens": 256}
    task_type = "generation"
    input_vars = ["text"]
else:
    meta = registry.load_with_metadata(request.task, request.version)
    base_prompt = meta["template"]
```

**Registry joins values and opens resulting file** — `prompts/registry.py:10-23`

The path is opened without resolving it against the registry root or checking containment.

```python
def load(self, task: str, version: str):
    key = f"{task}:{version}"
    if key in self._cache:
        return self._cache[key]

    path = PROMPT_BASE_PATH / task / f"{version}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")

    with open(path, "r") as f:
        prompt = yaml.safe_load(f)

    self._cache[key] = prompt
    return prompt
```

**Loaded YAML template is copied into metadata** — `prompts/registry.py:25-40`

Selected fields, including `template`, flow into the evolution job.

```python
def load_with_metadata(self, task: str, version: str) -> dict:
    prompt_def = self.load(task, version)

    metadata = {
        "task": prompt_def.get("task"),
        "task_type": prompt_def.get("task_type"),
        "input_variables": prompt_def.get("input_variables", []),
        "schema_fields": (
            prompt_def.get("output_schema", {})
            .get("fields", [])
        ),
        "constraints": prompt_def.get("constraints", {}),
        "template": prompt_def.get("template")
    }

    return metadata
```

**Evolution result contains prompt history** — `app.py:454-463`

The requestor can retrieve the job ID returned by the route and receive prompt history.

```python
jobs[job_id].update({
    "status": "completed",
    "progress": 100,
    "results": {
        "history": history,
        "initial_score": history[0]["score"],
        "final_score": history[-1]["score"],
        "improvement": history[-1]["score"] - history[0]["score"],
        "final_prompt": history[-1]["prompt"]
    },
```

Assertions:
- Path construction uses request values without canonical containment checks.
- Loaded YAML `template` flows into job results.

Limitations:
- Disclosure requires a readable compatible YAML mapping outside the registry root.
- No sensitive external file was read; deployment reachability is unknown.

#### Dataflow

`task/version` -\> `PromptRegistry.load()` -\> `open()`/`safe_load()` -\> metadata -\> evolution job

- **Source:** Caller-controlled task/version strings

- **Sink:** Filesystem open outside prompt root

- **Outcome:** Selected YAML prompt metadata disclosure

**Evolution uses request values for registry load** — `app.py:406-415`

Without `custom_prompt`, caller values reach `load_with_metadata()`.

```python
if request.custom_prompt:
    base_prompt = request.custom_prompt
    constraints = request.custom_constraints or {"temperature": 0.0, "max_tokens": 256}
    task_type = "generation"
    input_vars = ["text"]
else:
    meta = registry.load_with_metadata(request.task, request.version)
    base_prompt = meta["template"]
```

**Registry joins values and opens resulting file** — `prompts/registry.py:10-23`

The path is opened without resolving it against the registry root or checking containment.

```python
def load(self, task: str, version: str):
    key = f"{task}:{version}"
    if key in self._cache:
        return self._cache[key]

    path = PROMPT_BASE_PATH / task / f"{version}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")

    with open(path, "r") as f:
        prompt = yaml.safe_load(f)

    self._cache[key] = prompt
    return prompt
```

**Evolution result contains prompt history** — `app.py:454-463`

The requestor can retrieve the job ID returned by the route and receive prompt history.

```python
jobs[job_id].update({
    "status": "completed",
    "progress": 100,
    "results": {
        "history": history,
        "initial_score": history[0]["score"],
        "final_score": history[-1]["score"],
        "improvement": history[-1]["score"] - history[0]["score"],
        "final_prompt": history[-1]["prompt"]
    },
```

**Request accepts task and version strings** — `app.py:95-105`

The request model does not constrain `task` or `version` to registered identifiers.

```python
class EvolutionRequest(BaseModel):
    task: str
    version: str
    model: str
    optimizer_model: str = "command-a-03-2025"
    max_iterations: int = 3
    test_case_count: int = 3
    min_delta: float = 0.25
    custom_prompt: Optional[str] = None
    custom_constraints: Optional[dict] = None
    test_inputs: Optional[List[str]] = None
```

**Loaded YAML template is copied into metadata** — `prompts/registry.py:25-40`

Selected fields, including `template`, flow into the evolution job.

```python
def load_with_metadata(self, task: str, version: str) -> dict:
    prompt_def = self.load(task, version)

    metadata = {
        "task": prompt_def.get("task"),
        "task_type": prompt_def.get("task_type"),
        "input_variables": prompt_def.get("input_variables", []),
        "schema_fields": (
            prompt_def.get("output_schema", {})
            .get("fields", [])
        ),
        "constraints": prompt_def.get("constraints", {}),
        "template": prompt_def.get("template")
    }

    return metadata
```

#### Reachability

The route has no route-level authentication; live exposure and upstream controls are unknown.

- **Attacker:** Unauthenticated network caller

- **Entry point:** POST `/api/evolve`, then poll returned job ID

- **Outcome:** Read selected metadata from a compatible YAML file outside `prompts/versions`

Preconditions:
- Service is reachable by attacker.
- A compatible readable YAML mapping exists outside the intended directory.

Limitations:
- No particular secret or sensitive external file is established as readable.

#### Severity

**Medium** — A reachable caller may disclose selected fields from a compatible YAML file outside the intended registry; write and availability impact were not established.

Lower if upstream access control prevents untrusted requests or filesystem permissions make compatible sensitive YAML unavailable.

Impact assessment:
- **Level:** medium
- **Why:** Confidentiality of selected compatible prompt metadata can be lost; no file modification or arbitrary raw-file disclosure was established.

Likelihood assessment:
- **Level:** medium
- **Why:** Traversal is source-confirmed, but a sensitive compatible file and deployment reachability were not verified.

#### Remediation

Resolve the candidate path and reject it unless it is a descendant of `PROMPT_BASE_PATH.resolve()`; restrict `task` and `version` to approved registry identifiers.

Tests:
- Verify valid registered prompts load.
- Verify absolute paths and `../` in either path component are rejected before file access.

Preventive controls:
- Route all prompt-file reads through one helper that enforces canonical root containment.

## Reviewed Surfaces

| Surface | Risk Area | Outcome | Notes |
| --- | --- | --- | --- |
| FastAPI prompt evaluation and Jinja rendering | Untrusted template execution | Reported | Unsandboxed Jinja receives caller-controlled custom prompts. |
| Prompt registry path construction and YAML loading | Filesystem containment | Reported | Caller task/version strings reach path construction without containment validation. |
| Request-driven model work and job retention | Resource consumption | Reported | Unbounded work and retained results; deployed controls and credentials unknown. |
| Browser rendering of evaluation/evolution output | Cross-site scripting | Rejected | Unescaped innerHTML candidate had no cross-user delivery path; it requires victim-induced attacker prompt input and was treated as self-XSS. |
| Tracked text and SQLite data artifacts | Credential or sensitive-data exposure | No issue found | Read-only review found no directly recognizable credential values; deployment secrets were not inspected. |
| SQLite queries and YAML loading | Injection and unsafe deserialization | No issue found | No SQL injection confirmed; registry uses yaml.safe_load. |
