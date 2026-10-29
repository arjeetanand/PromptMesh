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
- Original illustration implementation commit `d1f1625` is included in PR #1 history.

## Section illustration follow-up

- Added a small companion vignette beside the page title on Evaluate, Compare, Prompt evolution, Fine-tune, Test cases, and Run history. Each uses the existing mascot artwork and a task-specific inline SVG scene (score/check, paired prompts, revision loop, model graph, test cards, or run timeline) in the PromptMesh blue and amber.
- Kept the form and data areas unchanged; no JavaScript behavior or dependencies were added.
- Browser verification passed at 1600px desktop and 390px mobile widths. All six images and SVG symbols rendered, with no horizontal overflow.
- The section markup and styles were implemented in commit `2723a66` on `codex/promptmesh-section-illustrations`, based on `107a847`.

## Section illustration follow-up

- Added a small companion vignette beside the page title on Evaluate, Compare, Prompt evolution, Fine-tune, Test cases, and Run history. Each uses the existing mascot artwork and a task-specific inline SVG scene (score/check, paired prompts, revision loop, model graph, test cards, or run timeline) in the PromptMesh blue and amber.
- Kept the form and data areas unchanged; no JavaScript behavior or dependencies were added.
- Browser verification passed at 1600px desktop and 390px mobile widths. All six images and SVG symbols rendered, with no overlap or horizontal overflow.
- Preview: `http://127.0.0.1:6004` remains available from this worktree. Restarting through `run.sh` reported an existing listener and stopped nothing; PID 39677 was verified with this worktree as its working directory.
- Branch: `codex/promptmesh-section-illustrations`, based on `107a847`; implementation commit: `2723a66`, included in PR #1.

## Navigation and background-job follow-up

- Added a visible Back to overview button on each non-overview workspace page. At narrow widths it becomes an arrow-only button next to the active page title.
- Added **Run in background** to the local LoRA and prompt evolution progress dialog. Closing the dialog leaves the existing poll active in the open browser tab. A top-bar status button shows progress, paused, complete, or failed state. Selecting it reopens progress, retries paused polling, or opens completed results; completion does not switch pages until selected.
- The browser tab must remain open for progress updates. No LoRA training or evolution job was started during this change.
- Focused UI verification: visited Evaluate, Compare, Prompt evolution, Fine-tune, Test cases, and Run history, confirmed Back to overview on each, and returned to Overview. At 390px mobile width, the document width remained 390px with no horizontal overflow. `node --test tests/ui_background_jobs.test.cjs` passed four checks covering dialog dismissal/reopening with polling active, the paused-job run lock, and LoRA/evolution completion status/results navigation. Source syntax, test syntax, launcher syntax, and `git diff --check` passed.
- Preview: `http://127.0.0.1:6004` is already serving this worktree. `run.sh` safely declined to restart the existing listener (PID 39677) because the launcher had no matching PID file; no process was stopped.
- Branch: `codex/promptmesh-navigation-dismissible-jobs`, based on `310d008`; implementation and regression-test commit `99a4dae`, with documentation commit `fbafd2c`, included in PR #1.

## Concepts and interview framing

- **Prompt evolution** edits instructions while keeping model weights unchanged.
- **SFT/LoRA** trains a small set of adapter weights on labeled prompt/answer examples while preserving the base checkpoint.
- The current training job scores the base checkpoint and adapter on the same grouped validation examples. It records JSON-valid rate, record exact match, per-field accuracy, train/validation loss, dataset and prompt hashes, split counts, model/tokenizer revisions, metric split, and selected hyperparameters. The validation scores use deterministic parsing, not an LLM judge. Training does not score the final-test split.
- Earlier saved adapters and the synthetic demo results below were produced before this validation-only change; their test scores are legacy results that were exposed during iteration, not an independent final benchmark.
- Interview description (process claim): “I built a local structured-extraction evaluation and LoRA/SFT workflow with grouped splits, deterministic gold metrics, hash-tracked artifacts, and validation-only prompt/model selection. A frozen evaluator compares prompt-only and LoRA arms on one shared test split with source-group uncertainty intervals.” Add that no real benchmark corpus or quality gain is available until you complete human review and run it on your authorized dataset.
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

## Gold validation selection and frozen benchmark follow-up

- Added exact-byte dataset snapshots and a benchmark-card gate. The card must match the current JSONL SHA-256, have all review/count fields, and mark `human_reviewed`; the synthetic demo cannot pass. This is a self-attestation check, not independent proof of review.
- Added 30-example / 10-source-group minimums on both validation and final-test splits. Training may still run without a review card for experimentation; prompt selection and final evaluation require a matching self-attested card.
- Added `/api/training/prompt-selections` to compare the built-in `extraction/v1` prompt and up to three user candidates using deterministic gold metrics on validation rows only. The lexicographic rule is record exact match, field accuracy, then JSON-valid rate; ties keep the earlier prompt. It writes a hash-checked private selection record tied to the dataset/card and validation-only schema-v3 LoRA artifact.
- Added `/api/training/benchmarks` and the Fine-tune UI action for the matched three-arm comparison: base+initial prompt, base+validation-selected prompt, and LoRA+the same selected prompt. All arms use the same reserved test rows. An exclusive reservation is written before the first test inference, preventing another process or retry from consuming that dataset version's holdout. A failed run after reservation requires a new dataset version.
- Reports store aggregate metrics, source-group bootstrap intervals, data/card/selection/prompt/adapter hashes, model/tokenizer revisions, split counts, device, and deterministic decoding settings. They do not store source text or per-example outputs. Selection and report files are private local JSON under gitignored `training/selections/` and `training/benchmarks/`; the one-time reservation stays with the dataset fingerprint after possible test access.
- The final evaluator loads only the pinned model revision already in the local cache (`local_files_only`); it does not download weights or call a provider. The existing training job may download Qwen weights when run on an uncached machine.
- Prompt evolution remains an LLM-judge heuristic workflow. Users can copy a candidate prompt into the gold-validation selector; the evolution job itself is not wired to read the private dataset.
- Focused mocked-runner, training, and API checks cover validation-only selection, undersized-split rejection, matched test arms, source-group intervals, reservation/retry behavior, report idempotency, and rejection of a second configuration. No real model inference, local training, corpus review, model download, or quantization measurement occurred.
- `run.sh` now prefers the project virtualenv. Edge rendered the Fine-tune screen from the launcher-owned 5004 test instance. The design inspector captured 1440px, 768px, and 390px views with zero horizontal overflow or browser console errors; no physical phone test was performed. It reports a false `no-title` flag even though its own hero metric and screenshot identify the visible h1, plus a warning that 72% of text is under 13px (field hints and metadata use 11–12px).
- Port 4004 remains held by Python PID 33390 with this repository as its working directory, but no launcher PID file exists and local requests were refused. I left that process untouched. The final browser check used port 5004.
- UI copy now calls review metadata self-attested and explicitly says PromptMesh cannot verify label quality. It also gates validation selection on both split minimums and corrects the adapter label, placeholder line breaks, and screen-reader status announcement.
- The remaining evidence gap is an authorized human-reviewed corpus and a real local run; no quality claim is supported yet.

## Next résumé milestones

1. Add an authorized, human-reviewed dataset using the JSONL and benchmark-card templates. The local card is a self-attestation, so preserve the annotation guidelines and review evidence separately.
2. Train a new schema-v3 adapter on that dataset, select prompts on validation only, then run the frozen matched benchmark once. Review per-example errors before making any quality claim.
3. Select a compatible installed quantization backend and compare it with the base model on the same frozen test set, recording quality, latency, peak memory, hardware, and limitations.
4. Package the measured run manifest and a short demo. Do not present synthetic results as model-quality evidence.

## Branch and pull request

- Previous implementation branch: `codex/promptmesh-evaluation-reliability`, evaluation reliability commit `913e392`.
- Implementation commit `ff28abb` and its handoff commit `80a010a` are on `codex/promptmesh-validation-selection`, based on `20cf220`.
- [PR #1 — PromptMesh UI redesign](https://github.com/arjeetanand/PromptMesh/pull/1) was already merged into `main` as `5b3b4c8`; its branch head was `20cf220`. This follow-up is in [PR #2](https://github.com/arjeetanand/PromptMesh/pull/2), open against `main` from `codex/promptmesh-validation-selection`. Do not merge without explicit approval.
- The user's standing preference is to open/update a PR targeting `main`. Do not merge without explicit approval.

## Run instructions and next action

- The existing `http://127.0.0.1:5004` tab displayed the updated Fine-tune markup, but its API process predates the quantization endpoint and left the new controls disabled. A fresh 6004 instance could not be reached from Edge; the existing 4004/5004 host processes were left untouched because their ownership could not be verified from this sandbox.
- Create/activate `.venv`, then run `pip install -r requirements.txt`.
- Main: `./run.sh` → `http://127.0.0.1:4004`; test and preview ports are 5004 and 6004.
- The original validation-selection stage passed 51 Python tests and 8 UI tests. The latest quantization follow-up passed 57 Python tests and 9 UI tests; its local inference smoke is documented below. No reviewed corpus or representative quality benchmark exists. Selection/report JSON remains local, and the Fine-tune UI does not restore a previous result after a page reload.
- Next: provide the authorized reviewed corpus, train a schema-v3 adapter, inspect its frozen benchmark, then run the optional quantized-inference comparison once.

## Quantized-inference follow-up — 2026-10-28

- Added optional `bitsandbytes==0.50.0` discovery and NF4/LLM.int8 inference to the frozen benchmark. The project dependency is isolated in `requirements-quantization.txt`; no global package or model-weight download was used.
- The benchmark attaches the existing full-precision LoRA adapter to each quantized base. It runs a short fixed synthetic canary before reserving the final test set, then measures all selected variants on the same selected prompt and identical reserved test rows.
- Reports include method, weight bits, backend/version/device, compute dtype, NF4 double quantization or the INT8 outlier threshold, task metrics and grouped intervals, load/inference seconds, generated tokens per second, and Transformers model footprint. The footprint is not peak device memory; timings are single cold runs.
- The UI explains that these bitsandbytes methods do not use an offline calibration dataset. NF4 is NormalFloat4, not ordinary signed INT4. AWQ/GPTQ calibration and QLoRA training are not implemented. The current adapter is full-precision LoRA/SFT, so this is quantized adapter inference, not QLoRA.
- This initial local smoke used a cached Qwen checkpoint, an existing synthetic-demo adapter, and one fixed synthetic input; NF4 and INT8 both generated output in the CPU-only command environment. The later adapter-attached MPS canary is recorded below.
- Regression coverage includes NF4/INT8 configuration, API validation, the pre-reservation canary, identical test rows, report fields, and calibration labeling. The full Python suite passed (57 tests), the Node UI suite passed (9 tests), Python compilation, JavaScript syntax, launcher syntax, and `git diff --check` passed.
- Edge rendered the updated Fine-tune markup on the existing 5004 tab. At 1440px and 390px, document width matched the viewport with no horizontal overflow; there were no browser console errors. The running host API is an older process that does not return quantization runtime metadata, so those controls remained disabled in that tab.
- A fresh `run.sh` attempt reported ready on 6004 inside the isolated command environment, but Edge could not connect to that instance. The existing 4004/5004 host processes were left untouched because their ownership could not be verified from this sandbox. The final branch is not confirmed running on the main port.
- At this earlier checkpoint, the adapter-attached path had only been checked in the CPU-only command environment; the subsequent host-context MPS canary below verified that path on MPS.
- No real reviewed corpus, frozen test benchmark, quality result, or AWQ/GPTQ calibration experiment exists. Keep the résumé claim to implemented workflow capabilities until that evidence is produced.
- Quantization implementation commit `7476163` was pushed to `codex/promptmesh-validation-selection`; [PR #2](https://github.com/arjeetanand/PromptMesh/pull/2) is verified open against `main` at head `7476163ee5d59d74d03006c8bbd722cafef02b0a`. It was not merged.

## Annotation protocol follow-up — 2026-10-28

- Added `training/datasets/ANNOTATION_GUIDE_v1.md` with task-specific rules for organization names, explicit event years, atomic claims, null labels, ambiguity, source grouping, exact-match behavior, human review, and holdout protection. Its examples are explicitly synthetic and not benchmark data.
- Set the benchmark-card template guideline ID to `entity-extraction-v1`, tracked the guide despite the dataset-directory ignore rule, and linked it from the dataset instructions and README.
- Corrected stale README language: training may run without review metadata, while prompt selection and frozen benchmarking require the matching `human_reviewed` card and dataset fingerprint. That card remains a local self-attestation.
- No authorized corpus was added or marked reviewed. A human still needs to populate and review the ignored dataset/card before model-quality or quantization claims can be made.
- Annotation guide and documentation commit `b8c4e4f` is on `codex/promptmesh-validation-selection`; whitespace and benchmark-card JSON checks passed. Runtime tests were not rerun because this follow-up changes documentation and templates only.

## Public-source review packet follow-up — 2026-10-28

- Prepared an ignored review packet under `training/datasets/review_packets/`: 19 concise source-based candidate inputs in `UNREVIEWED_DRAFT_candidates_20261028.jsonl`, a review sheet with source links/draft labels/rights status/review-decision fields, and packet instructions.
- The packet is not in Git and is below benchmark minimums. With 19 source groups, PromptMesh splits it 13/3/3; the validation and test splits each need at least 30 examples across 10 groups. No card is present and the app does not list the nested packet as a dataset.
- The existing parser accepts the row schema; readiness reports `missing_card`. All entries remain `NEEDS_HUMAN_REVIEW`, and source reuse permission is unverified. NASA pages need page-level third-party checks; commercial pages need reuse terms checked. NASA’s official media-use guidance explains these exceptions: https://www.nasa.gov/nasa-brand-center/images-and-media/.
- The user confirmed that `organization` means the claim actor. Updated `extraction/v1` to definition `1.1.0` and aligned the guide; the prompt template hash is captured by new benchmark selections.
- No training, prompt selection, final test inference, or quantized comparison used these drafts. They are not quality evidence.
- Added a regression check for the loaded prompt contract. Verification passed: 58 Python `unittest` tests, 9 Node tests, Python compilation, and `git diff --check`. `pytest` is not installed in the project environment; the project suite runs with `unittest`.

## Benchmark sizing and backend capability check — 2026-10-28

- Rechecked the private candidate packet: 19 rows across 19 source groups split 13/3/3, so it cannot pass the validation or final-test minimums.
- With the current seed-42 group splitter, 67 independent source groups with three distinct, label-consistent examples each produce 141 train / 30 validation / 30 test examples and 47 / 10 / 10 groups. This is one way to meet the current floors, not a human-reviewed dataset; readiness must still be checked after annotation.
- The restricted command environment's `.venv` has Torch 2.14.1 and bitsandbytes 0.50.0. MPS is built but reports unavailable there, so that quantization-runtime probe reported CPU; the separate host-context check below confirms MPS availability and the adapter-attached path.
- At the time of this checkpoint, PR #2 was at head `376784c3f5fd9e43fb83adb801d81224c8f4ea42`, open against `main`, and GitGuardian Security Checks had passed.

## Adapter-attached MPS canary and preview — 2026-10-28

- Rechecked in the local host context: Torch 2.14.1, bitsandbytes 0.50.0, and `torch.backends.mps.is_available() == True`. The restricted shell had reported MPS unavailable; the API process and escalated local command use the host MPS runtime.
- Started the current branch with `PROMPTMESH_PORT=6004 ./run.sh` in a persistent local shell. `GET /api/health` is healthy, the current API reports MPS plus BNB INT8/NF4, and `/` returns HTTP 200 with title `PromptMesh — Evaluation workspace`. Existing 4004/5004 processes lack run.sh PID files; they were left untouched. Preview: `http://127.0.0.1:6004`.
- Adapter-attached MPS smoke used cached Qwen/Qwen3-0.6B weights and the existing legacy synthetic-demo adapter `4d971ab48d8048c2a11af87562f54830`, with local-files-only loading and one fictional input. No dataset, benchmark reservation, or artifact was written. The legacy manifest lacks `tokenizer_revision`; `base_revision` and `tokenizer_revision` were supplied as `None` in memory for this hardware smoke only.
- Both methods generated JSON on MPS. NF4: 7.366 s load, 1.424 s inference, 24 tokens; it returned year as a string and a shortened claim. INT8: 1.351 s load, 9.668 s inference, 24 tokens; it returned year as an integer and the same shortened claim. These sequential single-input timings are not a performance comparison, and the output is not a quality result.
- This closes the adapter-attached hardware-path check only. A real prompt-only/LoRA/NF4/INT8 comparison remains pending a sufficiently sized human-reviewed, rights-cleared corpus.

## Public-source candidate expansion — 2026-10-28

- Expanded the ignored local review packet from 19 to 201 draft rows across 67 source groups. Added 48 source candidates from NASA, DOE, NSF, EPA, NIST, USDA, and USDOT pages; each source has three controlled phrasings with one shared proposed label. Existing 19 candidates retain their original input plus two context-wrapped variants.
- The variants share one underlying fact and must stay grouped. They can support a controlled phrasing-robustness study after review; they are not independent facts or a representative natural-document corpus. The 48 newly added source pages are all dated 2024, so year extraction remains imbalanced.
- The current seed-42 split is 141 train / 30 validation / 30 test rows and 47 / 10 / 10 source groups. All 201 rows are still `NEEDS_HUMAN_REVIEW`; every reuse status is unresolved. The packet remains nested under the ignored `training/datasets/review_packets/` directory and is not loaded as a training dataset.
- Source claims and dates were checked against official pages; source-specific ambiguity notes remain in the review sheet, including funding opportunities versus awards, selected versus completed awards, department/office naming, and a USDA headline/URL amount mismatch. Human label review and rights clearance are still required.
- The actor convention remains `organization` = focal claim actor, as confirmed by the user. No training, prompt selection, frozen benchmark, quantized comparison, or quality claim used this packet.
- Updated the dataset instructions, README, checklist, and handoff. The production JSONL parser accepted the draft; the 67 groups split 47 / 10 / 10 with 141 / 30 / 30 rows, and reviewed-label/note fields were empty. The CSV has no per-row reviewer/timestamp columns; the export card records reviewer role/time. This follow-up does not modify application code or load the packet.
- Documentation commit `146810a` is on `codex/promptmesh-validation-selection` and was pushed to existing PR #2, previously verified to target `main`. The GitHub API was unreachable during this turn, so the PR's current check and merge state was not re-queried.

## Local candidate review workbench — 2026-10-28

- Added a loopback-only API for the one ignored public-source review CSV. It validates group row indexes, records label decisions separately from source-reuse evidence, rejects symlinked packet paths, and replaces the CSV atomically.
- Added a Fine-tune review queue with linked-source context, the actor definition for `organization`, editable labels for each phrasing, row-level review/exclusion decisions, source-level reuse evidence, and group navigation. It never imports the packet into training.
- The local candidate CSV and draft JSONL remain git-ignored and unchanged by this implementation. No labels or reuse decisions were submitted. The benchmark remains unreviewed and its year labels remain imbalanced.
- Verification: 64 Python `unittest` tests passed; 9 Node UI checks passed; Python and JavaScript syntax, launcher syntax, and `git diff --check` passed. The refreshed preview API is healthy and its local packet summary is 201 rows / 67 groups / 0 reviewed labels / 0 reviewed groups / 0 eligible groups. Browser checks at 1440/768/390 CSS pixels found no horizontal overflow; group navigation and the mobile menu open/close worked. No review was saved and no physical phone test was performed.
- Branch: `codex/promptmesh-validation-selection`. Implementation `bf1fe93` and the handoff updates are pushed to existing [PR #2](https://github.com/arjeetanand/PromptMesh/pull/2). A live `gh pr view` check after `63309fa` confirmed the PR was OPEN against `main`; this follow-up updates documentation only, and the PR was not merged.
- The stale 6004 process was verified as a single PromptMesh Uvicorn process with this repository as its working directory and gracefully restarted. The current preview is `http://127.0.0.1:6004` in a persistent local terminal session. Port 4004 had multiple listeners and no matching `run.sh` PID file, so 4004 and 5004 were left untouched. Automatic review rejected an earlier unscoped debug invocation because it could have restarted 4004; that invocation did not run.
- Next: human-review candidates against sources, confirm reuse rights, diversify years, and create an authorized benchmark dataset/card. Then train a schema-v3 adapter, run the frozen test comparison, and measure quantized inference on that reviewed corpus. No model-quality result or real calibration experiment exists yet.

## Runtime reproducibility metadata — 2026-10-29

- New LoRA/SFT manifests, validation prompt-selection records, and frozen benchmark reports capture Python/platform/machine/device plus versions of Torch, Transformers, PEFT, TRL, Datasets, Accelerate, and optional bitsandbytes. Frozen reports include the adapter-training and prompt-selection environments. Missing optional distributions are recorded as `null`.
- The adapter API exposes this metadata; saved-adapter cards, prompt-selection results, and frozen reports show stage-specific runtime summaries. Older runs are labeled as missing runtime metadata rather than inferred.
- This records the environment used but does not pin a reinstallable environment. `requirements.txt` is still unpinned; a local training lock is a remaining reproducibility task.
- Verification: all 65 Python `unittest` tests and 11 Node UI tests passed; Python/JavaScript/launcher syntax and `git diff --check` passed. The browser loaded the latest Fine-tune UI on `http://127.0.0.1:6004`, showed the API connected and all three existing adapters as legacy runs, had no console errors, and had no horizontal overflow at the 987px viewport. The preview listener was PID 78788.
- Branch/commit: `codex/promptmesh-validation-selection`, implementation commit `ee93c0a`, pushed to the existing PR #2 targeting `main`. The push succeeded; GitHub API and DNS were unavailable afterward, so the PR's live state and checks could not be re-queried during this follow-up.
- No new training or benchmark job ran in this follow-up. Synthetic and public-source candidate data remain unused for model-quality claims; human review and rights clearance are still the next gate.

## Source revision reproducibility — 2026-10-29

- Runtime metadata now captures the current PromptMesh Git revision and a dirty/clean working-tree flag from one `git status --porcelain=v2` snapshot. If Git is unavailable or the source is outside a checkout, both values are `null`; no paths or diffs are saved.
- New adapter manifests and validation selections carry their own source state. Frozen reports keep separate adapter-training, prompt-selection, and benchmark source states. The existing schemas remain backward compatible because these are optional environment fields.
- Fine-tune runtime summaries show the short code revision and dirty/clean state; the details tooltip retains the full revision. Older environment records still render normally.
- Verification: 70 Python `unittest` tests and 12 Node UI tests passed; Python compilation, JavaScript syntax, `run.sh` syntax, and `git diff --check` passed. In the local browser at `http://127.0.0.1:4004/#finetune`, the page loaded with API connected and the unchanged review packet showed 351 rows / 117 groups / 0 reviewed. Existing adapter records are legacy and do not have source metadata, so no real record with the new label was available in the browser; the focused UI test covers it.
- `./run.sh` restarted the current main instance, which remains available at `http://127.0.0.1:4004`.
- No model-training, prompt-selection, frozen-benchmark, or quantized-inference job ran. The public-source candidate labels and reuse rights remain unreviewed, so no model-quality or calibration claim is supported.
- Implementation commit `8db6b58` was pushed to `codex/promptmesh-validation-selection`, which updates existing PR #2. PR #2's target `main` was previously confirmed; the current GitHub API query failed because `api.github.com` was unreachable.

## Gold-year test slices — 2026-10-29

- New frozen benchmark reports use schema version 4 and include per-gold-year metrics for the base initial prompt, validation-selected base prompt, LoRA, and each quantized arm. Each slice records examples, source groups, task metrics, and a source-group exact-match interval when at least two groups are present.
- Fine-tune results place year slices in accessible expandable sections; sparse one-group slices explicitly show that an interval is unavailable. Older schema-v3 reports remain readable without slices and are not rerun on a previously reserved test set.
- Verification: full Python suite passed (71 tests); UI suite passed (12 tests); Python/JavaScript syntax, `run.sh` syntax, and `git diff --check` passed. The updated app connected in a browser at `http://127.0.0.1:4004/#finetune`, where the review packet correctly shows 351 draft rows, 0 reviewed labels, and synthetic-demo-only training readiness. No real frozen report was available to render because no candidate labels or reuse permissions have been human-reviewed.
- Year slices include organization, year, and claim accuracy alongside record exact match, aggregate field accuracy, JSON validity, counts, and any available grouped interval. No real benchmark data was used; candidate labels and reuse permissions still require human review.
- Delivery: implementation commit `b1c90cf` is pushed on `codex/promptmesh-validation-selection`; existing PR [#2](https://github.com/arjeetanand/PromptMesh/pull/2) is open and targets `main`. No merge or deployment occurred.
- Next: human-review the public-source labels and reuse evidence, build an authorized dataset/card, then train a fresh adapter, select on validation, and run the frozen benchmark once. Inspect per-year results before making any quality or quantization claim.

## Year-diverse public-source candidates — 2026-10-29

- Appended 45 rows across 15 groups to the ignored local review packet, using official sources from Apple, United Launch Alliance, Xbox, Google, Microsoft, NIST, OpenAI, NVIDIA, DeepMind, NASA, and Anthropic. The candidates add proposed years 2020, 2021, 2022, 2023, and 2025; all source claims remain unreviewed drafts.
- The packet then had 246 rows across 82 source groups: 66 proposed 2024 groups, three groups each for 2020, 2021, 2022, 2023, and 2025, and one undated group. It was still severely imbalanced for year extraction. Every row remained `NEEDS_HUMAN_REVIEW`; new groups had unresolved reuse permission and blank reviewed-label/note fields. The CSV does not store reviewer/timestamp per row.
- The production dataset parser accepted the draft JSONL. CSV/JSONL row order, inputs, and labels align; all 82 groups have three variants; group-label consistency holds; the deterministic seed-42 split is 174/36/36 rows across 58/12/12 groups. This is structural validation only, not label approval, rights clearance, training, or benchmark evidence.
- Public-source facts and dates were checked against the linked official pages. Review notes flag year/announcement distinctions, actor naming such as DeepMind versus Google DeepMind, and NASA/OSIRIS-REx actor boundaries. The candidate inputs are paraphrases, not quoted source passages.
- Updated README, dataset guidance, checklist, and packet instructions. No application code, training dataset, benchmark card, adapter, or benchmark report changed. Next: review the candidates and wording variants against each page, confirm reuse permissions, then decide whether to expand the dataset further before calibration or model comparison.
- The tracked documentation update is commit `0bac3d6` on `codex/promptmesh-validation-selection`, pushed to existing PR #2. `gh pr view` verified PR #2 is open against `main` at the time of this handoff check; it was not merged.

## Local training dependency snapshot — 2026-10-29

- Added `requirements-training-macos-arm64.lock` with 47 exact pins for the active LoRA/SFT dependency closure and optional bitsandbytes backend, recorded from the currently working Python 3.12.13 / macOS 26.7.1 ARM64 `.venv`.
- Compared every lock pin with the installed distribution metadata; all 47 versions match. `pip check` reports no broken requirements. No package was installed or upgraded in this step.
- This snapshot does not pin app-only dependencies from `requirements.txt`, is not portable to Linux/Windows, and has not been installed in a clean environment. That clean-install check remains open.
- README now shows how to install the app requirements together with this lock on the recorded platform and states its limits. The existing `requirements-quantization.txt` remains the optional backend entry point for other environments.
- Lock commit `e2de5fc` is pushed to `codex/promptmesh-validation-selection`; PR #2 was verified open against `main` at head `e2de5fc` after the push. It was not merged.

## Fine-tune review accessibility audit — 2026-10-29

- Inspected the live local Fine-tune page on preview port 6004; the API was connected and the candidate queue showed 246 rows / 82 source groups with zero reviewed labels. The accessibility tree exposed the linked source, all three variants, labeled organization/year/claim fields, separate reuse controls, and save status. No review decision was saved.
- Keyboard traversal through the review form followed source group, previous/next, source link, each candidate's organization/year/claim/note/decision fields, reuse decision/evidence, and save. All visible controls had accessible names; headings followed H1/H2/H3 order; status feedback used polite status regions; no duplicate IDs were found.
- The candidate review panel had no horizontal overflow at CSS viewport widths 320, 390, 768, 1024, and 1440. The mobile navigation toggle exposed `Open navigation` / `Close navigation` and changed `aria-expanded`. The browser reported no console warnings or errors.
- Measured text contrast for the candidate summary, guidance, pending status, draft labels, source focus, and primary save button ranged from 6.29:1 to 17.37:1. This was a targeted manual check, not a whole-app contrast audit or accessibility certification. No screen-reader session or axe-core scan was run.
- The task browser viewport was restored after testing. Human label review, reuse-rights decisions, a balanced benchmark corpus, and the clean-install test for the environment lock remain open.

## Whole-workspace UI audit — 2026-10-29

- In the local preview at `http://127.0.0.1:6004`, navigated Overview, Evaluate, Compare prompts, Prompt evolution, Fine-tune, Test cases, and Run history. Each page showed its expected visible H1 and the API-connected status.
- Across the seven pages, the visible-control name check found no unnamed controls, no duplicate IDs were found, and there was no horizontal overflow at 320px, 390px, 767/768px, 1024px, or 1440px CSS widths.
- No evaluation, prompt generation, case generation, training, review save, or history deletion was triggered. This is browser navigation/layout evidence, not an end-to-end model workflow or production-site check.
- The user confirmed that extraction `organization` labels should identify the claim actor. The private candidate packet already uses that definition; its labels and source-reuse decisions remain unreviewed.
- The task browser viewport was restored. Whole-workspace screen-reader/axe review, real provider-backed workflow checks, human label review, and reuse-rights decisions remain open.

## Public URL check — 2026-10-29

- Read-only fetch of `https://finetunedb.com/` returned a FinetuneDB marketing page that announces its acquisition by Opper AI and links to a separate app host. The fetched page did not identify or serve the PromptMesh workspace.
- This does not establish whether the domain is associated with the repository or whether PromptMesh is deployed elsewhere. The app host, authenticated flows, and any PromptMesh production deployment were not inspected.

## Event-year split and candidate expansion — 2026-10-29

- Added 35 public-source candidate groups with three controlled paraphrases per group to the ignored review CSV. At that point the packet had 351 rows / 117 groups: 66 groups from 2024, ten each from 2020, 2021, 2022, 2023, and 2025, plus one undated group. All 351 rows still needed human review; reviewed-label/note fields were blank and all new reuse decisions were unresolved. The CSV did not contain per-row reviewer/timestamp columns.
- Candidate pages are official organization or agency sources. Inputs are paraphrases, not quoted passages. `review_focus` preserves source-specific cautions about actor naming, dates, reported metrics, future plans, and product claims. Public availability does not establish reuse permission.
- Added deterministic `group-year-stratified-v1` splitting for datasets with at least 30 source groups. Groups stay intact; event-year signatures with at least three groups contribute one group to each held-out split, remaining held-out groups are allocated toward 15% per split, and sparse signatures stay in training. Smaller datasets retain `group-hash-v1`; both use seed 42.
- Adapter manifests are schema 4, prompt selections schema 2, and final reports schema 2. They record split seed and strategy. Benchmark selection rejects older adapters and policy mismatches; ordinary adapter inference remains available. Existing test reservations remain bound to their data fingerprint, so a previously consumed holdout needs a new dataset version.
- The packet’s structural split is 243 training / 54 validation / 54 test rows across 81 / 18 / 18 groups. Every year from 2020 through 2025 appears in both held-out splits. This is only split-planning evidence: labels, event dates, actor boundaries, source rights, and corpus representativeness still need review. 2024 remains 56.4% of groups and the examples are concentrated in a limited set of domains.
- Verification: 66 Python unit tests and 11 Node UI tests passed. Python compilation, `node --check static/app.js`, `bash -n run.sh`, `git diff --check`, CSV group/label consistency, and split isolation passed.
- Browser check at `http://127.0.0.1:5004/#finetune` displayed the updated split-policy note for the synthetic demo. The current backend on that tab returned 404 for the candidate-review API and exposed only the synthetic dataset, so this is stale-server UI evidence, not verification of the updated API. `run.sh` found listeners on 4004 (PID 33390), 5004 (PID 94097), and 6004 (PID 78788); it had no matching launcher PID file for the preview/test instances and declined to stop them. No process was stopped; the updated backend is not confirmed running on the main port.
- Branch: `codex/promptmesh-validation-selection`; implementation commit `9149c8c` was pushed successfully to the branch backing attached PR #2 (previously recorded as targeting `main`). GitHub API access failed during this turn, so the PR's current state and base were not independently rechecked. The private CSV is ignored and was not staged. No merge or deployment occurred.
- Next: review candidate groups and wording against each source, decide reuse rights, correct or exclude ambiguous items, then curate an authorized dataset before training or making quality claims. After that, train a schema-4 adapter and run one frozen benchmark plus the quantized comparison on that reviewed dataset.

## Paired benchmark difference intervals — 2026-10-29

- New frozen benchmark reports use schema 3 and include paired source-group bootstrap 95% intervals for record exact-match differences: validation-selected prompt vs. initial prompt, LoRA vs. base with the selected prompt, and each quantized arm vs. full-precision LoRA. One sorted set of source groups is resampled for both arms; deltas are example-weighted and defined as comparison minus reference. The report records the reference/comparison labels, 1,000 resamples, and seed 42.
- Fine-tune result cards show the paired delta and interval in percentage points. Legacy reports without the new field continue to render without a fabricated zero.
- Regression coverage includes unequal source-group sizes, identical arms (exactly zero paired interval), report wiring for prompt/LoRA/quantized comparisons, and legacy UI rendering.
- Verification: 68 Python tests and 11 Node tests passed; Python compilation, `node --check static/app.js`, `bash -n run.sh`, and `git diff --check` passed. Existing `datetime.utcnow()` deprecation warnings remain in `app.py` and `core/security.py`.
- Started the current app on the configured main port using `run.sh`; browser at `http://127.0.0.1:4004/#finetune` confirmed API connection and loaded the candidate queue (351 rows, 117 groups, zero labels reviewed, zero groups eligible). Paired result cards were verified with the Node UI fixture because no real frozen report exists. Existing listeners on test/preview ports 5004/6004 were left untouched.
- Commit `9370d39` (`Add paired benchmark difference intervals`) was pushed to `codex/promptmesh-validation-selection`, the branch backing attached PR #2, previously recorded as targeting `main`. No merge or deployment occurred.
- Next: human-review candidate labels against sources, determine reuse permission with evidence, and address year/topic/source imbalance. The current packet has no eligible groups, so there is still no real-data model-quality or quantization result. After review, curate a versioned dataset/card, train a fresh adapter, select on validation, and run the one-shot frozen comparison.

## Review packet coverage UI — 2026-10-29

- The Fine-tune review queue now shows draft group counts by proposed event year and source host, names the largest hosts, and states that this is not the reviewed benchmark composition. It interleaves the group selector by year and includes each group’s proposed year in its option label, so sequential review samples the available years early without splitting source variants.
- Live browser check at `http://127.0.0.1:4004/#finetune` showed 351 rows / 117 groups, zero labels reviewed, zero eligible groups, year counts 2020–2025 plus one undated group, and 37 hosts. The first six options span 2020, 2021, 2022, 2023, 2024, and 2025. No review was saved.
- Verification: 68 Python tests and 12 Node tests passed; Python compilation, `node --check static/app.js`, `bash -n run.sh`, and `git diff --check` passed. The responsive CSS uses the existing mobile breakpoint and allows the coverage text to wrap; narrow-screen rendering was not separately measured in this turn.
- Commit `46b603d` (`Surface candidate coverage in review queue`) was pushed to `codex/promptmesh-validation-selection`, the branch backing attached PR #2, previously recorded as targeting `main`. The local app remains on 4004. No merge or deployment occurred.
- Next: review every candidate label and wording against its source, record reuse permission evidence or exclude it, then curate a balanced versioned dataset/card. Until that is done, the benchmark gate remains closed and no real model-quality or quantized-inference result exists.

## Gated review-to-dataset export — 2026-10-29

- Added a loopback-only **Build a reviewed dataset** action. It includes only `REVIEWED` variants from groups where every variant is `REVIEWED` or `EXCLUDED`, at least one variant is reviewed, and the source has confirmed reuse evidence. Excluded variants and unresolved or rights-unconfirmed groups stay out.
- The exporter validates the JSONL with the production dataset parser, uses the existing deterministic group split, and requires at least 30 examples across 10 groups in both validation and final test. It writes a private JSONL plus a matching, source-referenced self-attested card without overwriting existing IDs; partial file creation is rolled back. Export does not train or score the final test set.
- Verification: 74 Python tests and 14 Node UI tests passed. Python/JavaScript compilation, `bash -n run.sh`, and `git diff --check` passed. Coverage includes eligibility filtering, held-out floors, file permissions, no-overwrite, rollback, remote API rejection, UI gating, and the no-training/no-test-scoring message.
- Browser at `http://127.0.0.1:4004/#finetune` showed API connected, 351 draft rows / 117 groups / zero reviewed labels / zero excluded variants / zero export-eligible groups, labeled export fields, a polite readiness status, and a disabled export button. No decision was saved and no dataset/card was created. Rendered checks at CSS widths 320, 390, 767, 1024, and 1440 showed no document overflow and the export panel stayed within the viewport; fields stack at 320/390, text and controls fit at 320/390/767, and the button remains disabled. No screen-reader or axe scan was run.
- The first live restart exposed row-specific `review_focus` values in 19 source groups. Group consistency now checks only the source title, URL, and date; a regression fixture varies review focus by variant. After the fix, the browser loaded the full packet successfully with the expected zero-eligible state.
- `./run.sh` initially declined port 4004 because PID 30834 had no managed PID record. Read-only process inspection confirmed it was this repo's `uvicorn app:app`; a temporary PID record let the guarded script stop it gracefully. The first daemon was reaped when its command ended, so launcher session 60039 was kept alive for the final restart (PID 38316). The live OpenAPI document includes `POST /api/training/review-packet/export`, and the Fine-tune page reports API connected at `http://127.0.0.1:4004/#finetune`.
- No human source/label/right review, real training, validation selection, frozen benchmark, or quantized corpus comparison occurred. The candidate packet remains a draft and supports no real quality claim.
- Next: inspect the responsive panel, then review each candidate and the reuse terms. Only after enough eligible groups exist should the private JSONL/card be exported, followed by training, validation-only prompt selection, and one frozen test run.
- Delivery: implementation commit `8d200e3` (`Add gated reviewed dataset export`) was pushed to `codex/promptmesh-validation-selection`, which updates existing PR [#2](https://github.com/arjeetanand/PromptMesh/pull/2). PR #2's `main` target was confirmed earlier; the latest `gh pr view` request failed because `api.github.com` was unreachable. No merge or deployment occurred.

## Pinned local training checkpoint — 2026-10-29

- Fixed LoRA training provenance: the previous runner relied on `model.config._commit_hash`, which was empty in the validated Transformers runtime. Training now resolves the cached Hub snapshot with `local_files_only=True`, pins that commit for both base model and tokenizer loading, and fails if a snapshot commit cannot be identified. Loading remains under the repository model ID, so adapter metadata does not embed this machine's cache path.
- Updated Fine-tune and README instructions: Qwen3-0.6B must already exist in the local Hugging Face cache; training does not download it.
- Added a regression test for offline snapshot resolution and malformed snapshot paths. Verification passed: 75 Python tests, 14 Node UI tests, Python compilation, `node --check static/app.js`, `bash -n run.sh`, and `git diff --check`.
- Clean-source MPS smoke run `53cdb2ff066647b4b1e09ef315a9be14` completed in 31.8 seconds against `Qwen/Qwen3-0.6B` revision `c1899de289a04d12100db370d81485cdf75e47ca`; tokenizer revision matches. The manifest records source commit `c62203d` with `source_dirty: false`, Python 3.12.13, macOS ARM64, MPS, and the training dependency versions. It scored six synthetic validation examples, kept six final-test examples unused, and recorded adapter exact match 50%, field accuracy 83.33%, and valid JSON 100%. These synthetic scores are workflow evidence only, not a model-quality result.
- Browser at `http://127.0.0.1:4004/#finetune` showed API connected, the updated cache-only note, and the completed clean-source run. The current launcher session is kept open so port 4004 remains available.
- Branch `codex/promptmesh-validation-selection`; implementation commit `c62203d` is on the branch for existing PR [#2](https://github.com/arjeetanand/PromptMesh/pull/2), previously confirmed to target `main`. No merge or deployment occurred.
- Remaining: 351 public-source candidate rows / 117 groups are still draft with zero reviewed labels and zero export-eligible groups. Human source, label, and reuse-rights review is required before creating a real benchmark, selecting on validation, running one frozen final test, or making quality claims. Quantized adapter inference remains a synthetic hardware-path check only.
- Next action: review the candidate packet and source reuse terms, then export only after the 30-example / 10-group floors are met in both validation and final test. Train and select with validation data, then run the final test once and compare full precision with the quantized inference arms.

## Synchronized benchmark timing — 2026-10-29

- Frozen benchmark generation now synchronizes MPS/CUDA before and after timed work and synchronizes model loads before stopping their load timers. CPU execution is synchronous. Throughput counts generated token IDs directly, so decoded text is no longer re-tokenized for this metric.
- Reports record the timing method without changing the report schema. Fine-tune results show the method for both standard and quantized runs and label older reports that lack it.
- Verification: 76 Python tests and 14 Node UI tests passed; Python compilation, JavaScript syntax, `bash -n run.sh`, and `git diff --check` passed. Tests use mocked generation; no real accelerator benchmark or model-quality run occurred.
- Restarted the app on `http://127.0.0.1:4004/#finetune`; the rendered browser page showed API connected. The timing explanation and legacy fallback were checked with UI fixtures because no real frozen report is available.
- Commit `03a20ae` (`Measure synchronized inference timing`) was pushed to `codex/promptmesh-validation-selection`, the existing PR #2 branch. PR #2 was previously confirmed to target `main`; the latest `gh pr view` failed because `api.github.com` was unreachable. No merge or deployment occurred.
- Remaining: public-source labels and reuse permissions are still unreviewed (351 draft rows / 117 groups / zero eligible groups). No real benchmark quality, throughput, or calibration result exists. Next: complete human review and rights checks, build an eligible balanced dataset/card, then train, select on validation, and run one frozen evaluation.

## Host MPS timing smoke — 2026-10-29

- Exercised `_measure_generation` on host MPS with cached `Qwen/Qwen3-0.6B` revision `c1899de289a04d12100db370d81485cdf75e47ca` and validation-only adapter `53cdb2ff066647b4b1e09ef315a9be14`. Hub and Transformers were offline; the only input was the fictional sentence “Northstar announced a research center in 2024.” No dataset, frozen-test reservation, benchmark report, or output artifact was written.
- One cold pass per arm: full-precision LoRA generated 24 token IDs in 0.4963 s (48.356 tok/s; valid JSON); NF4 generated 29 in 1.2044 s (24.079 tok/s; invalid JSON); INT8 generated 25 in 6.1787 s (4.046 tok/s; valid JSON).
- These are a hardware-path and timer check only. A single example with different output lengths cannot establish a reliable speed ranking or model quality; the NF4 invalid-JSON result is a synthetic smoke observation, not a benchmark estimate.
- The local app remains on port 4004. The existing data gate remains unchanged: all 351 candidate rows across 117 groups require human label/source review and reuse-rights evidence before any gold benchmark or calibration study.

## Review queue accessibility — 2026-10-29

- The source title, source date, and review guidance change when a reviewer selects another group. The source summary container is now an atomic polite live region so those updates can be announced without moving focus away from the group selector or navigation button.
- Added a Node regression for the live-region attributes. Verification: 15 UI tests passed; JavaScript syntax, `bash -n run.sh`, and `git diff --check` passed. Commit `80f10aa` (`Announce review source changes accessibly`) is on `codex/promptmesh-validation-selection`.
- Restarted the app on `http://127.0.0.1:4004/#finetune`; the rendered page showed API connected. Chrome DevTools MCP is not configured, so this pass used the in-app browser accessibility tree and source checks. A VoiceOver/screen-reader announcement and an axe scan remain unverified.
- The live review queue still has 351 draft rows / 117 groups / zero reviewed rows / zero eligible groups. No source decisions were saved. The human-reviewed benchmark and its quality claims remain pending.

## Synthetic adapter provenance — 2026-10-29

- Synthetic-demo status now stays next to its metrics in fine-tune results, saved adapter cards, benchmark adapter choices, and the trained-model selectors for evaluation, comparison, and evolution. The selectors are refreshed after adapter metadata loads so they show the provenance label.
- Added a focused UI regression. Verification passed: all 16 Node UI tests, JavaScript syntax checks, `bash -n run.sh`, and `git show --check`.
- Browser at `http://127.0.0.1:4004/#finetune` showed API connected, the 351-row / 117-group review queue with zero reviewed labels and eligible groups, plus the synthetic-only label on benchmark adapter choices and saved cards. The evaluation page also showed the label on each trained-model checkbox. The private review CSV was unchanged.
- Commit `20f0e35` (`Label synthetic adapter evidence in UI`) was pushed to `origin/codex/promptmesh-validation-selection`, updating existing PR #2 (previously confirmed to target `main`). A fresh `gh pr view 2` check failed because it could not connect to `api.github.com`; no merge or deployment occurred.
- Remaining: the synthetic adapter metrics are workflow evidence only; no human-reviewed benchmark or real quality/quantized comparison exists. Review source labels and reuse rights before creating that benchmark.

## Benchmark gate and draft-split audit — 2026-10-29

- Current local review packet remains 351 rows / 117 groups: zero reviewed rows, zero resolved groups, zero eligible groups. No labels, rights decisions, datasets, adapters, or benchmark artifacts were changed.
- Read-only audit found the validation and frozen-test gates still require the same dataset/card fingerprint, validation-only adapter provenance, held-out group floors, and exclusive test reservation. No leakage-gate defect was found; the card's human-review and rights claims are still local self-attestations.
- Structural projection using the unreviewed proposed labels gives validation years 2020–2025 = 2 / 2 / 1 / 1 / 10 / 2 groups and test = 2 / 1 / 2 / 2 / 10 / 1. This makes 2024 10 of 18 groups in both held-out splits; do not call it representative without curation and disclosure.
- Spot-checked the first six year-interleaved official source pages against the draft headline and core-claim fields. The facts broadly match, but this is an assistant spot-check, not the requested human review; all reuse rights remain unresolved and every paraphrase still needs reviewer approval.
- An additional assistant spot-check covered the next date-diverse groups for 2020–2025: ULA Mars 2020, Microsoft Windows 11, NVIDIA Hopper/H100, NIST AI RMF 1.0, Amazon's first color Kindle, and OpenAI o3/o4-mini. Their official pages support the proposed focal actor, event year, and core claim. The OpenAI page now includes a later availability/deprecation notice; keep this draft label limited to the historical launch event. This does not verify every paraphrase or grant reuse rights; none of these groups was marked reviewed. Per-source notes remain in the ignored local review-packet README.
- A third spot-check covered Xbox Series X/S, NIST's 2021 AI RMF request, DeepMind Gato, NASA OSIRIS-REx, Amazon Prime Day 2024, and Anthropic Claude 4. Their official sources support the core historical claims. Flagged the `Xbox` versus `Microsoft` actor granularity and `Gato` summary wording for the human reviewer; no row or rights state changed. Details are in the ignored local review-packet README.
- A fourth assistant source spot-check covered five existing non-2024 groups: FDA remdesivir EUA (2020), IBM's 2 nm chip design (2021), Google Research's PaLM announcement (2022), ESA's Juice launch (2023), and NASA's 2025 astronaut class. Their official pages support the focal claims and event years. Reviewer flags: keep EUA distinct from full approval, distinguish a chip design from manufactured silicon, avoid PaLM performance claims, confirm ESA as the claim actor, and note NASA's release was updated after its September 22 announcement. These rows remain unreviewed and rights-unresolved; packet counts and year skew did not change. Details are in the ignored local review-packet README.
- The user confirmed that `organization` labels the focal claim’s actor. The annotation guide and prompt already use that convention. The current review CSV has 351 rows / 117 groups; its 246-row JSONL counterpart was stale, so a separate 351-row current draft was generated while preserving the older snapshot. Neither file is reviewed gold data.
- Verification: full Python suite passed (76 tests); UI suite passed (16 tests). The in-app browser at `http://127.0.0.1:4004/#finetune` showed API connected and the unchanged 0-eligible review state. No provider calls, training jobs, or benchmark runs were started.
- Next: human-review labels and reuse terms, then curate the cohort to address the 2024 skew before exporting a versioned dataset/card. Only afterward train, select on validation, reserve and score the test once, and run quantized inference.
- Delivery: commit `6c3ebc2` (`Document draft benchmark year skew`) was pushed to `origin/codex/promptmesh-validation-selection`, updating existing PR #2 (target `main` was previously confirmed). The latest PR query again failed to connect to `api.github.com`; no merge or deployment occurred.

## Calibrated inference follow-up — 2026-10-29

- Added an optional Optimum Quanto W8A8 post-training quantization arm to the existing frozen benchmark. It loads the pinned local LoRA adapter, merges it into the base, quantizes INT8 weights and activations, calibrates activation ranges, freezes the model, and evaluates on the same selected test rows as the full-precision LoRA arm.
- Calibration selects at most 16 deterministic training source groups and one label-free input per group. It uses the validation-selected prompt but reads no validation or final-test examples. The report stores the training split, input-only SHA-256, group/example counts, sample seed, momentum, prompt hash, backend version, quantization time, and calibration time.
- Added optional API/UI selection, mixed bitsandbytes/Quanto report provenance, and rendered calibration details. The optional backend list now includes `optimum-quanto==0.2.7`; it requires `ninja`, which is absent from the current `.venv`.
- Verification: full Python suite passed (81 tests) and the Node UI suite passed (16 tests); Python compilation, JavaScript syntax, launcher syntax, and `git diff --check` passed. These tests mock Quanto. No Quanto package installation, model inference, MPS calibration smoke, or reviewed-dataset benchmark has run yet.
- The local review sheet still has 351 unreviewed rows / 117 groups / zero eligible groups. The current 351-row schema-shaped JSONL was regenerated from the CSV; the older 246-row JSONL was preserved as a historical snapshot. The actor convention is now confirmed by the user and is already encoded in the prompt and annotation guide.
- Browser evidence: the current review UI shows the 351-row/117-group packet, zero reviewed and eligible rows, and the actor convention. The training panel labels the bundled 48-example dataset synthetic-only and blocks prompt selection/final benchmarking. `/api/health` returned healthy through the persistent local session; runtime discovery listed only bitsandbytes INT8/NF4, so Quanto is not selectable yet.
- Pending: install Quanto and `ninja` in the project `.venv` only after user approval, run one synthetic MPS canary with the cached Qwen checkpoint, pin the dependency closure in the environment lock, then restart and verify the Quanto option on port 4004. No real-data quality claim is supported until human labels and reuse rights are reviewed.
- Delivery: branch `codex/promptmesh-validation-selection`, commit `d9d3a15`, pushed to [PR #2](https://github.com/arjeetanand/PromptMesh/pull/2), which is open and targets `main`; it has not been merged. The guarded `./run.sh` restart left PromptMesh healthy at `http://127.0.0.1:4004` (PID 78625). The in-app Fine-tune page reloaded with API connected and the draft review gates visible.

## Current workflow verification — 2026-10-29

- Re-ran the existing full suite: 81 Python tests and 16 Node UI tests passed. Python emitted existing `datetime.utcnow()` deprecation warnings from `app.py:912` and `core/security.py:121`.
- The live Fine-tune review page at `http://127.0.0.1:4004/#finetune` showed API connected, 351 draft rows across 117 groups, zero reviewed labels, and zero export-eligible groups. The accessibility tree exposes names for organization/year/claim fields, per-variant decisions, reuse status/evidence, and save/export actions. No review was saved.
- Chrome DevTools MCP is not configured, so no axe scan or screen-reader announcement check was run. Earlier targeted manual layout and contrast checks remain the available evidence; whole-workspace assistive-technology verification is open.
- No training or benchmark job ran. The source packet remains unreviewed and rights-unresolved; real-data model-quality and quantized-quality results are still unavailable.

## Public-source review packet expansion — 2026-10-29

- Added ten proposed source groups to the ignored local review sheet, each with three controlled variants: WHO's COVID-19 pandemic characterization and OpenAI's GPT-3 few-shot research post (2020); GitHub Copilot's technical preview and NASA Perseverance's Mars touchdown (2021); OpenAI's ChatGPT research preview and NASA's Artemis I launch (2022); Meta's gated LLaMA research release and ISRO's Chandrayaan-3 soft landing (2023); OpenAI's GPT-5 introduction and Alibaba Group's Qwen3 announcement (2025).
- Checked the linked official pages at the focal claim/date level. The private packet README records each URL and cautions: distinguish WHO's characterization from a PHEIC declaration; treat GPT-3/Qwen3 company-reported results as claims, not independent benchmark evidence; preserve the original Copilot technical-preview date; distinguish LLaMA's gated research access; and keep each historical event separate from later page updates or product status. These are assistant spot-checks only.
- At the packet-expansion snapshot, the ignored packet had 381 draft rows / 127 groups: 12 groups each for 2020, 2021, 2022, 2023, and 2025; 66 groups for 2024; and one undated group. All rows remained `NEEDS_HUMAN_REVIEW`; reviewed-label/note fields were blank; reuse terms were unresolved. The CSV does not include per-row reviewer/timestamp columns.
- At that snapshot, CSV and JSONL aligned in row order and proposed labels; each group had three variants and the parser accepted the JSONL. The seed-42 split was train 267/89 groups, validation 57/19, test 57/19; 2024 contributed 10 of 19 groups to each held-out split.
- A possible year-balanced planning cohort at that stage used 12 groups per year, selecting 12 of 66 proposed 2024 groups; it projected to 50/11/11 groups or 150/33/33 rows. It was a planning projection only, not evidence of quality, rights, or representativeness.
- Browser check: the Fine-tune page at `http://127.0.0.1:4004/#finetune` loaded with API connected and showed 381 rows / 127 groups / zero reviewed labels / zero excluded variants / zero export-eligible groups. Its proposed-year coverage matched the CSV, and the export action was disabled. No decision was saved.
- Delivery: commit `8175dc0` (`Expand public-source review packet`) is pushed to `origin/codex/promptmesh-validation-selection`, updating existing PR #2, previously confirmed to target `main`; it remains unmerged. A fresh PR-state query failed because `api.github.com` was unreachable and the web fetch returned a cache miss.
- Pending: human-review all source labels and variants and verify reuse terms. Do not create a benchmark card, train/select, score the final test, or make résumé quality claims from this draft.

## MPS quantization smoke and reproducibility audit — 2026-10-29

- Runtime identity: the live API and an approved host-context probe of the project `.venv` report MPS available. The default sandboxed shell reports CPU, so its device result is not representative of the app process. Runtime: macOS 26.7.1 arm64, Python 3.12.13, Torch 2.14.1, Transformers 5.21.0, PEFT 0.21.2, TRL 1.16.0, bitsandbytes 0.50.0. Quanto and `ninja` are absent. The source revision during the smoke was `5253efc975ac43fcb05e466d47b45d5c61ded72b`, with a clean tree.
- Ran an in-memory smoke using cached Qwen/Qwen3-0.6B revision `c1899de289a0`, validation-only synthetic adapter `67eb726005d4434181b3c95512ca0577` (adapter hash prefix `ea9c29c2d681`), and one fixed fictional input. All arms used the extraction prompt, deterministic generation, and the app's 128-token limit; no dataset rows, provider calls, benchmark reservation, or report files were used.

| Arm | Load seconds | Inference seconds | Generated tokens | Tokens/sec | Model footprint bytes | JSON keys valid |
|---|---:|---:|---:|---:|---:|---|
| FP32 LoRA | 4.4290 | 0.5512 | 27 | 48.981 | 2,388,787,712 | Yes |
| bitsandbytes INT8 + LoRA | 0.8936 | 6.7463 | 27 | 4.002 | 756,285,952 | Yes |
| bitsandbytes NF4 + LoRA | 2.0609 | 0.9864 | 24 | 24.332 | 536,084,992 | Yes |

- These are single-input, single-pass synthetic timings. They are sensitive to load/cache state, output length, and runtime conditions; footprint is not peak device memory. No arm's schema-valid JSON establishes extraction accuracy, and the INT8 arm was slower in this smoke. Do not present these values as a quality result, stable speed ranking, or throughput benchmark.
- Read-only audit confirmed the Quanto configuration digest includes method, split, group limit, seed, and momentum, while the report stores the deterministic calibration-input fingerprint and runtime metadata. `pip check` found no broken requirements; its pip-cache warning was non-fatal. A fresh clean-environment install remains unverified.
- No Quanto calibration run occurred because `optimum-quanto==0.2.7` and `ninja` are not installed. The real-data quantized study still requires reviewed labels/rights, a selected adapter, and a one-shot frozen test run.

## Keyboard skip navigation — 2026-10-29

- Added a keyboard-visible skip link before the app frame. Its `#workspace` target is programmatically focusable, and the hash router preserves the selected page for this anchor while retaining the Overview fallback for unknown fragments.
- Added a focused Node regression for the target and route behavior. The full Python suite passes (81 tests) and the UI suite passes (17 tests); JavaScript and launcher syntax checks and `git diff --check` pass. Python emitted existing `datetime.utcnow()` deprecation warnings.
- Browser check before the restart: Tab focused the skip link; Enter changed the hash to `#workspace`, focused the main workspace, and kept Fine-tune selected. No review data was saved.
- The guarded `./run.sh` command reported port 4004 healthy in its command environment, but the embedded browser returned `ERR_CONNECTION_REFUSED`; a later listener check found no process on port 4004. CUA also reports the Mac is locked. The final served CSS and live page could not be checked after that restart. Resume by unlocking the Mac, starting the app through its desktop project terminal, and repeating the keyboard check.
- Screen-reader and axe checks remain open. No provider calls, training jobs, or benchmark runs were started.
- Delivery: commit `71daeb0` was pushed to `origin/codex/promptmesh-validation-selection`, updating the existing PR #2 (previously verified to target `main`). A fresh PR-state query failed because `api.github.com` was unreachable. No merge occurred.

## Résumé and interview framing — 2026-10-29

- Added a current résumé line and interview talk track to the README. It describes the implemented source-grouped evaluation, validation-only selection, local Qwen3-0.6B LoRA/SFT, runtime provenance, and post-training quantization paths without claiming real-data gains.
- The wording explicitly says the available MPS timings are one synthetic smoke, Quanto W8A8 is optional, and QLoRA training is not implemented. Real-data quality and performance claims remain gated on a reviewed, rights-cleared corpus.

## Benchmark gate recheck — 2026-10-29

- At the prior benchmark gate check, the ignored CSV had 381 rows / 127 groups, all `NEEDS_HUMAN_REVIEW`; reviewed labels/notes were empty and reuse text was unresolved or required source-specific terms review. The CSV has no per-row reviewer/timestamp columns.
- Current draft JSONL has the same 381 rows / 127 groups; the 246-row / 82-group JSONL is historical. No benchmark or prompt-selection report JSON was found under `training/`; the artifact-name search only matched the tracked benchmark-card template.
- Next: restore the app from the desktop terminal after unlock, review source claims and reuse terms, select a balanced rights-cleared cohort, then export the card and run validation selection before a single frozen-test comparison.
- Delivery: commits `431cf2c` and `4ed72d6` are pushed to `origin/codex/promptmesh-validation-selection`. PR #2 is currently open and targets `main` at head `4ed72d696e37db66f65008342312c629dbef5a33`; it remains unmerged.

## Calibration fingerprint binding — 2026-10-29

- Confirmed `organization` means the focal claim actor; the extraction prompt and annotation guide already follow that rule. The clarification did not change any candidate labels or review decisions.
- The frozen Quanto W8A8 configuration hash now includes the SHA-256 of the exact deterministic, input-only calibration rows selected from the training split. The same rows feed the backend canary and inference arm; test examples and labels remain excluded from calibration.
- Clarified that the two NF4 smoke observations were separate runs with different adapters: one returned parseable JSON, while the earlier run did not. Neither smoke establishes extraction quality.
- Verification: 81 Python tests and 17 Node UI tests passed; `node --check static/app.js`, `bash -n run.sh`, and `git diff --check` passed. Existing `datetime.utcnow()` deprecation warnings remain. Quanto calibration was not run because Quanto and `ninja` are absent.
- Implementation commit: `1abc362` (`Bind calibration inputs to benchmark configuration`) on `codex/promptmesh-validation-selection`, for existing PR [#2](https://github.com/arjeetanand/PromptMesh/pull/2) targeting `main`. No merge occurred.
- No model inference, data review, or browser session occurred. Port 4004 had no listener when checked; Quanto calibration remains unverified because Quanto and `ninja` are absent.

## Draft actor/year input consistency — 2026-10-29

- A mechanical scan found three proposed actor labels that used expanded names absent from the corresponding inputs, plus one GPT-3 row whose proposed year was not visible in the input. I checked the linked official source pages, aligned the actor forms across each group, and made the GPT-3 year explicit in that input.
- Regenerated the ignored JSONL draft mirror from the CSV. Structural verification passed: 381 rows / 127 groups / three variants each; all proposed actor names and years appear in each corresponding input; proposed labels are consistent within groups; the mirror matches row order and labels; and the application dataset parser accepts it.
- All rows remain `NEEDS_HUMAN_REVIEW`; reviewed labels/notes are empty and every reuse condition remains unresolved. The CSV has no per-row reviewer/timestamp columns; the export card records reviewer role/time. These changes prepare the packet for review and are not human label approval or rights clearance. No training or benchmark was run.
- Source pages checked: [NASA Ames annual report](https://www.nasa.gov/ames-partnerships/annual-report-2024/), [Alibaba Qwen3 announcement](https://www.alibabagroup.com/en-US/document-1853940226976645120), [DOE award profile](https://www.energy.gov/osbp/annual-doe-small-business-awards-program), and [OpenAI GPT-3 paper announcement](https://openai.com/index/language-models-are-few-shot-learners/).

## Official-source audit and review handoff — 2026-10-29

- Read-only source checks covered 25 candidate groups across NASA, DOE, and EPA. Corrections aligned the NASA Intuitive Machines event year with its 2021 contract award (with a planned 2024 delivery), included D.C. in the EPA lead-grant recipient scope, flagged a DOE gasoline chronology ambiguity, tightened a DOE HALEU review note, and fixed date-article/capitalization issues in candidate inputs. No row was approved or excluded.
- Current ignored packet: 381 draft variants across 127 source groups (12 groups each for 2020, 2022, 2023, and 2025; 13 for 2021; 65 for 2024; one undated). All rows remain `NEEDS_HUMAN_REVIEW`; reviewed labels/notes are blank; reuse status is unresolved. The packet remains outside Git and outside `training/datasets/` loadable datasets.
- Structural validation passed: each source group has three variants; proposed labels are consistent within groups; actor/year values appear in each input; CSV/JSONL mirrors align; and the application parser accepts the draft. This confirms packet shape only, not source-label accuracy or reuse permission.
- Browser verification at `http://127.0.0.1:4004/#finetune`: API connected; the page displayed 381 rows / 127 groups / 0 reviewed / 0 excluded / 0 export-eligible, with year counts matching the packet and the export button disabled. No review decision was saved. Port 4004 is running under `./run.sh`.
- The review UI defines `organization` as the named claim actor. For each group, review all three phrasings against its linked page; correct or exclude variants, then resolve reuse permission with evidence. Public availability alone does not clear reuse rights. Export remains blocked until enough reviewed, rights-cleared source groups satisfy both held-out split floors.
- Official pages checked include [NASA’s Intuitive Machines contract announcement](https://www.nasa.gov/news-release/nasa-selects-intuitive-machines-for-new-lunar-science-delivery/), [NASA’s Earth-science aircraft selections](https://science.nasa.gov/earth/nasa-selects-new-aircraft-driven-studies-of-earth-and-climate-change/), [DOE’s gasoline reserve contracts](https://www.energy.gov/articles/doe-awards-contracts-sale-northeast-gasoline-supply-reserve-americans-hit-road-summer), [DOE’s HALEU award](https://www.energy.gov/ne/articles/us-department-energy-awards-17-million-first-round-haleu-criticality-benchmarking), and [EPA’s lead-grant announcement](https://www.epa.gov/newsreleases/biden-harris-administration-announces-26-million-grants-protect-children-lead-drinking).
- No training, prompt selection, frozen test, model-quality claim, or rights determination used this packet. Next action: review candidates and source reuse terms in the local workbench, then export only a reviewed, permission-cleared dataset.

## Cross-version final-test reuse guard — 2026-10-29

- The leakage audit found that a previous final-test group could re-enter training or validation after a dataset version changed, and the same test examples could be reserved again under a new dataset ID or after training-only edits.
- Added a private SQLite registry containing only SHA-256 fingerprints for source-group IDs and whitespace/case-normalized inputs. Training, validation prompt selection, and later final-test runs reject known identities. New reservations serialize in a SQLite write transaction. Legacy reservations are indexed only from an exact matching original dataset snapshot; if that snapshot is missing or changed, the guard fails closed.
- Verification: all 88 Python tests and 17 Node UI tests pass; Python compile, JavaScript syntax, launcher syntax, and `git diff --check` pass. Existing `datetime.utcnow()` deprecation warnings and the Torch macOS redirect note remain.
- Browser check at `http://127.0.0.1:4004/#finetune`: API connected; the review queue showed 381 draft rows / 127 groups / 0 reviewed / 0 excluded / 0 eligible. The new reuse disclosure was visible, and the synthetic demo remained explicitly unavailable for benchmark selection. No review decision was saved.
- Identity matching depends on stable source-group IDs or exact normalized input text. It cannot detect paraphrases when both the ID and wording change. It protects future training/selection after a final-test reservation; it does not independently establish annotation quality or reuse rights.
- No human review, model training, prompt selection, frozen benchmark, or quantization run used the draft packet. Keep the 381-row review and source-reuse gate open.
- Delivery: implementation commit `695680b813ff0740d34bc04d41a33425c5b040bf` is pushed on `codex/promptmesh-validation-selection`. Verified existing PR [#2](https://github.com/arjeetanand/PromptMesh/pull/2) is OPEN and targets `main`. It remains unmerged.
- The app is live at `http://127.0.0.1:4004`. The guarded launcher reported healthy, but its detached process did not persist in this command environment; a persistent foreground Uvicorn session now serves the browser verification.

## Workspace navigation focus — 2026-10-29

- Sidebar, in-app, and fragment navigation now move focus to the selected page's `h1`, which has `tabindex="-1"`; the initial route does not move focus. This gives keyboard and assistive-technology users context after a workspace transition.
- Added a Node regression covering focusable headings, visible keyboard focus, sidebar navigation, initial-load behavior, and fragment changes. Verification: 88 Python tests and 18 Node UI tests pass; Python/JavaScript/launcher syntax checks and `git diff --check` pass.
- Live browser check at `http://127.0.0.1:4004/#finetune`: pressed Enter on Overview; the accessibility tree reported focus on the `Your model lab` heading, and the blue focus ring was visible. The API remained connected; no review decision was saved.
- A full screen-reader and axe audit remains pending. This browser check verifies focus movement and accessible-tree state only.
- Delivery: commit `6bdf60a026b5a8f0645109b0588180b856cd723c` is on `codex/promptmesh-validation-selection`; it is being pushed to existing PR [#2](https://github.com/arjeetanand/PromptMesh/pull/2), which targets `main`. No merge.

## Cold/warm per-request latency — 2026-10-29

- Frozen benchmark report schema 7 records a cold first request for each fresh model load, then times every request in one full scored pass. It reports cold latency, median warm p50, nearest-rank warm p90, warm sample count, and total scored-pass inference time. The first test input is generated twice; only the scored pass contributes task metrics.
- The timing protocol is included in the frozen configuration fingerprint, so a report created under the prior single-pass method cannot be reused as if it used the new protocol. The UI displays the cold/warm fields on the full-precision LoRA and quantized inference cards.
- Verification: 88 Python tests and 18 Node UI tests passed; Python compilation, JavaScript syntax, launcher syntax, and `git diff --check` passed. Existing `datetime.utcnow()` deprecation warnings and the Torch macOS redirect note remain.
- Live browser check at `http://127.0.0.1:4004/#finetune`: page loaded and API connected. It still shows 381 draft rows / 127 source groups / 0 reviewed; synthetic demo data remains blocked for prompt selection and final benchmark. No review or benchmark action was performed. The new result-card fields are covered by the Node UI test; a live completed report is not available to render in the browser.
- Limitations: no real model inference or quantized comparison was run; the default synthetic demo cannot support quality claims. Peak device memory remains unmeasured, and the one-pass p50/p90 values are not repeated-run throughput estimates. Human label review and source-reuse clearance remain open.
- Delivery: implementation commit `6c2753d` and handoff commit `0301ae0` are pushed on `codex/promptmesh-validation-selection`. Existing PR [#2](https://github.com/arjeetanand/PromptMesh/pull/2) was verified OPEN against `main`; no merge occurred.
- Run instructions: `./run.sh` serves the local app on port 4004. The app is currently available at `http://127.0.0.1:4004/#finetune`.
- Next action: review the draft variants and source-reuse terms in the local workbench, then train and run the frozen benchmark only on reviewed, permission-cleared data.

## Backend-aware device memory reporting — 2026-10-29

- Frozen benchmark schema 8 fingerprints the memory measurement protocol. CUDA runs reset PyTorch allocator peak counters after model load and report peak allocated/reserved bytes. Allocations made outside the PyTorch allocator may be missing. MPS runs record Metal-driver allocated bytes before and after inference, including cached allocations; these are snapshots, not peaks. CPU runs show device memory as unavailable. Model footprint remains separate.
- Quantized and full-precision result cards distinguish CUDA peaks, MPS snapshots, unavailable values, and reports that predate memory metadata. The report note explains the MPS and CUDA limitations.
- Verification: 89 Python tests and 18 Node UI tests passed; Python compilation, JavaScript syntax, launcher syntax, and `git diff --check` passed. CUDA and MPS memory APIs were exercised with deterministic mocks; no model inference was run. The default `.venv` reports CPU only; the live Fine-tune page reports API connected and MPS for the host runtime.
- Live browser check at `http://127.0.0.1:4004/#finetune`: 381 draft rows / 127 source groups / 0 reviewed, and the synthetic demo remains blocked from final benchmarking. There is no completed report to render; CUDA, MPS, and unavailable memory-card rendering is covered by the Node UI test.
- Limitations remain: no human-reviewed benchmark, quantized quality comparison, or actual memory result exists. MPS cannot provide a peak through the exposed PyTorch API, and the CUDA allocator metric may exclude third-party allocations.
- Delivery: implementation commit `8e6107e` is on `codex/promptmesh-validation-selection` for existing PR [#2](https://github.com/arjeetanand/PromptMesh/pull/2), targeting `main`. No merge.
- Next action: review labels and source reuse rights before the real training and frozen quantized comparison.

## Year-aware review queue — 2026-10-29

- Added a proposed-event-year filter to the Fine-tune review queue. The selector and Previous/Next navigation now share the same interleaved group order; switching years warns before discarding unsaved review edits. The filter only narrows navigation and does not select a 72-group cohort or change label, reuse-rights, or export decisions.
- Reconciled `training/datasets/README.md` with the current ignored draft: 381 rows / 127 groups, split 267/57/57 rows across 89/19/19 groups. The draft has 65 groups proposed for 2024, 13 for 2021, 12 for each other dated year, and one undated. All remain unreviewed.
- Verification: all 89 Python tests and 19 Node UI tests pass; `node --check static/app.js`, `bash -n run.sh`, and `git diff --check` pass. Browser check on port 4004 at 1440px, 768px, and 390px had API connected and no horizontal overflow. The 2024 filter displayed 65 groups and navigation stayed within that year; switching to All years followed the interleaved order. Queue remained at 0 reviewed / 0 excluded / 0 export-eligible. No review decision was saved.
- Delivery: commit `de8bf4d0972fc19f2463ba0f695500741aefbf1f` is pushed to `codex/promptmesh-validation-selection`. It updates the existing PR #2 branch, whose recorded target is `main`; the GitHub API could not refresh PR state this turn (`error connecting to api.github.com`). No merge.
- Limitations: no human-reviewed or rights-cleared benchmark exists, and no cohort has been selected. The exported year distribution must be checked before claiming balance. A full screen-reader/axe audit and automated visual inspector were not completed; the inspector's Chrome process exited early. App remains available at `http://127.0.0.1:4004/#finetune` via `./run.sh`.
- Next action: review the candidate labels and reuse terms, then make an explicit reviewed cohort selection before reporting evaluation or quantization results.

## Deterministic reviewed-year cohort export — 2026-10-29

- Added a separate **Year-balanced pilot · 12 per year** option to the local review export. It selects 12 fully reviewed and rights-cleared source groups for each reviewed event year from 2020 through 2025 with the deterministic `year-balanced-v1` SHA-256 ranking and seed 42. **All eligible groups** remains the default option. Previewing and exporting do not edit the review packet.
- The private schema-v2 benchmark card records the complete eligible group/year candidate list, cohort rule, seed, and selected group IDs. Dataset validation recomputes the selection and checks that rows, reviewed years, and source references agree with the card. Export readiness also checks actual grouped validation and test floors after cohort selection.
- This cohort balances year counts only. It does not balance topics, source hosts, organizations, or writing styles, and it is not a representativeness claim. With 72 fully included groups and three variants per group, the current split projects to 50/11/11 groups (150/33/33 rows), but excluded variants change those counts and readiness computes the actual split.
- Verification: all 92 Python tests and 20 Node UI tests passed; Python compilation, JavaScript and `run.sh` syntax, and `git diff --check` passed. In the browser, the app at `http://127.0.0.1:4004/#finetune` reported API connected. At 1600px and 390px CSS widths there was no horizontal overflow; the mobile export fields used one column and the balanced readiness reason showed 0/12 groups for every year. In both cohort modes, export stayed disabled at zero eligible groups. Browser console errors: none. The viewport was reset after testing.
- The foreground PromptMesh listener remains on port 4004. The browser check is positive; a shell `curl` from the command sandbox could not reach that isolated localhost listener, so it is not an independent endpoint check.
- No review decision, rights determination, dataset export, training run, prompt selection, final benchmark, or real-data quantization measurement was performed. The ignored packet remains 381 draft rows / 127 groups / 0 reviewed labels / 0 eligible groups. Human label review and reuse clearance are still required before model-quality claims.
- Delivery: implementation commit `19c40e1` is pushed on `codex/promptmesh-validation-selection`. Existing PR [#2](https://github.com/arjeetanand/PromptMesh/pull/2) was confirmed OPEN against `main` after the push. No merge occurred.
- Next action: review candidate labels and source reuse conditions, then inspect the exported cohort and actual split counts before training, selecting a prompt, or reserving the frozen test set.

## Training lock verification helper — 2026-10-29

- Added `python -m training.verify_lock` to validate that the active environment is Python 3.12 on macOS ARM64 and that every package in `requirements-training-macos-arm64.lock` is present at its exact pinned version. The helper is read-only and rejects unpinned/duplicate lock entries. README setup and provenance sections include the command; `pip check` remains a separate dependency-integrity check.
- Verification: all 47 pins matched the current `.venv`; `pip check` reported no broken requirements. Five focused lock-verifier tests and all 97 Python tests passed; the UI suite passed all 20 tests; Python compilation, JavaScript and launcher syntax, and `git diff --check` passed.
- This validates the existing environment only. No fresh virtual environment or packages were installed; a clean install has not been proven, and the app requirements remain unpinned.
- Delivery: verifier commit `789bf33` is committed on `codex/promptmesh-validation-selection` for existing PR #2 targeting `main`. No clean install was run.
- Next: after approval, create a disposable environment under `/private/tmp`, install the documented app requirements plus the training lock, and run the verifier, `pip check`, and import smoke checks. Do not replace the active `.venv` or download model weights.

## Public-source candidate expansion — 2026-10-29

- Added 14 candidate groups and 42 paraphrased rows to the ignored local review packet. The current CSV and JSONL mirror now contain 423 rows across 141 groups: 14 groups for 2020, 16 for 2021, 15 each for 2022, 2023, and 2025, 65 for 2024, and one undated group. The 20261028 JSONL snapshot remains unchanged and historical.
- Spot-checked the 14 focal claims and dates against official NOAA, NASA/JPL, USGS, WHO, and Meta pages. The private review-packet README records each source link and ambiguities such as local/UTC dates, publication year versus event year, partner/vehicle versus mission actor, and the difference between NOAA and Scripps measurements.
- Structural verification passed: PromptMesh’s parser accepts the JSONL; all 141 groups have three unique variants and consistent proposed labels; each proposed actor and year appears in every input; CSV and JSONL match in row order, input, and output; and all rows remain `NEEDS_HUMAN_REVIEW` with blank reviewed fields and unresolved/source-specific reuse review.
- The exact seed-42 group-year split projects to 297/63/63 rows across 99/21/21 groups. Proposed labels remain unreviewed, so these are planning counts, not benchmark evidence. No dataset/card was exported; no review decisions, training, prompt selection, inference, or frozen test run occurred.
- Updated the tracked dataset guidance with the new year counts and split projection. The ignored packet instructions and checklist now record the expanded review queue and the remaining review gate.
- Browser verification remains incomplete. The user unlocked the Mac, and CUA inventory now lists PromptMesh tabs on ports 4004, 5004, and 6004. However, direct tab inspection still fails with `browser.user is unavailable`; the tab titles alone do not confirm rendered content. The default shell sandbox cannot connect to port 4004, but the project-owned listener responds to `GET /api/health` with HTTP 200 and `status: healthy` when local-network access is allowed. `./run.sh` uses main port 4004 (test 5004, preview 6004); recheck the rendered page when tab control is available.
- Remaining: human-review every source and variant, verify source-specific reuse rights, and create a matching reviewed dataset/card before any model-quality or quantization claim. The clean training-lock installation and full browser recheck also remain open.
- Delivery: the public-source expansion and documentation are committed on `codex/promptmesh-validation-selection` for existing PR #2 targeting `main`; no merge.

## Frozen benchmark failure analysis — 2026-10-29

- Added privacy-safe failure analysis to every frozen benchmark arm: invalid JSON/schema outputs, examples and groups with at least one error, and per-field mismatch counts, overall and by gold year. Invalid outputs count as mismatches for every field. Reports contain only aggregate counts, not source text, group IDs, or generations.
- Bumped frozen report schema to v9 and included the report schema version in the configuration fingerprint so an older report cannot silently stand in for the new shape.
- Added a semantic, horizontally scrollable table to each arm’s UI details and clarified that Quanto calibration/quantization sub-times are included in load time.
- Verification: 99 Python tests and 20 UI tests passed; Python compilation, JavaScript syntax, `run.sh` syntax, and `git diff --check` passed. The synthetic fixture verifies error categories, year slices, and that no text or IDs are saved.
- Runtime: the detached launcher reported healthy but its process did not persist after the tool returned. A persistent foreground Uvicorn session now serves port 4004 (PID 94162); `/api/health` returns HTTP 200, the API reports MPS and bitsandbytes 0.50.0, and `/static/app.js` serves the new renderer.
- Browser: Edge rendered Fine-tune at 1185px with API connected, 423 candidate rows / 141 groups / 0 reviewed / 0 excluded / 0 eligible. The document and body widths both equal 1185px; console errors were empty. No review decision was saved. The advertised 390px viewport override left the actual viewport at 1185px, so mobile verification remains open. The new failure table was not shown against a real report because no human-reviewed benchmark exists.
- Remaining: human-review labels, wording, and reuse terms; run the matched real-data prompt/LoRA/quantized comparison only after that gate; test the failure table at mobile widths and complete the full screen-reader/axe audit. Effective trainer/adapter settings were added in the follow-on section below.
- Next: keep the 423-row packet review-only until human review is completed, then export a matching benchmark/card and run the validation-selected, frozen matched study.
- Delivery: implementation commit `6cfc68d` is on `codex/promptmesh-validation-selection`, the branch for existing PR #2 targeting `main`; no merge.

## LoRA manifest reproducibility — 2026-10-29

- Added schema-v5 `training_configuration` snapshots from the constructed TRL `SFTConfig` and PEFT `LoraConfig`, including precision, optimizer/schedule, batch and accumulation settings, sequence length, LoRA rank/alpha/dropout/targets, plus float32 local-only base-model loading.
- Made bf16 and fp16 explicitly false on the float32 training path. The installed `SFTConfig` raised a BF16/GPU compatibility error with its current defaults; the regression now constructs the pinned config and verifies the saved settings without loading model weights.
- Frozen benchmark eligibility now requires a complete schema-v5 configuration. Older schema-v4 adapters remain available for ordinary inference, but cannot be selected for a new final benchmark.
- Added an accessible expandable configuration disclosure to training results and saved-adapter rows. Legacy adapters say their effective settings were not recorded.
- Frozen report schema v10 embeds the adapter configuration, includes its digest in the report configuration fingerprint, and renders the same settings disclosure in benchmark results.
- Verification: 103 Python tests and 21 UI tests passed; Python compilation, JavaScript syntax, launcher syntax, and `git diff --check` passed.
- Browser: the fresh Edge Fine-tune page at 1185px had no document overflow or console errors. The previously saved adapters were legacy and correctly showed the missing-settings note; a follow-on schema-v5 smoke and live result disclosure are recorded below. Edge's 390px viewport override still leaves the page at 1185px.
- No model was loaded or trained during this implementation-only change. Human review of candidate labels and reuse terms, a clean-lock installation, and real matched benchmark/quantization measurements remain open.
- Next: review and rights-clear the public-source packet, then train a schema-v5 adapter on the reviewed split and run the validation-selected, frozen matched study.
- Delivery: implementation commit `0836d5f` is on `codex/promptmesh-validation-selection`, the branch for existing PR #2 targeting `main`; no merge.

## Live schema-v5 training smoke — 2026-10-29

- The updated server initially was not loaded: a first synthetic run produced an older schema-v4 manifest. The guarded launcher restarted the project-owned process, but that detached process exited when the command returned, so PromptMesh was started in a persistent foreground Uvicorn session on port 4004 (PID 19515).
- Completed a one-epoch local run on `entity_extraction_demo` with Qwen/Qwen3-0.6B on MPS: 36 training rows, 6 validation rows, 6 final-test rows reserved, and 35.8 seconds elapsed. Validation exact match was 50.0%, field accuracy 83.3%, and valid JSON 100%; these synthetic results are workflow evidence only, not model-quality evidence. The final test was not scored.
- The resulting local adapter run `1bc8d7cebab34ff4bc648c385b04a1ea` has manifest schema v5. Its configuration digest validates; the snapshot records one epoch, LoRA rank 8 / alpha 16, float32, bf16/fp16 false, local-only weight loading, and remote code disabled.
- The live training result shows the complete TRL trainer, PEFT LoRA, and model-loading settings in an accessible disclosure. The saved-adapter list also exposes the configuration. The 423-row source-review packet remains at 0 reviewed labels and 0 eligible groups.
- The separate earlier run `51ce874d57b6411e8f0cadb8578a61e1` remains a schema-v4 legacy adapter from the stale server; it was not deleted or used for any benchmark.
- Mobile viewport verification and the human-reviewed, rights-cleared training/benchmark remain open.
- Next: review source labels and reuse rights, then export the authorized dataset and run validation selection before the matched frozen comparison.
