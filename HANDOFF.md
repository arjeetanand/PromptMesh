# PromptMesh UI redesign handoff

## Change inventory

- Replaced the legacy interface with a responsive overview, evaluation, prompt comparison, prompt evolution, test-case generation, and run-history workspace.
- Reconnected the frontend forms to the current FastAPI schemas and job response fields, including evolution's object-shaped result payload.
- Added per-case evaluation and prompt-comparison breakdowns, top-model summary, evolution history, JSON export, and browser-local run summaries. Full results remain in the API's in-memory job store for 30 minutes.
- Added `run.sh` with safe PID/command/working-directory checks and port assignments 4004 (main), 5004 (test), and 6004 (preview).
- Added missing FastAPI/Uvicorn requirements and documented setup and the current training boundary.
- Saved the chosen visual direction in `.taste-skill/direction.json` (framed sheet, IBM Plex, muted warm frame, teal data accent).

## Model-workflow terminology

- **Evaluation:** score model outputs on the same inputs; inspect quality, latency, and token counts.
- **Prompt comparison:** compare two prompt versions against a shared input and model set.
- **Prompt evolution:** use observed failures to revise instructions; this changes prompt text, not model weights.
- **Fine-tuning:** not implemented. SFT/LoRA needs a dataset, training adapter, checkpoint handling, and a held-out base-versus-adapter evaluation.

For an interview, describe the first three as implemented workflows and identify fine-tuning as the next engineering milestone. Do not claim the UI trains models.

## Verification

- `node --check static/app.js`: passed.
- `bash -n run.sh`: passed.
- `python3 -m py_compile app.py`: passed.
- `git diff --check`: passed at the last check.
- API endpoint and payload/response shapes were inspected in `app.py`.
- Browser rendering was reviewed at desktop and 480px mobile widths, including mobile navigation and custom-prompt mode. The temporary static preview served the HTML/CSS/JS; API calls were unavailable in that preview.
- `./run.sh` was attempted and could not start the API: `No module named uvicorn`. FastAPI/Uvicorn are listed in `requirements.txt` but were not installed.

## Branch and launch

- Branch: `codex/promptmesh-ui-redesign`.
- UI implementation commit: `2c574ef` (`Redesign PromptMesh experiment workspace UI`).
- Branch is pushed to `origin/codex/promptmesh-ui-redesign`.
- Pull request: [#1 — Redesign PromptMesh experiment workspace UI](https://github.com/arjeetanand/PromptMesh/pull/1), targeting `main`.
- Setup: create/activate `.venv`, then `pip install -r requirements.txt`.
- Main: `./run.sh` → `http://127.0.0.1:4004`.
- Test: `PROMPTMESH_PORT=5004 ./run.sh`.
- Preview: `PROMPTMESH_PORT=6004 ./run.sh`.

## Next action

Install the documented Python dependencies in the intended environment, launch the API, and run a real evaluation using a configured local or cloud model. Then add a separate, bounded LoRA/SFT training pipeline if model-weight tuning is still in scope.
