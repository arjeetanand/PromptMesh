# PromptMesh UI and local LoRA handoff

## Change inventory

- Replaced the legacy form-first interface with a responsive experiment workspace for evaluation, prompt comparison/evolution, test-case generation, and run history.
- Added a Fine-tune page and API for local Qwen3-0.6B LoRA supervised fine-tuning. It exposes dataset discovery, bounded run settings, progress, saved adapters, loss curves, and base-versus-adapter held-out metrics.
- Added a JSONL dataset contract and deterministic source-group split so paraphrases from one source cannot appear in both train and test sets. Private dataset files and run artifacts are ignored by Git; the synthetic demo remains tracked.
- Added local adapter model registration so completed runs can be selected in existing model workflows.
- Added dataset readiness details and a SHA-256 fingerprint to the Fine-tune page; adapter manifests and saved-adapter rows retain the fingerprint for run lineage.
- Added per-field held-out comparison for organization, year, and claim.
- Applied the requested black frame, white work surface, `#0F41F3` actions, and limited `#F9B318` highlights.
- Added focused unit tests, documented the local training setup, and retained the safe launcher on ports 4004/5004/6004.

## Illustration follow-up

- Generated two original transparent mascot poses in the PromptMesh palette: a thinking hero pose and a compact run-history pose. Optimized WebP assets are in `static/images/` (about 268 KB combined).
- Replaced the overview's static process diagram with the hero companion and added the alternate pose to both empty run-history states. Loading and API error placeholders remain text-led.
- Added gentle character float and thought-dot animation; the existing `prefers-reduced-motion` rule disables it.
- Browser verification passed at 1600px desktop and 390px mobile widths. Both poses loaded (1345px source width), neither view had horizontal overflow, and the run-history empty state rendered its alternate pose.
- Confirmed the reduced-motion rule is present. `node --check static/app.js`, `bash -n run.sh`, and `git diff --check` passed.
- Branch: `codex/promptmesh-illustrations`, based on `1e9c543`; implementation commit: `d1f1625`. This follow-up has not been pushed or merged.

## Section illustration follow-up

- Added a small companion vignette beside the page title on Evaluate, Compare, Prompt evolution, Fine-tune, Test cases, and Run history. Each uses the existing mascot artwork and a task-specific inline SVG scene (score/check, paired prompts, revision loop, model graph, test cards, or run timeline) in the PromptMesh blue and amber.
- Kept the form and data areas unchanged; no JavaScript behavior or dependencies were added.
- Browser verification passed at 1600px desktop and 390px mobile widths. All six images and SVG symbols rendered, with no horizontal overflow.
- Branch: `codex/promptmesh-section-illustrations`, based on `107a847`; local commit details will be recorded after committing. This follow-up has not been pushed or merged.

## Concepts and interview framing

- **Prompt evolution** edits instructions while keeping model weights unchanged.
- **SFT/LoRA** trains a small set of adapter weights on labeled prompt/answer examples while preserving the base checkpoint.
- The training job scores the base checkpoint and adapter on the same untouched, grouped test examples. It records JSON-valid rate, record exact match, per-field accuracy, train/validation loss, dataset hash, split counts, model revision, and selected hyperparameters. The held-out scores use deterministic parsing, not an LLM judge.
- Interview description: “I built a local, reproducible SFT experiment for structured extraction: grouped data splits prevent source leakage, LoRA adapts a small model, and a fixed held-out set compares the adapter against its base model with schema and exact-match metrics.”
- Do not claim a gain from the tracked 48-example synthetic demo. A résumé result requires a reviewed domain dataset, a separate test set, repeated runs or uncertainty analysis, and an observed improvement.
- LoRA is the implemented low-resource choice. QLoRA is a memory-saving option for larger checkpoints; full fine-tuning updates all weights and costs more memory; RAG adds retrieved context at inference, DPO needs preference pairs, and distillation trains a smaller student from a teacher. Those methods are not implemented in this stage.

## Data and runtime notes

- `training/datasets/entity_extraction_demo.jsonl` is synthetic workflow data only. Add private JSONL files beside it using `training/datasets/README.md`; those files are gitignored.
- The first training run downloads the Qwen3-0.6B checkpoint from Hugging Face (approximately 1.5 GB). Training and the fine-tune page's held-out scoring are local. The general PromptMesh evaluation endpoint can use a remote judge model; its UI path now identifies that distinction.
- Adapter output is stored under `training/runs/` and can be selected by `trained:<run-id>`. Local runs are gitignored.
- Completed the bundled synthetic demo on MPS: 36 train / 6 validation / 6 held-out examples, one epoch, LoRA rank 8, 70.8 seconds. Base: 0% valid JSON, 0% exact records, 0% field accuracy. Adapter: 100% valid JSON, 0% exact records, 66.7% field accuracy (organization/year 100%, claim 0%); validation loss 0.3336. With only six synthetic test examples, these numbers demonstrate the workflow and are not a quality result or résumé claim.
- Loaded the saved adapter through `models.registry.get_model()` and completed a local synthetic extraction inference. The checkpoint download is cached on this machine, outside the repository.

## Verification

- `./.venv/bin/python -m unittest discover -s tests -p 'test_training.py' -v`: 7 tests passed, including dataset path confinement, SHA-256 fingerprints, grouped split isolation, metric parsing, adapter path validation, lazy Cohere client construction, and Transformers batch generation.
- Python compilation, `node --check static/app.js`, `bash -n run.sh`, and `git diff --check`: passed.
- Loopback API checks for health, datasets, adapters, models, and tasks passed. The dataset endpoint returns the 64-character SHA-256 and MPS runtime; an unknown dataset returned 404 and an epoch count of 4 returned 422.
- Browser review passed at desktop and 480px mobile width with no horizontal overflow. The Fine-tune page shows the readiness card and dataset fingerprint; the mobile drawer opens and closes without changing the current tab.
- The design-taste inspector could not launch headless Edge in this environment; the connected in-app browser was used for rendered desktop/mobile and navigation checks.
- A UI-started local run completed on MPS and rendered the base/adapter comparison and loss history. Saved adapter inference through the model registry also passed. The six-example synthetic test remains workflow evidence only.
- The first end-to-end attempt exposed Transformers 5 batch handling in both held-out scoring and adapter inference; both callers now pass `input_ids` and `attention_mask` to `generate`, and the regression test covers those paths.

## Branch and pull request

- Branch: `codex/promptmesh-ui-redesign`.
- Pull request: [#1 — PromptMesh UI redesign](https://github.com/arjeetanand/PromptMesh/pull/1), targeting `main`.
- The task commits `8a4e0db`, `31ba8a0`, and `7767a81` are on the PR branch. GitHub CLI could not verify live PR metadata after the latest push because `api.github.com` was unreachable.
- Do not merge PR #1.

## Run instructions and next action

- Current local server: `http://127.0.0.1:4004`; start with `source .venv/bin/activate && ./run.sh` in this environment. `/api/health` returned `healthy` during handoff.
- Create/activate `.venv`, then run `pip install -r requirements.txt`.
- Main: `./run.sh` → `http://127.0.0.1:4004`; test and preview ports are 5004 and 6004.
- Next: verify PR #1 still targets `main` when the GitHub API is reachable; do not merge it.
