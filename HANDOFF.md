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

- Prepared an ignored review packet under `training/datasets/review_packets/`: 19 concise source-based candidate inputs in `UNREVIEWED_DRAFT_candidates_20261028.jsonl`, a review sheet with source links/draft labels/rights status/reviewer fields, and packet instructions.
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
- Updated the dataset instructions, README, checklist, and handoff. The production JSONL parser accepted the draft; the 67 groups split 47 / 10 / 10 with 141 / 30 / 30 rows, and all reviewer fields remain blank. This follow-up does not modify application code or load the packet.
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
- The packet now has 246 rows across 82 source groups: 66 proposed 2024 groups, three groups each for 2020, 2021, 2022, 2023, and 2025, and one undated group. It is still severely imbalanced for year extraction. Every row remains `NEEDS_HUMAN_REVIEW`; new groups have unresolved reuse permission and blank reviewer fields.
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

- Added 35 public-source candidate groups with three controlled paraphrases per group to the ignored review CSV. The packet now has 351 rows / 117 groups: 66 groups from 2024, ten each from 2020, 2021, 2022, 2023, and 2025, plus one undated group. All 351 rows still need human review; reviewer fields are blank and all new reuse decisions are unresolved.
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
