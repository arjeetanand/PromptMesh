# PromptMesh UI and local LoRA handoff

## Change inventory

- Replaced the legacy form-first interface with a responsive experiment workspace for evaluation, prompt comparison/evolution, test-case generation, and run history.
- Added a Fine-tune page and API for local Qwen3-0.6B LoRA supervised fine-tuning. It exposes dataset discovery, bounded run settings, progress, saved adapters, loss curves, and base-versus-adapter validation metrics.
- Added a JSONL dataset contract and deterministic source-group split so paraphrases from one source cannot appear in different splits. Private dataset files and run artifacts are ignored by Git; the synthetic demo remains tracked.
- Added local adapter model registration so completed runs can be selected in existing model workflows.
- Added dataset readiness details and a SHA-256 fingerprint to the Fine-tune page; adapter manifests and saved-adapter rows retain the fingerprint for run lineage.
- Added per-field comparison for organization, year, and claim.
- Applied the requested black frame, white work surface, `#0F41F3` actions, and limited `#F9B318` highlights.
- Added focused unit tests, documented the local training setup, and retained the safe launcher on ports 4004/5004/6004.

## Illustration follow-up

- Generated two original transparent mascot poses in the PromptMesh palette: a thinking hero pose and a compact run-history pose. Optimized WebP assets are in `static/images/` (about 268 KB combined).
- Replaced the overview's static process diagram with the hero companion and added the alternate pose to both empty run-history states. Loading and API error placeholders remain text-led.
- Added gentle character float and thought-dot animation; the existing `prefers-reduced-motion` rule disables it.
- Browser verification passed at 1600px desktop and 390px mobile widths. Both poses loaded (1345px source width), neither view had horizontal overflow, and the run-history empty state rendered its alternate pose.
- Confirmed the reduced-motion rule is present. `node --check static/app.js`, `bash -n run.sh`, and `git diff --check` passed.
- Original illustration implementation commit `d1f1625` is included in the updated PR #1 history; PR #1 remains unmerged.

## Section illustration follow-up

- Added a small companion vignette beside the page title on Evaluate, Compare, Prompt evolution, Fine-tune, Test cases, and Run history. Each uses the existing mascot artwork and a task-specific inline SVG scene (score/check, paired prompts, revision loop, model graph, test cards, or run timeline) in the PromptMesh blue and amber.
- Kept the form and data areas unchanged; no JavaScript behavior or dependencies were added.
- Browser verification passed at 1600px desktop and 390px mobile widths. All six images and SVG symbols rendered, with no horizontal overflow.
- The section markup and styles are included in implementation commit `913e392` on `codex/promptmesh-evaluation-reliability`, based on `107a847`.

## Concepts and interview framing

- **Prompt evolution** edits instructions while keeping model weights unchanged.
- **SFT/LoRA** trains a small set of adapter weights on labeled prompt/answer examples while preserving the base checkpoint.
- The current training job scores the base checkpoint and adapter on the same grouped validation examples. It records JSON-valid rate, record exact match, per-field accuracy, train/validation loss, dataset and prompt hashes, split counts, model/tokenizer revisions, metric split, and selected hyperparameters. The validation scores use deterministic parsing, not an LLM judge. Training does not score the final-test split.
- Earlier saved adapters and the synthetic demo results below were produced before this validation-only change; their test scores are legacy results that were exposed during iteration, not an independent final benchmark.
- Interview description (process claim): “I built a local structured-extraction SFT workflow with grouped splits, LoRA training, deterministic schema and exact-match metrics, and reproducibility metadata. I separated validation-based selection from final-test reporting; the human-reviewed benchmark and final comparison are still in progress.”
- Current evaluation claim: “I repaired an LLM-judge evaluation path so task-specific scoring is preserved and a failed judge produces a failed run instead of a plausible score.”
- Do not claim a gain from the tracked 48-example synthetic demo. A résumé result requires a reviewed domain dataset, a separate test set, repeated runs or uncertainty analysis, and an observed improvement.
- LoRA is the implemented low-resource choice. QLoRA is a memory-saving option for larger checkpoints; full fine-tuning updates all weights and costs more memory; RAG adds retrieved context at inference, DPO needs preference pairs, and distillation trains a smaller student from a teacher. Those methods are not implemented in this stage.

## Data and runtime notes

- `training/datasets/entity_extraction_demo.jsonl` is synthetic workflow data only. Add private JSONL files beside it using `training/datasets/README.md`; those files are gitignored.
- The first training run downloads the Qwen3-0.6B checkpoint from Hugging Face (approximately 1.5 GB). Training and the fine-tune page's validation scoring are local. The general PromptMesh evaluation endpoint can use a remote judge model; its UI path identifies that distinction.
- Adapter output is stored under `training/runs/` and can be selected by `trained:<run-id>`. Local runs are gitignored.
- Historical pre-change run on the bundled synthetic demo used MPS: 36 train / 6 validation / 6 test examples, one epoch, LoRA rank 8, 70.8 seconds. Base: 0% valid JSON, 0% exact records, 0% field accuracy. Adapter: 100% valid JSON, 0% exact records, 66.7% field accuracy (organization/year 100%, claim 0%); validation loss 0.3336. The six-example test metrics were exposed during iterative training and are legacy workflow evidence only, not an independent quality result or résumé claim.
- Loaded the saved adapter through `models.registry.get_model()` and completed a local synthetic extraction inference. The checkpoint download is cached on this machine, outside the repository.

## Verification

- `./.venv/bin/python -m unittest discover -s tests -p 'test_training.py' -v`: 7 tests passed, including dataset path confinement, SHA-256 fingerprints, grouped split isolation, metric parsing, adapter path validation, lazy Cohere client construction, and Transformers batch generation.
- Python compilation, `node --check static/app.js`, `bash -n run.sh`, and `git diff --check`: passed.
- Loopback API checks for health, datasets, adapters, models, and tasks passed. The dataset endpoint returns the 64-character SHA-256 and MPS runtime; an unknown dataset returned 404 and an epoch count of 4 returned 422.
- Browser review passed at desktop and 480px mobile width with no horizontal overflow. The Fine-tune page shows the readiness card and dataset fingerprint; the mobile drawer opens and closes without changing the current tab.
- The design-taste inspector could not launch headless Edge in this environment; the connected in-app browser was used for rendered desktop/mobile and navigation checks.
- A UI-started local run completed on MPS and rendered the base/adapter comparison and loss history. Saved adapter inference through the model registry also passed. The six-example synthetic test remains workflow evidence only.
- The first end-to-end attempt exposed Transformers 5 batch handling in both held-out scoring and adapter inference; both callers now pass `input_ids` and `attention_mask` to `generate`, and the regression test covers those paths.

## Evaluation reliability follow-up

- Corrected the task-specific classification/verification score formula; the duplicate generic formula had been overwriting it.
- The judge no longer returns neutral scores after three failures. The shared scorer raises `JudgeUnavailableError`; API jobs fail visibly, the CLI rethrows it, and the diagnostic script reports no score.
- Renamed the Evaluate-page chip to `LLM-judged run`; README now states that these scores are heuristics, not gold-label benchmark results.
- Added four regression tests for task-specific weights, missing judge results, and retry exhaustion.
- Full suite: 29 tests passed. Python compilation, JavaScript syntax, and `git diff --check` passed.
- Browser verification on port 4004 showed `API connected` after reload and the `LLM-judged run` label. At a 390px viewport, the page width stayed 390px; the page rendered without horizontal overflow or browser console errors. No remote judge call was made.

## Validation-only selection follow-up

- Changed local LoRA training so base and adapter selection metrics use the grouped validation split; the training job does not pass final-test rows to generation or scoring.
- New adapter manifests record schema version 2, prompt version/hash, tokenizer revision, `metrics_split: validation`, and `test_split_used: false`. Older manifests without a metric-split field are exposed as `legacy_test` and labeled in the UI as previously exposed test metrics.
- Prepared a one-row JSONL example and an `unreviewed` benchmark-card template. The template files are tracked; filled datasets and cards remain ignored. The trainer does not yet enforce card review status, and no human-reviewed dataset has been supplied.
- Updated the Fine-tune UI and README to call the current results validation metrics and keep final-test counts labeled as reserved.
- Focused training suite: 10 passed; prompt-evolution provenance regression: 1 passed; full suite: 33 passed. Python compilation, `node --check static/app.js`, `bash -n run.sh`, and `git diff --check` passed.
- Browser check on port 4004 showed the Fine-tune API connected, old adapters labeled as legacy test metrics, and the reserved final-test split. The prompt-evolution page showed the optimization-input and judge-score disclosure at 390px with no horizontal overflow or browser console error. The viewport was restored to the normal 1185px width.
- Runtime note: the app API reports MPS and its server process loaded Apple's Metal driver, while a fresh CLI probe reported MPS unavailable. Resolve this discrepancy before quantization measurements; no quantization package or model was installed/downloaded for that work.
- Prompt evolution reuses the supplied examples for candidate selection and uses the configured LLM judge without gold labels. The UI now calls them optimization inputs, labels scores as judge heuristics, and exported results record the method, input role, and count. This does not enforce separation from a future final benchmark.

## Next résumé milestones

1. Add a human-reviewed, versioned gold dataset with grouped train/validation/test splits. Training model selection now uses validation data. Prompt evolution identifies its supplied inputs as an optimization set, but a separate frozen evaluator and enforced data boundary remain to be built.
2. Compare a base model, prompt-only baseline, and LoRA adapter on the same untouched test examples. Report task metrics, repeated-run variation or confidence intervals, and exact model/data revisions.
3. Add a quantized-inference experiment only after selecting a backend that works on the target hardware. Compare quality, latency, and peak memory against the unquantized model on the same frozen test set.
4. Package one reproducible run manifest and a short demo, including dataset limitations and failure cases. Do not present the synthetic example scores as model-quality evidence.

## Branch and pull request

- Previous implementation branch: `codex/promptmesh-evaluation-reliability`, evaluation reliability commit `913e392`.
- Current validation-selection work is on `codex/promptmesh-validation-selection`, commit `68204e1`, based on PR head `745bf89`.
- [PR #1 — PromptMesh UI redesign](https://github.com/arjeetanand/PromptMesh/pull/1) is open, targets `main`, and uses its existing head branch `codex/promptmesh-ui-redesign`. The validation-selection commit is being added to that PR.
- Do not merge PR #1.

## Run instructions and next action

- Current local server: `http://127.0.0.1:4004`; start with `source .venv/bin/activate && ./run.sh` in this environment. `/api/health` returned `healthy` during handoff.
- Create/activate `.venv`, then run `pip install -r requirements.txt`.
- Main: `./run.sh` → `http://127.0.0.1:4004`; test and preview ports are 5004 and 6004.
- Next: build the reviewed gold benchmark and validation-only prompt/model selection before reporting quality gains.
