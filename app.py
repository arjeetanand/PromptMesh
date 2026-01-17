from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
from datetime import datetime
import uuid

# ============================================================
# PROJECT IMPORTS
# ============================================================

from prompts.registry import PromptRegistry
from core.types import render_prompt
from core.executor import PromptExecutor
from evaluation.scorer import evaluate
from comparison.runner import run_prompt_comparison
from optimization.failure_analysis import analyze_failure
from optimization.evolver import evolve_prompt
from optimization.testcase_generator import generate_test_cases
from models.registry import get_model

# ============================================================
# PATH CONFIGURATION (CRITICAL FIX)
# ============================================================

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"

if not STATIC_DIR.exists():
    raise RuntimeError("Missing static/ folder. Create static/index.html, styles.css, app.js")

# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="PromptMesh",
    version="1.0.0"
)

# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# STATIC FILE SERVING (FIXED)
# ============================================================

app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static"
)

# ============================================================
# GLOBAL STATE
# ============================================================

jobs = {}
registry = PromptRegistry()
executor = PromptExecutor()

# ============================================================
# REQUEST MODELS
# ============================================================

class PromptVersionRequest(BaseModel):
    task: str
    version: str


class EvaluationRequest(BaseModel):
    task: str
    version: str
    models: List[str]
    test_inputs: Optional[List[str]] = None
    generate_test_cases: bool = True
    test_case_count: int = 3


class ComparisonRequest(BaseModel):
    task: str
    versions: List[str]
    models: List[str]
    test_input: str


class EvolutionRequest(BaseModel):
    task: str
    version: str
    model: str
    optimizer_model: str = "command-a-03-2025"
    max_iterations: int = 3
    test_case_count: int = 3
    min_delta: float = 0.25


class TestCaseGenerationRequest(BaseModel):
    task_type: str
    base_inputs: List[str]
    schema_fields: Optional[List[str]] = None
    count: int = 5

# ============================================================
# FRONTEND ENTRYPOINT (FIXED)
# ============================================================

@app.get("/")
async def root():
    return FileResponse(STATIC_DIR / "index.html")

# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }

# ============================================================
# TASKS
# ============================================================

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
        task_dir = BASE_DIR / "prompts" / "versions" / task

        versions = [
            f.stem for f in task_dir.glob("*.y*ml")
        ]

        return {"versions": versions}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# MODELS
# ============================================================

@app.get("/api/models")
async def get_models():
    from models.registry import MODEL_DEFINITIONS

    return {
        "fast": ["llama3.2:latest"],
        "mid": ["qwen2.5:latest"],
        "heavy": ["command-a-03-2025"],
        "all": list(MODEL_DEFINITIONS.keys())
    }

# ============================================================
# JOB STATUS
# ============================================================

@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):

    job = jobs.get(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job

# ============================================================
# EVALUATION
# ============================================================

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

# ============================================================
# COMPARISON
# ============================================================

@app.post("/api/compare")
async def compare_prompt(request: ComparisonRequest, bg: BackgroundTasks):

    job_id = str(uuid.uuid4())

    jobs[job_id] = {
        "status": "running",
        "progress": 0,
        "results": None,
        "error": None,
        "started_at": datetime.utcnow().isoformat()
    }

    bg.add_task(run_comparison_job, job_id, request)

    return {"job_id": job_id, "status": "started"}

# ============================================================
# EVOLUTION
# ============================================================

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

# ============================================================
# TEST CASE GENERATION
# ============================================================

@app.post("/api/test-cases/generate")
async def generate_tests(request: TestCaseGenerationRequest):

    try:
        cases = generate_test_cases(
            task_type=request.task_type,
            input_variables=["text"],
            base_inputs=request.base_inputs,
            schema_fields=request.schema_fields,
            n=request.count
        )

        return {"success": True, "test_cases": cases}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# BACKGROUND JOBS
# ============================================================

async def run_evaluation_job(job_id: str, request: EvaluationRequest):

    try:
        meta = registry.load_with_metadata(request.task, request.version)

        base_prompt = meta["template"]
        constraints = meta["constraints"]
        input_var = meta["input_variables"][0]
        task_type = meta["task_type"]

        if request.generate_test_cases:
            inputs = generate_test_cases(
                task_type=task_type,
                input_variables=meta["input_variables"],
                base_inputs=request.test_inputs or [],
                schema_fields=meta["schema_fields"],
                n=request.test_case_count
            )
        else:
            inputs = request.test_inputs

        jobs[job_id]["progress"] = 20

        results = []
        total = len(request.models)

        for i, model_name in enumerate(request.models):

            model = get_model(model_name)
            model_outputs = []

            for text in inputs:
                rendered = render_prompt(base_prompt, {input_var: text})

                raw = model.run(rendered, constraints)

                score = evaluate(
                    raw["output"],
                    constraints,
                    text,
                    task_type
                )

                model_outputs.append({
                    "input": text,
                    "output": raw["output"],
                    "score": score.score,
                    "breakdown": score.breakdown,
                    "tokens": raw["tokens"],
                    "latency_ms": raw["latency_ms"]
                })

            avg_score = sum(x["score"] for x in model_outputs) / len(model_outputs)

            results.append({
                "model": model_name,
                "average_score": round(avg_score, 2),
                "results": model_outputs
            })

            jobs[job_id]["progress"] = 20 + int(((i + 1) / total) * 70)

        results.sort(key=lambda x: x["average_score"], reverse=True)

        jobs[job_id].update({
            "status": "completed",
            "progress": 100,
            "results": results,
            "completed_at": datetime.utcnow().isoformat()
        })

    except Exception as e:
        jobs[job_id].update({
            "status": "failed",
            "progress": 100,
            "error": str(e),
            "completed_at": datetime.utcnow().isoformat()
        })


async def run_comparison_job(job_id: str, request: ComparisonRequest):

    try:
        results = run_prompt_comparison(
            task=request.task,
            prompt_versions=request.versions,
            input_vars={"text": request.test_input},
            models=request.models
        )

        formatted = []

        for r in results:
            formatted.append({
                "prompt_version": r.prompt_version,
                "model": r.model,
                "output": r.output,
                "score": r.evaluation.score,
                "breakdown": r.evaluation.breakdown
            })

        jobs[job_id].update({
            "status": "completed",
            "progress": 100,
            "results": formatted,
            "completed_at": datetime.utcnow().isoformat()
        })

    except Exception as e:
        jobs[job_id].update({
            "status": "failed",
            "progress": 100,
            "error": str(e),
            "completed_at": datetime.utcnow().isoformat()
        })


async def run_evolution_job(job_id: str, request: EvolutionRequest):

    try:
        meta = registry.load_with_metadata(request.task, request.version)

        base_prompt = meta["template"]
        constraints = meta["constraints"]
        input_var = meta["input_variables"][0]

        jobs[job_id]["progress"] = 20

        inputs = generate_test_cases(
            task_type=meta["task_type"],
            input_variables=meta["input_variables"],
            base_inputs=[],
            schema_fields=meta["schema_fields"],
            n=request.test_case_count
        )

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
            "completed_at": datetime.utcnow().isoformat()
        })

    except Exception as e:
        jobs[job_id].update({
            "status": "failed",
            "progress": 100,
            "error": str(e),
            "completed_at": datetime.utcnow().isoformat()
        })

# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
