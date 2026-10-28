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
- Local integration smoke used a cached Qwen checkpoint, an existing synthetic-demo adapter, and one fixed synthetic input. NF4 and INT8 both generated output in the sandbox's CPU-only runtime. A previous host MPS smoke confirmed BNB NF4/INT8 operation on MPS, but the new adapter-attached path has not been exercised on MPS from this sandbox.
- Regression coverage includes NF4/INT8 configuration, API validation, the pre-reservation canary, identical test rows, report fields, and calibration labeling. The full Python suite passed (57 tests), the Node UI suite passed (9 tests), Python compilation, JavaScript syntax, launcher syntax, and `git diff --check` passed.
- Edge rendered the updated Fine-tune markup on the existing 5004 tab. At 1440px and 390px, document width matched the viewport with no horizontal overflow; there were no browser console errors. The running host API is an older process that does not return quantization runtime metadata, so those controls remained disabled in that tab.
- A fresh `run.sh` attempt reported ready on 6004 inside the isolated command environment, but Edge could not connect to that instance. The existing 4004/5004 host processes were left untouched because their ownership could not be verified from this sandbox. The final branch is not confirmed running on the main port.
- The adapter-attached NF4/INT8 smoke generated output using a cached Qwen checkpoint, an existing synthetic-demo adapter, and one fixed synthetic input in the CPU-only command environment. The host Fine-tune screen reports MPS, and an earlier base-only BNB smoke passed on MPS, but this new adapter-attached path was not verified on MPS.
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
- Verification: 64 Python `unittest` tests passed; 9 Node UI checks passed; Python and JavaScript syntax, launcher syntax, and `git diff --check` passed. Edge rendered the new review heading at its current desktop viewport, but the existing API returned 404 for the new route, so the group fields and save action did not render in that session. The skill inspector could not launch Chrome. The live queue still needs a fresh API process and responsive checks at 1440/768/390px.
- Branch: `codex/promptmesh-validation-selection`. The implementation commit `bf1fe93` (`Add local source candidate review workbench`) and handoff commit `43ff26f` are pushed to the existing [PR #2](https://github.com/arjeetanand/PromptMesh/pull/2) branch. PR #2 was previously verified against `main`; its current GitHub checks and merge state were not re-queried.
- A scoped `run.sh` attempt returned “Port 6004 is already in use” and left the listener running. Ports 4004, 5004, and 6004 remain occupied; no process was stopped. Automatic review rejected a later unscoped debug invocation because it could have restarted 4004; that invocation did not run.
- Next: safely manage the existing preview process, then verify the queue at 1440/768/390px and push the follow-up handoff update to PR #2. Human source review, reuse clearance, year diversification, reviewed JSONL/card creation, model-quality results, and a real quantized comparison remain open.
