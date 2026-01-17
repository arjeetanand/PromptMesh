from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
from datetime import datetime
import uuid

# Import your existing modules
from prompts.registry import PromptRegistry
from core.types import render_prompt
from core.executor import PromptExecutor
from evaluation.scorer import evaluate
from comparison.runner import run_prompt_comparison
from optimization.failure_analysis import analyze_failure
from optimization.evolver import evolve_prompt
from optimization.testcase_generator import generate_test_cases, detect_task_type
from models.registry import get_model

app = FastAPI(title="PromptMesh", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Global state for job tracking
jobs = {}
registry = PromptRegistry()
executor = PromptExecutor()

# ============================================================
# REQUEST/RESPONSE MODELS
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
# API ENDPOINTS
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main HTML interface"""
    with open("static/index.html", "r") as f:
        return f.read()

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/tasks")
async def get_available_tasks():
    """Get list of available tasks"""
    try:
        tasks_dir = Path("prompts/versions")
        tasks = [d.name for d in tasks_dir.iterdir() if d.is_dir()]
        return {"tasks": tasks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tasks/{task}/versions")
async def get_task_versions(task: str):
    """Get available versions for a task"""
    try:
        task_dir = Path(f"prompts/versions/{task}")
        versions = [f.stem for f in task_dir.glob("*.yaml")]
        return {"versions": versions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/prompts/load")
async def load_prompt(request: PromptVersionRequest):
    """Load a specific prompt version"""
    try:
        prompt_meta = registry.load_with_metadata(request.task, request.version)
        return {
            "success": True,
            "data": prompt_meta
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/models")
async def get_available_models():
    """Get list of available models"""
    from models.registry import MODEL_DEFINITIONS
    
    models = {
        "fast": ["llama3.2:latest"],
        "mid": ["qwen2.5:latest"],
        "heavy": ["command-a-03-2025"],
        "all": list(MODEL_DEFINITIONS.keys())
    }
    return models

@app.post("/api/evaluate")
async def evaluate_prompt(request: EvaluationRequest, background_tasks: BackgroundTasks):
    """Evaluate a prompt across models"""
    job_id = str(uuid.uuid4())
    
    jobs[job_id] = {
        "status": "running",
        "progress": 0,
        "results": None,
        "error": None,
        "started_at": datetime.now().isoformat()
    }
    
    background_tasks.add_task(run_evaluation, job_id, request)
    
    return {
        "job_id": job_id,
        "status": "started"
    }

@app.post("/api/compare")
async def compare_prompts(request: ComparisonRequest, background_tasks: BackgroundTasks):
    """Compare multiple prompt versions"""
    job_id = str(uuid.uuid4())
    
    jobs[job_id] = {
        "status": "running",
        "progress": 0,
        "results": None,
        "error": None,
        "started_at": datetime.now().isoformat()
    }
    
    background_tasks.add_task(run_comparison, job_id, request)
    
    return {
        "job_id": job_id,
        "status": "started"
    }

@app.post("/api/evolve")
async def evolve_prompt_endpoint(request: EvolutionRequest, background_tasks: BackgroundTasks):
    """Evolve a prompt to improve performance"""
    job_id = str(uuid.uuid4())
    
    jobs[job_id] = {
        "status": "running",
        "progress": 0,
        "results": None,
        "error": None,
        "started_at": datetime.now().isoformat()
    }
    
    background_tasks.add_task(run_evolution, job_id, request)
    
    return {
        "job_id": job_id,
        "status": "started"
    }

@app.post("/api/test-cases/generate")
async def generate_test_cases_endpoint(request: TestCaseGenerationRequest):
    """Generate test cases for a task"""
    try:
        test_cases = generate_test_cases(
            task_type=request.task_type,
            input_variables=["text"],
            base_inputs=request.base_inputs,
            schema_fields=request.schema_fields,
            n=request.count
        )
        
        return {
            "success": True,
            "test_cases": test_cases
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get status of a background job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return jobs[job_id]

# ============================================================
# BACKGROUND TASK FUNCTIONS
# ============================================================

async def run_evaluation(job_id: str, request: EvaluationRequest):
    """Background task for evaluation"""
    try:
        # Load prompt
        prompt_meta = registry.load_with_metadata(request.task, request.version)
        base_prompt = prompt_meta["template"]
        constraints = prompt_meta["constraints"]
        input_var = prompt_meta["input_variables"][0]
        task_type = prompt_meta["task_type"]
        
        # Generate or use provided test inputs
        if request.generate_test_cases:
            test_inputs = generate_test_cases(
                task_type=task_type,
                input_variables=prompt_meta["input_variables"],
                base_inputs=request.test_inputs or [],
                schema_fields=prompt_meta["schema_fields"],
                n=request.test_case_count
            )
        else:
            test_inputs = request.test_inputs
        
        jobs[job_id]["progress"] = 20
        
        # Evaluate across models
        results = []
        total_models = len(request.models)
        
        for idx, model_name in enumerate(request.models):
            model = get_model(model_name)
            model_results = []
            
            for text in test_inputs:
                rendered = render_prompt(base_prompt, {input_var: text})
                
                raw = model.run(rendered, constraints)
                eval_result = evaluate(
                    raw["output"],
                    constraints,
                    text,
                    task_type
                )
                
                model_results.append({
                    "input": text,
                    "output": raw["output"],
                    "score": eval_result.score,
                    "breakdown": eval_result.breakdown,
                    "tokens": raw["tokens"],
                    "latency_ms": raw["latency_ms"]
                })
            
            avg_score = sum(r["score"] for r in model_results) / len(model_results)
            
            results.append({
                "model": model_name,
                "average_score": round(avg_score, 2),
                "results": model_results
            })
            
            jobs[job_id]["progress"] = 20 + int((idx + 1) / total_models * 70)
        
        # Sort by score
        results.sort(key=lambda x: x["average_score"], reverse=True)
        
        jobs[job_id].update({
            "status": "completed",
            "progress": 100,
            "results": results,
            "completed_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        jobs[job_id].update({
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.now().isoformat()
        })

async def run_comparison(job_id: str, request: ComparisonRequest):
    """Background task for comparison"""
    try:
        results = run_prompt_comparison(
            task=request.task,
            prompt_versions=request.versions,
            input_vars={"text": request.test_input},
            models=request.models
        )
        
        formatted_results = []
        for r in results:
            formatted_results.append({
                "prompt_version": r.prompt_version,
                "model": r.model,
                "output": r.output,
                "score": r.evaluation.score,
                "breakdown": r.evaluation.breakdown
            })
        
        jobs[job_id].update({
            "status": "completed",
            "progress": 100,
            "results": formatted_results,
            "completed_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        jobs[job_id].update({
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.now().isoformat()
        })

async def run_evolution(job_id: str, request: EvolutionRequest):
    """Background task for evolution"""
    try:
        # Load prompt
        prompt_meta = registry.load_with_metadata(request.task, request.version)
        base_prompt = prompt_meta["template"]
        constraints = prompt_meta["constraints"]
        input_var = prompt_meta["input_variables"][0]
        
        jobs[job_id]["progress"] = 10
        
        # Generate test cases
        test_inputs = generate_test_cases(
            task_type=prompt_meta["task_type"],
            input_variables=prompt_meta["input_variables"],
            base_inputs=[],
            schema_fields=prompt_meta["schema_fields"],
            n=request.test_case_count
        )
        
        jobs[job_id]["progress"] = 20
        
        # Get models
        optimizer_model = get_model(request.optimizer_model)
        execution_model = get_model(request.model)
        
        # Evolve
        history = evolve_prompt(
            initial_prompt=base_prompt,
            task_inputs=test_inputs,
            constraints=constraints,
            optimizer_model=optimizer_model,
            execution_model=execution_model,
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
            "completed_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        jobs[job_id].update({
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.now().isoformat()
        })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)