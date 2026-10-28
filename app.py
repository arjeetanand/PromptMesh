from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from typing import List, Literal, Optional
from pathlib import Path
from datetime import datetime
import asyncio
import hashlib
import hmac
import ipaddress
import os
import threading


# ============================================================
# PROJECT IMPORTS
# ============================================================
from prompts.registry import PromptRegistry
from core.types import render_prompt
from core.security import (
    CallerJobLimitError,
    JobStore,
    MAX_ACTIVE_JOBS_PER_CALLER,
    MAX_EVOLUTION_INPUTS,
    MAX_EVOLUTION_ITERATIONS,
    MAX_INPUT_CHARS,
    MAX_MODELS,
    MAX_OUTPUT_TOKENS,
    MAX_PROMPT_CHARS,
    MAX_REQUESTS_PER_MINUTE,
    MAX_TEST_INPUTS,
    RequestBodyLimitMiddleware,
    RequestRateLimiter,
    ServerJobLimitError,
)
from core.executor import PromptExecutor
from evaluation.scorer import evaluate
from comparison.runner import run_prompt_comparison
from optimization.failure_analysis import analyze_failure
from optimization.evolver import evolve_prompt
from optimization.testcase_generator import generate_test_cases
from models.registry import get_model
from training.datasets import benchmark_card_status, list_datasets, load_dataset, load_dataset_snapshot, split_dataset
from training.benchmark import (
    MAX_PROMPT_CANDIDATES,
    load_prompt_selection,
    run_frozen_benchmark,
    run_prompt_selection,
    validate_prompt_template,
)
from training.runner import run_lora_training, training_runtime
from training.registry import get_benchmark_adapter, list_adapters


# ============================================================
# PATH CONFIGURATION
# ============================================================
BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"

if not STATIC_DIR.exists():
    raise RuntimeError("Missing static/ folder. Create static/index.html, styles.css, app.js")


# ============================================================
# FASTAPI APP
# ============================================================
app = FastAPI(title="PromptMesh", version="1.0.0")


# ============================================================
# CORS
# ============================================================
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("PROMPTMESH_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(RequestBodyLimitMiddleware)


# ============================================================
# STATIC FILE SERVING
# ============================================================
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ============================================================
# GLOBAL STATE
# ============================================================
API_KEY = os.environ.get("PROMPTMESH_API_KEY", "").strip() or None
if API_KEY and len(API_KEY) < 32:
    raise RuntimeError("PROMPTMESH_API_KEY must contain at least 32 characters")

jobs = JobStore()
TRAINING_LOCK = threading.Lock()
registry = PromptRegistry()
executor = PromptExecutor()
request_limiter = RequestRateLimiter(limit=MAX_REQUESTS_PER_MINUTE)
login_limiter = RequestRateLimiter(limit=5, window_seconds=300, max_callers=4096)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _is_loopback_request(request: Request) -> bool:
    try:
        client_is_local = ipaddress.ip_address(_client_ip(request)).is_loopback
    except ValueError:
        client_is_local = False
    return client_is_local and request.url.hostname in {"localhost", "127.0.0.1", "::1"}


def _has_valid_api_key(request: Request) -> bool:
    authorization = request.headers.get("authorization", "")
    scheme, _, supplied = authorization.partition(" ")
    return bool(
        API_KEY
        and scheme.lower() == "bearer"
        and supplied
        and hmac.compare_digest(supplied.encode("utf-8"), API_KEY.encode("utf-8"))
    )


@app.middleware("http")
async def enforce_api_access(request: Request, call_next):
    path = request.url.path
    if path.startswith("/api/") and path not in {"/api/health", "/api/session"}:
        origin = request.headers.get("origin")
        expected_origin = f"{request.url.scheme}://{request.headers.get('host', '')}"
        if origin and origin != expected_origin and (not API_KEY or origin not in ALLOWED_ORIGINS):
            return JSONResponse({"detail": "Cross-origin API access is not allowed"}, status_code=403)
        if API_KEY:
            if not _has_valid_api_key(request):
                return JSONResponse(
                    {"detail": "A valid Bearer API key is required"},
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"},
                )
            identity = hashlib.sha256(
                f"{API_KEY}\0{_client_ip(request)}".encode("utf-8")
            ).hexdigest()
        else:
            if not _is_loopback_request(request):
                return JSONResponse(
                    {"detail": "Remote API access requires PROMPTMESH_API_KEY"},
                    status_code=403,
                )
            identity = f"local:{_client_ip(request)}"
        request.state.caller_id = identity
    return await call_next(request)


def _caller_id(request: Request) -> str:
    return request.state.caller_id


def _enforce_request_quota(request: Request):
    if not request_limiter.allow(_caller_id(request)):
        raise HTTPException(status_code=429, detail="Request limit exceeded; retry in one minute")


def _validate_text_values(values, label, *, max_length):
    if values is None:
        return
    for value in values:
        if len(value) > max_length:
            raise HTTPException(
                status_code=422,
                detail=f"Each {label} value must be at most {max_length} characters",
            )


def _validate_custom_constraints(constraints):
    if not constraints:
        return
    max_tokens = constraints.get("max_tokens")
    if max_tokens is not None:
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int):
            raise HTTPException(status_code=422, detail="max_tokens must be an integer")
        if not 1 <= max_tokens <= MAX_OUTPUT_TOKENS:
            raise HTTPException(
                status_code=422,
                detail=f"max_tokens must be between 1 and {MAX_OUTPUT_TOKENS}",
            )


def _admit_job(request: Request) -> str:
    _enforce_request_quota(request)
    try:
        return jobs.create(_caller_id(request))
    except CallerJobLimitError as exc:
        raise HTTPException(
            status_code=429,
            detail=f"At most {MAX_ACTIVE_JOBS_PER_CALLER} jobs may run per caller",
        ) from exc
    except ServerJobLimitError as exc:
        raise HTTPException(status_code=503, detail="The job capacity is full") from exc


def _run_admitted_job(job_id, runner, request_model):
    try:
        runner(job_id, request_model)
    finally:
        jobs.finish(job_id)


def _run_admitted_training_job(job_id, request_model):
    _run_admitted_local_model_job(job_id, run_lora_training, request_model)


def _run_admitted_local_model_job(job_id, runner, request_model):
    try:
        runner(job_id, request_model, jobs)
    finally:
        jobs.finish(job_id)
        TRAINING_LOCK.release()


async def _expire_jobs():
    while True:
        await asyncio.sleep(60)
        jobs.prune()


_job_cleanup_task = None


@app.on_event("startup")
async def start_job_cleanup():
    global _job_cleanup_task
    _job_cleanup_task = asyncio.create_task(_expire_jobs())


@app.on_event("shutdown")
async def stop_job_cleanup():
    if _job_cleanup_task:
        _job_cleanup_task.cancel()
        try:
            await _job_cleanup_task
        except asyncio.CancelledError:
            pass


# ============================================================
# REQUEST MODELS
# ============================================================
class PromptVersionRequest(BaseModel):
    task: str = Field(min_length=1, max_length=64)
    version: str = Field(min_length=1, max_length=64)


class EvaluationRequest(BaseModel):
    task: str = Field(min_length=1, max_length=64)
    version: str = Field(min_length=1, max_length=64)
    models: List[str] = Field(min_length=1, max_length=MAX_MODELS)
    test_inputs: Optional[List[str]] = Field(default=None, max_length=MAX_TEST_INPUTS)
    generate_test_cases: bool = True
    test_case_count: int = Field(default=3, ge=0, le=MAX_TEST_INPUTS)
    custom_prompt: Optional[str] = Field(default=None, max_length=MAX_PROMPT_CHARS)
    custom_constraints: Optional[dict] = Field(default=None, max_length=32)


class ComparisonRequest(BaseModel):
    task: str = Field(min_length=1, max_length=64)
    versions: List[str] = Field(min_length=1, max_length=MAX_MODELS)
    models: List[str] = Field(min_length=1, max_length=MAX_MODELS)
    test_input: str = Field(max_length=MAX_INPUT_CHARS)
    custom_prompts: Optional[dict[str, str]] = Field(default=None, max_length=MAX_MODELS)


class EvolutionRequest(BaseModel):
    task: str = Field(min_length=1, max_length=64)
    version: str = Field(min_length=1, max_length=64)
    model: str = Field(min_length=1, max_length=128)
    optimizer_model: str = Field(default="command-a-03-2025", min_length=1, max_length=128)
    max_iterations: int = Field(default=3, ge=0, le=MAX_EVOLUTION_ITERATIONS)
    test_case_count: int = Field(default=3, ge=0, le=MAX_TEST_INPUTS)
    min_delta: float = Field(default=0.25, ge=0, le=1)
    custom_prompt: Optional[str] = Field(default=None, max_length=MAX_PROMPT_CHARS)
    custom_constraints: Optional[dict] = Field(default=None, max_length=32)
    test_inputs: Optional[List[str]] = Field(default=None, max_length=MAX_EVOLUTION_INPUTS)


class TestCaseGenerationRequest(BaseModel):
    task_type: str = Field(min_length=1, max_length=64)
    base_inputs: List[str] = Field(min_length=1, max_length=MAX_TEST_INPUTS)
    schema_fields: Optional[List[str]] = Field(default=None, max_length=32)
    count: int = Field(default=5, ge=1, le=MAX_TEST_INPUTS)


class FineTuneRequest(BaseModel):
    dataset_id: str = Field(min_length=1, max_length=64)
    epochs: int = Field(default=1, ge=1, le=3)
    learning_rate: float = Field(default=0.0002, gt=0, le=0.0005)
    lora_rank: Literal[4, 8, 16] = 8


class PromptSelectionRequest(BaseModel):
    dataset_id: str = Field(min_length=1, max_length=64)
    adapter_run_id: str = Field(min_length=32, max_length=32)
    candidate_prompts: List[str] = Field(min_length=1, max_length=MAX_PROMPT_CANDIDATES)


class FrozenBenchmarkRequest(BaseModel):
    selection_id: str = Field(min_length=32, max_length=32)
    adapter_run_id: str = Field(min_length=32, max_length=32)


class ApiSessionRequest(BaseModel):
    api_key: str = Field(min_length=32, max_length=256)


# ============================================================
# ROUTES
# ============================================================
@app.get("/")
async def root():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def health_check(request: Request):
    auth_required = API_KEY is not None or not _is_loopback_request(request)
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "auth_required": auth_required,
        "remote_access_enabled": API_KEY is not None or _is_loopback_request(request),
    }


@app.get("/api/session")
async def session_status(request: Request):
    local_access = _is_loopback_request(request)
    auth_required = API_KEY is not None or not local_access
    return {
        "auth_required": auth_required,
        "authenticated": (API_KEY is None and local_access) or _has_valid_api_key(request),
    }


@app.post("/api/session")
async def create_session(request: Request, credentials: ApiSessionRequest):
    if API_KEY is None:
        if _is_loopback_request(request):
            return {"auth_required": False, "authenticated": True}
        raise HTTPException(status_code=403, detail="Set PROMPTMESH_API_KEY for remote access")
    caller = f"login:{_client_ip(request)}"
    if not login_limiter.allow(caller):
        raise HTTPException(status_code=429, detail="Too many authentication attempts")
    if not hmac.compare_digest(credentials.api_key.encode("utf-8"), API_KEY.encode("utf-8")):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return {"auth_required": True, "authenticated": True}


@app.get("/api/tasks/{task}/versions/{version}/prompt")
async def get_prompt_content(task: str, version: str):
    """Get the full prompt template for editing"""
    try:
        meta = registry.load_with_metadata(task, version)
        return {
            "template": meta["template"],
            "constraints": meta["constraints"],
            "task_type": meta["task_type"],
            "input_variables": meta["input_variables"],
            "schema_fields": meta.get("schema_fields", [])
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="Prompt not found") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Prompt could not be loaded") from e


@app.get("/api/tasks")
async def get_tasks():
    try:
        tasks_dir = BASE_DIR / "prompts" / "versions"
        tasks = [d.name for d in tasks_dir.iterdir() if d.is_dir()]
        return {"tasks": tasks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tasks/{task}/versions")
async def get_task_versions(task: str):
    try:
        return {"versions": registry.list_versions(task)}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="Prompt task not found") from e


@app.get("/api/models")
async def get_models():
    from models.registry import MODEL_DEFINITIONS
    trained = [adapter["id"] for adapter in list_adapters()]
    return {
        "fast": ["llama3.2:latest"],
        "mid": ["qwen2.5:latest"],
        "heavy": ["command-a-03-2025"],
        "all": list(MODEL_DEFINITIONS.keys()) + trained,
    }


@app.get("/api/training/datasets")
async def get_training_datasets():
    return {"datasets": list_datasets(), "runtime": training_runtime()}


@app.get("/api/training/adapters")
async def get_training_adapters():
    return {"adapters": list_adapters()}


@app.post("/api/training/jobs")
async def start_training(request: FineTuneRequest, bg: BackgroundTasks, http_request: Request):
    runtime = training_runtime()
    if not runtime["available"]:
        missing = ", ".join(runtime["missing"])
        raise HTTPException(status_code=503, detail=f"Local training dependencies are missing: {missing}")
    try:
        split_dataset(load_dataset(request.dataset_id))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Training dataset not found") from exc
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not TRAINING_LOCK.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="A local fine-tuning job is already running")
    job_id = None
    try:
        job_id = _admit_job(http_request)
        bg.add_task(_run_admitted_training_job, job_id, request)
    except Exception:
        if job_id:
            jobs.finish(job_id)
        TRAINING_LOCK.release()
        raise
    return {"job_id": job_id, "status": "started"}


@app.post("/api/training/prompt-selections")
async def start_prompt_selection(request: PromptSelectionRequest, bg: BackgroundTasks, http_request: Request):
    _validate_text_values(request.candidate_prompts, "prompt candidate", max_length=MAX_PROMPT_CHARS)
    try:
        for prompt in request.candidate_prompts:
            validate_prompt_template(prompt)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        rows, digest = load_dataset_snapshot(request.dataset_id)
        card = benchmark_card_status(request.dataset_id, rows, digest)
        if not card["card_ready"]:
            raise HTTPException(status_code=422, detail=card.get("reason") or "A matching review card is required")
        if not card["validation_ready"] or not card["final_test_ready"]:
            raise HTTPException(status_code=422, detail="Validation and final-test splits each need at least 30 examples across 10 source groups")
        get_benchmark_adapter(request.adapter_run_id, request.dataset_id, digest)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Dataset or adapter not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _schedule_local_model_job(bg, http_request, request, run_prompt_selection)


@app.post("/api/training/benchmarks")
async def start_frozen_benchmark(request: FrozenBenchmarkRequest, bg: BackgroundTasks, http_request: Request):
    try:
        selection = load_prompt_selection(request.selection_id)
        if request.adapter_run_id != selection["adapter_run_id"]:
            raise ValueError("The benchmark adapter must match validation prompt selection")
        rows, digest = load_dataset_snapshot(selection["dataset_id"])
        card = benchmark_card_status(selection["dataset_id"], rows, digest)
        if not card["card_ready"] or digest != selection["dataset_sha256"] or card.get("card_sha256") != selection["benchmark_card_sha256"]:
            raise ValueError("Dataset or benchmark card changed after validation prompt selection")
        get_benchmark_adapter(request.adapter_run_id, selection["dataset_id"], digest)
        if not card["validation_ready"] or not card["final_test_ready"]:
            raise ValueError("Validation and final-test splits each need at least 30 examples across 10 source groups")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Dataset or adapter not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _schedule_local_model_job(bg, http_request, request, run_frozen_benchmark)


def _schedule_local_model_job(bg, http_request, request, runner):
    runtime = training_runtime()
    if not runtime["available"]:
        missing = ", ".join(runtime["missing"])
        raise HTTPException(status_code=503, detail=f"Local model dependencies are missing: {missing}")
    if not TRAINING_LOCK.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="A local model job is already running")
    job_id = None
    try:
        job_id = _admit_job(http_request)
        bg.add_task(_run_admitted_local_model_job, job_id, runner, request)
    except Exception:
        if job_id:
            jobs.finish(job_id)
        TRAINING_LOCK.release()
        raise
    return {"job_id": job_id, "status": "started"}


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str, request: Request):
    job = jobs.get(job_id, _caller_id(request))
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.post("/api/evaluate")
async def evaluate_prompt(request: EvaluationRequest, bg: BackgroundTasks, http_request: Request):
    _validate_text_values(request.models, "model name", max_length=128)
    _validate_text_values(request.test_inputs, "test input", max_length=MAX_INPUT_CHARS)
    _validate_custom_constraints(request.custom_constraints)
    if request.test_inputs and request.generate_test_cases:
        if len(request.test_inputs) + request.test_case_count > MAX_TEST_INPUTS:
            raise HTTPException(
                status_code=422,
                detail=f"Manual and generated test inputs may total at most {MAX_TEST_INPUTS}",
            )
    if not request.test_inputs and request.test_case_count == 0:
        raise HTTPException(status_code=422, detail="At least one test case is required")

    job_id = _admit_job(http_request)
    bg.add_task(_run_admitted_job, job_id, run_evaluation_job, request)
    return {"job_id": job_id, "status": "started"}


@app.post("/api/compare")
async def compare_prompt(request: ComparisonRequest, bg: BackgroundTasks, http_request: Request):
    _validate_text_values(request.models, "model name", max_length=128)
    _validate_text_values(request.versions, "prompt version", max_length=64)
    _validate_text_values([request.test_input], "test input", max_length=MAX_INPUT_CHARS)
    if request.custom_prompts:
        if any(len(version) > 64 for version in request.custom_prompts):
            raise HTTPException(status_code=422, detail="Prompt version names must be at most 64 characters")
        _validate_text_values(request.custom_prompts.values(), "custom prompt", max_length=MAX_PROMPT_CHARS)

    job_id = _admit_job(http_request)
    bg.add_task(_run_admitted_job, job_id, run_comparison_job, request)
    return {"job_id": job_id, "status": "started"}


@app.post("/api/evolve")
async def evolve_prompt_api(request: EvolutionRequest, bg: BackgroundTasks, http_request: Request):
    _validate_text_values([request.model, request.optimizer_model], "model name", max_length=128)
    _validate_text_values(request.test_inputs, "test input", max_length=MAX_INPUT_CHARS)
    _validate_custom_constraints(request.custom_constraints)
    if not request.test_inputs and request.test_case_count == 0:
        raise HTTPException(status_code=422, detail="At least one test case is required")

    job_id = _admit_job(http_request)
    bg.add_task(_run_admitted_job, job_id, run_evolution_job, request)
    return {"job_id": job_id, "status": "started"}


@app.post("/api/test-cases/generate")
async def generate_tests(request: TestCaseGenerationRequest, http_request: Request):
    _enforce_request_quota(http_request)
    _validate_text_values(request.base_inputs, "base input", max_length=MAX_INPUT_CHARS)
    _validate_text_values(request.schema_fields, "schema field", max_length=128)
    try:
        work_token = jobs.reserve(_caller_id(http_request))
    except CallerJobLimitError as exc:
        raise HTTPException(
            status_code=429,
            detail=f"At most {MAX_ACTIVE_JOBS_PER_CALLER} model jobs may run per caller",
        ) from exc
    except ServerJobLimitError as exc:
        raise HTTPException(status_code=503, detail="The model work capacity is full") from exc
    try:
        cases = await run_in_threadpool(
            generate_test_cases,
            task_type=request.task_type,
            input_variables=["text"],
            base_inputs=request.base_inputs,
            schema_fields=request.schema_fields,
            n=request.count,
        )
        return {"success": True, "test_cases": cases}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Test case generation failed") from e
    finally:
        jobs.release_work(work_token)


# ============================================================
# BACKGROUND JOBS
# ============================================================
def run_evaluation_job(job_id: str, request: EvaluationRequest):
    try:
        if request.custom_prompt:
            base_prompt = request.custom_prompt
            constraints = request.custom_constraints or {"temperature": 0.0, "max_tokens": 256}
            task_type = "generation"
            input_vars = ["text"]
        else:
            meta = registry.load_with_metadata(request.task, request.version)
            base_prompt = meta["template"]
            constraints = meta["constraints"]
            task_type = meta["task_type"]
            input_vars = meta["input_variables"]

        input_var = input_vars[0]

        if request.test_inputs and len(request.test_inputs) > 0:
            inputs = list(request.test_inputs)
            if request.generate_test_cases and request.test_case_count > 0:
                inputs = generate_test_cases(
                    task_type=task_type,
                    input_variables=input_vars,
                    base_inputs=request.test_inputs,
                    schema_fields=[],
                    n=len(request.test_inputs) + request.test_case_count
                )
        else:
            base_inputs = get_default_inputs(task_type)
            inputs = generate_test_cases(
                task_type=task_type,
                input_variables=input_vars,
                base_inputs=base_inputs,
                schema_fields=[],
                n=request.test_case_count
            )
            if not inputs or len(inputs) == 0:
                inputs = base_inputs[:request.test_case_count]

        if not inputs or len(inputs) == 0:
            raise ValueError("No test inputs available. Please provide manual inputs.")

        print(f"[INFO] Running evaluation with {len(inputs)} test inputs")
        jobs.update(job_id, {"progress": 20})

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

            avg_score = round(sum(x["score"] for x in model_outputs) / len(model_outputs), 2) if model_outputs else 0.0

            results.append({
                "model": model_name,
                "average_score": avg_score,
                "results": model_outputs
            })

            jobs.update(job_id, {"progress": 20 + int(((i + 1) / total) * 70)})

        results.sort(key=lambda x: x["average_score"], reverse=True)

        jobs.update(job_id, {
            "status": "completed",
            "progress": 100,
            "results": results,
            "completed_at": datetime.utcnow().isoformat()
        })

    except Exception as e:
        print(f"[ERROR] Evaluation job failed: {e}")
        import traceback
        traceback.print_exc()
        jobs.update(job_id, {
            "status": "failed",
            "progress": 100,
            "error": str(e),
            "completed_at": datetime.utcnow().isoformat()
        })


def run_comparison_job(job_id: str, request: ComparisonRequest):
    try:
        # Custom prompts mode
        if request.custom_prompts:
            results = []
            for version_name, prompt_text in request.custom_prompts.items():
                for model_name in request.models:
                    model = get_model(model_name)
                    
                    # Replace {text} placeholder
                    rendered = prompt_text.replace('{text}', request.test_input)
                    
                    # Run model
                    raw = model.run(rendered, {"temperature": 0.0, "max_tokens": 256})
                    
                    # Evaluate
                    evaluation = evaluate(raw["output"], {"temperature": 0.0}, request.test_input, "generation")
                    
                    results.append({
                        "prompt_version": version_name,
                        "model": model_name,
                        "output": raw["output"],
                        "score": evaluation.score,
                        "breakdown": evaluation.breakdown
                    })
        else:
            # YAML-based comparison
            results_obj = run_prompt_comparison(
                task=request.task,
                prompt_versions=request.versions,
                input_vars={"text": request.test_input},
                models=request.models
            )
            
            results = []
            for r in results_obj:
                results.append({
                    "prompt_version": r.prompt_version,
                    "model": r.model,
                    "output": r.output,
                    "score": r.evaluation.score,
                    "breakdown": r.evaluation.breakdown
                })

        jobs.update(job_id, {
            "status": "completed",
            "progress": 100,
            "results": results,
            "completed_at": datetime.utcnow().isoformat()
        })

    except Exception as e:
        print(f"[ERROR] Comparison job failed: {e}")
        import traceback
        traceback.print_exc()
        jobs.update(job_id, {
            "status": "failed",
            "progress": 100,
            "error": str(e),
            "completed_at": datetime.utcnow().isoformat()
        })


def run_evolution_job(job_id: str, request: EvolutionRequest):
    try:
        if request.custom_prompt:
            base_prompt = request.custom_prompt
            constraints = request.custom_constraints or {"temperature": 0.0, "max_tokens": 256}
            task_type = "generation"
            input_vars = ["text"]
        else:
            meta = registry.load_with_metadata(request.task, request.version)
            base_prompt = meta["template"]
            constraints = meta["constraints"]
            task_type = meta["task_type"]
            input_vars = meta["input_variables"]

        input_var = input_vars[0]
        jobs.update(job_id, {"progress": 20})

        if request.test_inputs and len(request.test_inputs) > 0:
            inputs = request.test_inputs
        else:
            base_inputs = get_default_inputs(task_type)
            inputs = generate_test_cases(
                task_type=task_type,
                input_variables=input_vars,
                base_inputs=base_inputs,
                schema_fields=[],
                n=request.test_case_count
            )
            if not inputs or len(inputs) == 0:
                inputs = base_inputs[:request.test_case_count]

        if not inputs:
            raise ValueError("No optimization examples available for evolution")

        print(f"[INFO] Starting prompt evolution with {len(inputs)} optimization inputs")

        optimizer = get_model(request.optimizer_model)
        executor_model = get_model(request.model)

        history = evolve_prompt(
            initial_prompt=base_prompt,
            task_inputs=inputs,
            constraints=constraints,
            optimizer_model=optimizer,
            execution_model=executor_model,
            input_var=input_var,
            max_iters=request.max_iterations,
            min_delta=request.min_delta
        )

        jobs.update(job_id, {
            "status": "completed",
            "progress": 100,
            "results": {
                "history": history,
                "initial_score": history[0]["score"],
                "final_score": history[-1]["score"],
                "improvement": history[-1]["score"] - history[0]["score"],
                "final_prompt": history[-1]["prompt"],
                "score_method": "llm_judge_heuristic",
                "selection_data_role": "optimization_inputs",
                "optimization_input_count": len(inputs),
            },
            "completed_at": datetime.utcnow().isoformat()
        })

    except Exception as e:
        print(f"[ERROR] Evolution job failed: {e}")
        import traceback
        traceback.print_exc()
        jobs.update(job_id, {
            "status": "failed",
            "progress": 100,
            "error": str(e),
            "completed_at": datetime.utcnow().isoformat()
        })


def get_default_inputs(task_type: str) -> List[str]:
    """Provide default test inputs for each task type"""
    defaults = {
        "summarization": [
            "In 2023, Apple reported a 10% increase in revenue while also announcing layoffs across several departments due to market uncertainty.",
            "The European Union introduced new AI regulations aimed at improving transparency and safety, though some companies expressed concerns about compliance costs."
        ],
        "extraction": [
            "In 2022, Google announced that its cloud platform achieved a 30% increase in customer adoption.",
            "Microsoft released a new product in 2023 with advanced AI capabilities."
        ],
        "classification": [
            "The product exceeded expectations and delivered outstanding performance.",
            "Customer service was slow and unhelpful."
        ],
        "verification": [
            "Claim: Tesla increased vehicle production by 50% in 2022. Source: Tesla reported significant production growth in 2022."
        ],
        "reasoning": [
            "The company improved its performance last year compared to previous years."
        ],
        "generation": [
            "Write a short motivational quote about learning.",
            "Generate a two-line product description for a smartwatch."
        ]
    }
    return defaults.get(task_type, [
        "Sample input text for testing.",
        "Another test input for evaluation."
    ])


# ============================================================
# ENTRY POINT
# ============================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
