# PromptMesh UI and local LoRA checklist

- [x] Inspect the checkout, existing UI/API, prompt version, model registry, and active changes.
- [x] Create and work on `codex/promptmesh-ui-redesign`.
- [x] Redesign the responsive evaluation workspace while reconnecting the existing evaluation, comparison, evolution, test-case, and history flows.
- [x] Add a synthetic extraction demo dataset with strict JSONL validation and deterministic group-level train/validation/test splitting.
- [x] Add deterministic held-out schema, field-accuracy, and exact-record metrics.
- [x] Add bounded local Qwen3-0.6B LoRA/SFT jobs, local adapter persistence, and model-registry integration.
- [x] Add the Fine-tune page, saved adapter list, progress reporting, loss visualization, and base-versus-adapter results.
- [x] Add local dataset readiness, content fingerprints, and per-field held-out scores.
- [x] Apply the requested black, `#0F41F3`, white, and sparing `#F9B318` palette across the workspace.
- [x] Keep private datasets and generated adapter runs out of Git; document that the demo set is not benchmark or résumé evidence.
- [x] Run focused training tests, syntax checks, and loopback API checks after the dataset fingerprint and metric display changes.
- [x] Reinspect the palette and Fine-tune page at desktop and mobile widths; verify the mobile drawer opens and closes without navigating away.
- [x] Complete a one-epoch synthetic LoRA/SFT run on MPS, show its held-out results in the UI, and load the saved adapter through the model registry. The demo scores are workflow evidence only, not a quality claim.
- [x] Commit and push the LoRA/SFT implementation and design-token follow-up (`8a4e0db`, `31ba8a0`, `7767a81`) to PR #1.
- [x] Confirm the live PR target is `main` (`gh pr view 1`).

## Illustration follow-up

- [x] Read the referenced illustration task and inspect PromptMesh's hero and true empty states.
- [x] Generate an original two-pose PromptMesh companion and optimize the transparent images as WebP.
- [x] Add the companion to the overview and empty run-history states with reduced-motion-aware animation.
- [x] Verify image loading, desktop/mobile rendering, and the history empty state in the browser.
- [x] Include the original illustration implementation in PR #1 targeting `main`.

## Section illustration follow-up

- [x] Add a compact companion vignette to every non-overview workspace page, with a motif specific to that page.
- [x] Verify all six sections at desktop and 390px mobile widths with no horizontal overflow.
- [x] Include the section illustrations in PR #1 targeting `main`.

## Evaluation reliability follow-up

- [x] Create a dedicated branch from the current clean PromptMesh tree.
- [x] Fix classification and verification scoring weights and prevent judge outages from returning a score.
- [x] Propagate judge failures through the scorer, app jobs, CLI, and diagnostic script.
- [x] Add regression tests and clarify the LLM-judge scope in the UI and README.
- [x] Run the complete suite (29 passed), Python compilation, JavaScript syntax check, and diff check.
- [x] Verify the Evaluate label, API connection, mobile layout at 390px, and browser console.
- [x] Commit as `913e392` and update PR #1 targeting `main`.

## Benchmark integrity follow-up

- [x] Create a dedicated validation-selection task branch from the current PR head.
- [x] Score prompted base and LoRA adapter on validation rows during training; keep final-test rows unscored.
- [x] Label older saved-adapter test metrics as legacy because they were exposed during iterative training.
- [x] Record prompt version/hash, tokenizer revision, metrics split, and final-test usage in new run manifests.
- [x] Prepare a non-ingested JSONL row template and an `unreviewed` benchmark-card template; keep filled data and cards gitignored.
- [x] Label prompt-evolution examples as optimization inputs, disclose LLM-judge heuristic scores, and include score/input provenance in exported results.
- [x] Run focused training and evolution regressions, the full suite, syntax checks, and desktop/mobile UI checks at 390px.
- [x] Add a separate gold-validation prompt selector and frozen final-benchmark runner; evolution remains a heuristic workflow whose candidates can be copied into the selector.

## Next résumé milestones

- [x] Add evidence-based résumé wording and an interview talk track that distinguish implemented workflow from real-data results still pending human review.
- [ ] Create a human-reviewed, versioned gold benchmark with grouped train/validation/test splits; keep prompt evolution and model selection on validation data only.
- [ ] Compare base, prompt-only, and LoRA results on the same untouched test examples; report task metrics and uncertainty.
- [ ] Measure quantized versus unquantized inference quality, latency, and memory on a declared backend and hardware.
- [ ] Publish a reproducible run manifest and demo that distinguish synthetic workflow checks from model-quality evidence.

## Gold benchmark workflow

- [x] Validate the reviewer card against the exact JSONL fingerprint, review/count metadata, and source-group split; keep synthetic data ineligible.
- [x] Mark readiness as a self-attested review card, not independently verified human review; require at least 30 validation and test examples across 10 source groups each.
- [x] Compare extraction/v1 and a candidate prompt on gold validation data only, and save a hash-checked selection record tied to a validation-only schema-v4 LoRA adapter.
- [x] Reserve the frozen test set before inference, then compare base+initial prompt, base+selected prompt, and LoRA+selected prompt on identical test rows; include aggregate metrics and source-group bootstrap intervals.
- [x] Add paired source-group bootstrap intervals for exact-match differences across prompt, LoRA, and quantized-inference arms; surface the comparison direction and percentage-point delta in Fine-tune results.
- [x] Add gold-year test metrics and source-group counts for every frozen benchmark arm; show grouped confidence intervals when each year slice has at least two groups.
- [x] Store selection/report artifacts locally with private permissions and keep them out of Git.
- [x] Add Fine-tune UI controls and background-job progress/result states for prompt selection and final benchmarking.
- [x] Review Fine-tune at desktop in Edge and inspect 1440px, 768px, and 390px layouts; synthetic data is blocked and the inspector reports no horizontal overflow. No physical phone test was performed.
- [x] Rerun the full Python suite (51 passed), UI job checks (8 passed), syntax checks, and whitespace validation.
- [x] Open PR #2 targeting `main` after verifying PR #1 was already merged; leave PR #2 unmerged.
- [x] Add optional bitsandbytes LLM.int8 and NF4 runtime configuration and Fine-tune controls for a quantized inference comparison.
- [x] Run a fixed synthetic backend canary before reserving test data; record matched test metrics, grouped intervals, load/inference time, generated-token rate, and model footprint.
- [x] Explain that bitsandbytes methods do not use offline calibration; distinguish Quanto W8A8 post-training calibration from QLoRA training and leave AWQ/GPTQ out.
- [x] Define `organization` as the claim actor in extraction prompt definition 1.1.0 and the annotation guide.
- [x] Prepare a private 246-row public-source candidate review packet across 82 source groups with source URLs, draft labels, unresolved rights status, and review-decision fields; keep it outside the loadable dataset directory.
- [x] Add 15 official-source candidate groups dated 2020, 2021, 2022, 2023, and 2025 to extend the packet’s year coverage.
- [x] Add 35 more official-source candidate groups; the local review packet now has 351 draft rows across 117 groups, with 10 groups per proposed year from 2020, 2021, 2022, 2023, and 2025.
- [x] Stratify datasets with at least 30 source groups by event-year signature; record the seed and strategy in adapter, prompt-selection, and frozen-report provenance and reject incompatible prior artifacts.
- [x] Show the selected split strategy in the Fine-tune dataset readiness panel.
- [ ] Human-review every candidate and wording variant against its linked source, confirm reuse rights, and build a more balanced, representative dataset before claiming general extraction quality.
- [x] Add regression coverage for INT8/NF4 configuration, identical test rows, calibration labeling, and invalid or unavailable API selections.
- [x] Add a fingerprinted cold-first-request and warm per-request p50/p90 protocol; render its timing fields in quantized result cards.
- [x] Capture CUDA PyTorch allocator peaks and MPS driver allocation snapshots; label snapshots and unavailable values distinctly from peaks.
- [x] Assert that the loaded extraction prompt definition 1.1.0 keeps the actor/recipient rule.
- [x] Check Fine-tune at 1440px and 390px in Edge; the document has no horizontal overflow or browser console errors.
- [x] Verify adapter-attached NF4/INT8 generation on MPS with one synthetic canary input; this confirms the hardware path only, not benchmark quality.
- [ ] Supply and human-review an authorized real dataset, train a new schema-v5 adapter, and run a real frozen benchmark; no model-quality result exists yet.
- [ ] Run the calibrated quantized comparison on a human-reviewed corpus; no real-data quality result exists.

## Local candidate review workbench

- [x] Add a loopback-only review API for the ignored public-source candidate CSV, with validated group updates and atomic writes.
- [x] Add a Fine-tune review queue that keeps each source's phrasings together, applies the actor label rule, and separates label review from reuse permission.
- [x] Show proposed-year and source-host counts in the review queue so candidate packet imbalance is visible before curation.
- [x] Keep the private packet out of Git and the loadable training datasets until an authorized reviewed JSONL is created.
- [x] Add a gated local export that includes only reviewed variants from fully resolved groups with confirmed reuse evidence, then writes a private JSONL and self-attested benchmark card only when validation and final-test floors pass.
- [x] Add regression checks for source grouping, safe writes, symlink rejection, and loopback-only access even with an API key.
- [x] Verify the export gate, held-out split floors, no-overwrite behavior, rollback, and “no training or test scoring” UI message; no dataset was exported because the current packet has zero eligible groups.
- [x] Open the updated Fine-tune page in the local browser and confirm the export fields have accessible names, the readiness text is announced, and the button stays disabled at zero eligible groups.
- [x] Inspect the export panel at 320px, 390px, and tablet width in a rendered browser; the fields stack on mobile, controls and text fit, and no document overflow appears at 320px, 390px, or 767px.
- [ ] Review candidates against sources, confirm reuse permissions, address topic/source-type imbalance, and create an authorized benchmark dataset/card.
- [x] Verify the new Fine-tune queue in the browser at 1440px, 768px, and 390px; confirm group navigation and mobile menu behavior. No physical phone test was performed.
- [x] Audit the live candidate-review form: all visible controls are named, tab order is logical, status regions and heading structure are present, key text contrast is at least 4.5:1, and there is no horizontal overflow at 320px, 390px, 768px, 1024px, or 1440px.
- [ ] Verify the review flow with a screen reader and an automated axe-core scan; neither was run in this manual browser audit.

## Runtime reproducibility follow-up

- [x] Record Python, platform, device, and installed training/inference package versions in adapter, validation-selection, and frozen-benchmark records.
- [x] Record the PromptMesh source revision and clean/dirty working-tree state in each stage's runtime metadata, and surface it in the Fine-tune UI.
- [x] Surface training, selection, and benchmark runtime metadata in the Fine-tune UI and distinguish older runs with missing metadata.
- [x] Pin the current Python 3.12 / macOS ARM64 LoRA/SFT and bitsandbytes dependency closure; verify every lock pin matches the active `.venv` and `pip check` passes.
- [x] Add a repeatable read-only verifier for exact package pins and the lock's Python/platform target; test normalization, duplicates, mismatch reporting, and platform rejection.
- [x] Run the verifier against the active `.venv`: all 47 pins match, and `pip check` reports no broken requirements.
- [x] Install `requirements.txt` and the training lock into a disposable Python 3.12.13 / macOS ARM64 environment; verify 47 exact pins, `pip check`, dependency imports, and all 109 Python tests without downloading model weights.
- [ ] Consider pinning the general application requirements separately; the current clean install confirms today's resolution, not future reproducibility.

## Whole-workspace UI audit — 2026-10-29

- [x] Navigate Overview, Evaluate, Compare, Evolution, Fine-tune, Test cases, and Run history in the local browser; confirm the API-connected status and visible page heading.
- [x] Check visible control names, duplicate IDs, and horizontal overflow at 320px, 390px, 767/768px, 1024px, and 1440px on all seven pages.
- [ ] Complete a whole-workspace screen-reader and automated accessibility audit; the current evidence is a targeted manual browser inspection.
- [ ] Verify provider-backed evaluation, model generation, local training, and quantized benchmark flows end to end; no jobs or provider calls were started in this audit.

## Cached model revision follow-up — 2026-10-29

- [x] Resolve the cached Hugging Face snapshot commit before loading the LoRA base model and tokenizer, with local-only loading enforced.
- [x] Add regression coverage for commit extraction and reject snapshot paths that cannot prove a pinned revision.
- [x] Complete a local MPS synthetic smoke run; manifest records the same immutable base/tokenizer revision and keeps the six-example final test unused. Its scores remain workflow-only.
- [x] Repeat the smoke run after committing the fix; the 31.8-second MPS run records source commit `c62203d` with a clean tree.
- [x] State the local checkpoint-cache requirement consistently in the Fine-tune help and README.
- [ ] Human-review and license-check enough candidate groups for a real benchmark; no real quality result is available yet.

## Benchmark timing accuracy — 2026-10-29

- [x] Synchronize MPS/CUDA around frozen-benchmark generation and model loading; count generated output token IDs instead of re-tokenizing decoded text.
- [x] Record the timing method in reports and show a clear fallback for older reports that lack it.
- [x] Add focused regressions for generated token counts, accelerator synchronization, report metadata, and legacy UI rendering.
- [x] Restart the main local app on port 4004 and confirm the Fine-tune page reports API connected.
- [x] Exercise the synchronized timer on local MPS with the cached validation-only adapter and one fictional prompt across full precision, NF4, and INT8.
- [ ] Run this timing method on the human-reviewed benchmark corpus; no real quality or throughput result exists yet.

## Review queue accessibility — 2026-10-29

- [x] Announce the selected source title, date, and review guidance when the user changes source groups.
- [x] Add a regression check for the polite, atomic live region; all 15 UI tests pass.
- [x] Restart the app on port 4004 and confirm the Fine-tune page reports API connected.
- [x] Recheck the live review form and current suites: labeled source and reuse controls are present; all 81 Python and 16 UI tests pass.
- [ ] Verify the announcement with a screen reader and run axe; neither was run in this browser check.

## Synthetic adapter provenance — 2026-10-29

- [x] Label synthetic-demo metrics as workflow-only in fine-tune results, saved adapters, benchmark adapter choices, and trained-model selectors.
- [x] Add a focused UI regression; all 16 UI tests pass, with JavaScript syntax and diff checks clean.
- [x] Reload the Fine-tune page on port 4004 and confirm the updated UI is served; inspect evaluation model labels too.

## Draft benchmark split audit — 2026-10-29

- [x] Compute the seed-42 validation/test year composition from draft labels and document that 2024 contributes 10 of 18 groups to each held-out split.
- [x] Apply the user-confirmed actor label convention and reconcile the current 351-row CSV with a full current JSONL draft; preserve the older 246-row JSONL snapshot as historical.
- [x] Recheck selection and frozen-test gates; full Python suite (76) and UI suite (16) pass.
- [x] Spot-check five existing non-2024 source groups for core claim/date support; record source-specific review cautions without changing labels or rights fields.
- [ ] Human-review labels and reuse rights, then curate a balanced cohort before exporting or claiming representative benchmark results.

## Calibrated inference follow-up — 2026-10-29

- [x] Add optional Quanto INT8 weight + INT8 activation PTQ beside bitsandbytes inference, merging the full-precision LoRA adapter before quantization.
- [x] Calibrate on at most one input-only example per training source group; exclude labels, validation, and test inputs and record hashes, split, sampling seed, momentum, and timings.
- [x] Add API and Fine-tune controls, mixed-backend report provenance, calibrated result timing, and regressions for train-only sample selection, loader order, matched test rows, and UI rendering.
- [x] Full Python suite passes (81) and Node UI suite passes (16); Python compilation, JavaScript syntax, launcher syntax, and `git diff --check` pass.
- [x] Verify the local API health and quantization runtime on port 4004: the service is healthy and exposes bitsandbytes INT8/NF4; Quanto is absent from the current `.venv`.
- [x] Recheck the browser review workbench: it shows 351 draft rows / 117 source groups / 0 reviewed labels / 0 eligible groups and the actor-label rule; synthetic data remains blocked from benchmark selection.
- [ ] After approval, install `optimum-quanto==0.2.7` and `ninja` in `.venv`; run a synthetic local MPS calibration/inference canary with the cached checkpoint, update the environment lock, restart the app, and verify the enabled Quanto option in the browser.

## Navigation and background-job follow-up

- [x] Add a Back to overview control to every non-overview page.
- [x] Allow local LoRA training and prompt evolution progress dialogs to close while polling continues in the open tab.
- [x] Show running, paused, completed, and failed status in the top bar; link completion to its results without changing the current page.
- [x] Add four Node regression checks for LoRA/evolution progress dismissal, reopening, completion status, and results navigation.
- [x] Verify tab navigation and responsive header behavior in the browser.
- [x] Include the navigation and background-job follow-up in PR #1 targeting `main`.

## Public-source review packet expansion — 2026-10-29

- [x] Add ten proposed source groups for 2020–2025: WHO pandemic characterization, OpenAI GPT-3 few-shot study, GitHub Copilot technical preview, NASA Perseverance landing, OpenAI ChatGPT research preview, NASA Artemis I launch, Meta LLaMA research release, ISRO Chandrayaan-3 landing, OpenAI GPT-5 introduction, and Alibaba Qwen3 introduction.
- [x] Keep all new rows as drafts and retain source-specific cautions for event dates, actor granularity, gated access, page updates, and company-reported model claims.
- [x] Regenerate the ignored schema-shaped JSONL mirror and validate the current 381-row / 127-group packet, three variants per group, blank review fields, unresolved reuse states, HTTPS source URLs, and parser acceptance.
- [x] Recompute the seed-42 projection: 267/57/57 rows across 89/19/19 groups; each held-out split has 2 groups from 2021 and 9 from 2024.
- [x] Document a possible 72-group year-balanced planning cohort (12 groups per year from 2020–2025; choose 12 of 13 proposed 2021 groups and 12 of 65 proposed 2024 groups only after review), projecting to 150/33/33 rows across 50/11/11 groups.
- [x] Refresh the review workbench at `http://127.0.0.1:4004/#finetune`; it displays 381 rows / 127 groups / 0 reviewed / 0 excluded / 0 eligible, the year counts, and a disabled export action. No decision was saved.
- [x] Recheck the ignored packet files: the review CSV and current JSONL each contain 381 rows / 127 groups, all rows still need human review, reviewed-label/note fields are blank, the CSV has no per-row reviewer/timestamp columns, and no benchmark/selection report artifact exists under `training/`.
- [x] Scan every variant for actor/year presence; source-check and correct three draft actor-name expansions and one missing input year, regenerate the ignored JSONL mirror, and keep all review/rights states pending.
- [x] Source-audit 25 groups from the 2024-heavy batch against official pages and all three variants; correct the NASA contract event year, EPA recipient scope, and grammar/date notes without marking any row reviewed.
- [x] Persist hashed final-test source-group/input identities across dataset versions and reject overlap before training, validation selection, or another frozen test; legacy reservations require the exact original dataset snapshot to be safely indexed.
- [x] Cover duplicate dataset IDs, training-only edits, changed event-year splits, renamed groups with repeated inputs, legacy reservations, and disjoint data in benchmark regressions.
- [ ] Human-review source fidelity, actor/year/claim labels, every variant, and reuse terms before exporting a dataset or making benchmark claims.

## MPS quantization smoke — 2026-10-29

- [x] Resolve the runtime discrepancy: the default sandbox sees CPU, while the host-context check and live API both report MPS using the project `.venv`.
- [x] Run FP32 LoRA, bitsandbytes INT8, and NF4 on fixed synthetic inputs at the app's 128-token limit. A later smoke returned parseable JSON for all three; an earlier run on another adapter produced invalid JSON for NF4.
- [x] Record load/inference time, generated token count, and model footprint as one hardware smoke only; no dataset rows, test reservation, or benchmark artifact was used.
- [x] Confirm `pip check` reports no broken requirements and that Quanto/`ninja` remain absent; record W8A8 calibration settings and bind the exact input fingerprint into the frozen-run configuration hash.
- [x] Assert the calibration-input fingerprint participates in the frozen configuration hash; run the 81-test Python suite and 17-test UI suite.
- [ ] Repeat quantized quality/performance measurement on a human-reviewed, rights-cleared benchmark; the synthetic smoke is not model-quality or throughput evidence.

## Year-balanced review navigation — 2026-10-29

- [x] Add a proposed-event-year filter and make Previous/Next use the same interleaved order as the source-group selector.
- [x] Keep filtering/navigation separate from label decisions, source reuse rights, cohort selection, and export eligibility.
- [x] Reconcile the dataset README's packet counts and seed-42 split table against the current ignored draft.
- [x] Verify 89 Python tests, 19 Node UI tests, JavaScript/launcher syntax, and `git diff --check`.
- [x] Verify the live review workbench at 1440px, 768px, and 390px with API connected and no horizontal overflow; confirm the packet remains at 0 reviewed / 0 eligible.
- [ ] Human-review every candidate and its reuse conditions; verify the exported year distribution before describing a cohort as balanced.

## Deterministic reviewed-year cohort export — 2026-10-29

- [x] Add an explicit balanced-pilot export choice while preserving the all-eligible export path.
- [x] Select 12 source groups per 2020–2025 from human-reviewed event years with a deterministic SHA-256 seed-42 rule; fail readiness if any year lacks 12 eligible groups or either held-out split misses its example/group floor.
- [x] Record eligible group/year candidates, the strategy, seed, and selected groups in a versioned benchmark card; validate that the dataset rows, references, and deterministic selection agree.
- [x] Keep cohort preview/export read-only with respect to review labels and reuse decisions; add regressions for underfilled years, determinism, tampered provenance, and UI gating.
- [x] Run the complete Python suite (92 passed), UI job suite (20 passed), Python compilation, JavaScript and launcher syntax checks, and `git diff --check`.
- [x] Verify the export choice in the browser at desktop and 390px widths with API connected, no horizontal overflow, the correct per-cohort readiness message, and the export action disabled at zero reviewed/eligible groups; confirm there are no browser console errors.
- [ ] Human-review labels and reuse rights, then inspect the selected cohort and actual split composition before any model or quantization claim.

## Host-diverse reviewed cohort — 2026-10-29

- [x] Keep the 12-groups-per-year pilot and maximize distinct normalized HTTPS hosts before repeating hosts; use deterministic seed-42 SHA-256 ranking.
- [x] Record every eligible candidate group ID, reviewed year, normalized host, and source URL plus selected groups in schema-v3 cards; keep schema-v2 year-only cards loadable.
- [x] Add export/UI regressions for host maximization, deterministic ordering, balanced repeat fill, source URL validation, candidate provenance, and legacy card loading.
- [x] Verify the live 4004 browser shows the host-diverse explanation, API connected, and 423 rows / 141 groups / 0 reviewed / 0 eligible without saving review data.
- [x] Measure actual 320, 390, 767, and 1440 CSS px layouts: document width matches the viewport, review cards have no internal overflow, and export fields switch to one column on mobile; restore the browser viewport afterward.
- [x] At 390 CSS px, inspect the rendered review workbench: all 55 visible controls have names, there are no duplicate IDs or visible images without alt text, 11 live regions are present, and browser console errors are empty. This is a targeted DOM audit; full screen-reader and axe checks remain open.
- [ ] Review labels, variants, and reuse rights; inspect the real selected host distribution before training or quality claims. Current projection uses unreviewed proposed labels only.

## Keyboard skip navigation — 2026-10-29

- [x] Add a keyboard-visible skip link to the main workspace and keep in-page fragments from redirecting the active app route.
- [x] Add regression coverage for the skip-link target and route preservation; all 81 Python tests and 17 Node UI tests pass, JavaScript and launcher syntax checks pass, and `git diff --check` is clean.
- [x] In the browser, Tab focuses the skip link and Enter moves focus to the workspace while Fine-tune remains selected; no review was saved.
- [x] Recheck the final served page after restarting the local app; the in-app browser reports API connected and the updated holdout disclosure is visible.
- [ ] Complete the full screen-reader and axe audit.

## Cross-version final-test reuse guard — 2026-10-29

- [x] Persist hashed source-group and normalized-input identities for frozen tests; block known test identities from later training, validation selection, or final-test use across dataset versions.
- [x] Safely index older reservation/report artifacts only when their exact original dataset snapshot is still available; otherwise fail closed.
- [x] Verify with 88 Python tests, 17 Node UI tests, Python/JavaScript/launcher syntax checks, and `git diff --check`.
- [x] Restart the app on port 4004 and confirm the Fine-tune page is connected and discloses the exact-match limitation.
- [ ] Human-review the 423-row / 141-group source packet and reuse terms before training or benchmark claims.

## Workspace navigation focus — 2026-10-29

- [x] Move keyboard and fragment navigation focus to the selected page heading; leave initial page load focus unchanged.
- [x] Add a UI regression for sidebar navigation, initial load, hash changes, and focusable page headings.
- [x] Verify in the browser that selecting Overview focuses its `h1`; API remains connected on port 4004.
- [ ] Complete a full screen-reader and axe audit.

## Public-source candidate expansion — 2026-10-29

- [x] Add 14 official-source candidate groups (42 paraphrase rows) across 2020, 2021, 2022, 2023, and 2025; keep all entries in the ignored review packet.
- [x] Keep every proposed label in `NEEDS_HUMAN_REVIEW`, reviewed-label/note fields blank, and reuse permission unresolved.
- [x] Regenerate the ignored JSONL mirror; verify 423 rows / 141 groups, three variants per group, consistent labels, visible proposed actor/year in every input, exact CSV/JSONL mirror order, and application parser acceptance.
- [x] Recompute the seed-42 split with PromptMesh: 297/63/63 rows across 99/21/21 groups; update the dataset guide and review handoff with proposed-year counts and review caveats.
- [x] Spot-check the 14 focal claims against their official primary pages and record actor/date ambiguities for human review.
- [x] Confirm the project-owned 4004 listener matches this checkout and `/api/health` returns HTTP 200 with `status: healthy`; the default command sandbox cannot reach loopback.
- [x] Inspect the rendered Fine-tune review queue in Edge at 1185px: API connected, 423 rows / 141 groups / 0 reviewed / 0 excluded / 0 export-eligible; no horizontal overflow or console errors, and no review was saved.
- [ ] Check the new failure-analysis details/table in a real browser at a 390px viewport; Edge's advertised viewport control did not change the actual 1185px viewport during this run.
- [ ] Render failure analysis from an actual human-reviewed benchmark; no real benchmark report exists yet.
- [ ] Human-review every source, label, and wording variant; confirm source-specific reuse rights before creating a benchmark dataset/card.

## Frozen benchmark failure analysis — 2026-10-29

- [x] Add per-arm aggregate counts for invalid JSON, invalid schema, failed examples/groups, and field mismatches overall and by gold year; reports do not retain source text, group IDs, or generated answers.
- [x] Bump frozen report schema to v9 and bind that schema version into the configuration fingerprint.
- [x] Render the breakdown in a semantic, horizontally scrollable table with overlap and privacy notes; clarify that Quanto calibration/quantization times are included in load time.
- [x] Verify with 99 Python tests, 20 Node UI tests, Python compilation, JavaScript syntax, launcher syntax, and `git diff --check`.
- [x] Restart PromptMesh in a persistent foreground session on port 4004; API health is HTTP 200 and the app reports MPS with bitsandbytes 0.50.0.
- [x] Serve-check the updated UI script and inspect the live Fine-tune queue in Edge; no review decisions were saved.
- [ ] Inspect the failure-analysis report at desktop and mobile sizes once a real reviewed benchmark is available; complete the full screen-reader/axe audit.
- [x] Add the remaining effective trainer/LoRA settings to saved training manifests for more self-contained reproduction.

## LoRA manifest reproducibility — 2026-10-29

- [x] Snapshot effective SFT trainer and PEFT LoRA settings, including optimizer, schedule, precision, batch sizes, accumulation, sequence length, rank, alpha, dropout, and target modules.
- [x] Record float32 model loading, local-only weight access, and disabled remote code execution without storing an output path or credentials.
- [x] Make bf16/fp16 false explicit for the float32 training path; test the installed TRL config constructor without loading model weights.
- [x] Bump the adapter manifest contract to schema v5 and require the complete saved configuration for frozen-benchmark eligibility; schema-v4 adapters remain available for inference.
- [x] Show the full configuration in training results and saved-adapter details; label older runs whose settings were not recorded.
- [x] Embed the adapter settings in frozen reports and include their digest in the benchmark configuration fingerprint; bump the frozen report schema to v10.
- [x] Full Python suite (103) and Node UI suite (21) pass; Python compilation, JavaScript/shell syntax, and `git diff --check` pass.
- [x] Inspect the updated Fine-tune page in Edge at 1185px: no overflow or console errors; existing adapters are clearly labeled as legacy.
- [ ] Inspect the configuration disclosure on a schema-v5 adapter at mobile width; the schema-v5 smoke exists, but Edge's 390px viewport override did not apply.
- [ ] Human-review the 423-row public-source packet and reuse terms before creating a real training dataset or benchmark.

## Live schema-v5 training smoke — 2026-10-29

- [x] Run one local SFT epoch on the synthetic demo: 36 train rows, 6 validation rows, and 6 reserved final-test rows; the final test was not scored.
- [x] Verify the saved adapter manifest is schema v5 and its full training-configuration digest validates; precision is float32 with bf16/fp16 disabled and local-only weight loading.
- [x] Keep saved-adapter tokenizer and model loading local-only, preserve the pinned base revision, and cover both loader arguments with a regression test.
- [x] Verify the live training result and saved-adapter row expose the effective trainer, LoRA, and model-loading settings.
- [x] Confirm the review packet remains at 423 candidates, 0 reviewed labels, and 0 eligible groups.
- [ ] Run a schema-v5 fine-tune on a human-reviewed, rights-cleared dataset after review is complete.

## Source reuse terms context — 2026-10-29

- [x] Add an optional HTTPS source-terms URL to the reviewer card, with copy that states the link does not grant or confirm reuse permission.
- [x] Keep legacy packets compatible and reject invalid/non-HTTPS terms URLs.
- [x] Add the Apple Website Terms link to the three Apple M1 variants in the ignored review packet; leave every label and reuse decision pending.
- [x] Verify 108 Python tests, 22 Node UI tests, JavaScript syntax, launcher syntax, and `git diff --check`.
- [x] Verify the live Apple card at `http://127.0.0.1:4004/#finetune`: terms link is visible, reuse status remains “Not confirmed,” and the queue remains 423 rows / 141 groups / 0 reviewed / 0 eligible.
- [x] Keep launcher state under a stable `/tmp/promptmesh-<uid>` path so changing `TMPDIR` does not lose process ownership; keep the app available on port 4004.
- [ ] Human-review source labels and source-specific terms; no reuse permission or benchmark quality result is confirmed.

## Frozen benchmark runtime fingerprint — 2026-10-29

- [x] Include the inference environment and processor/device identity in the frozen-report configuration fingerprint before cache lookup.
- [x] Include selected quantization backend versions and effective method settings; use the same recorded settings in the report variants.
- [x] Reject runtime or backend changes before loading a model or running test inference; keep cache reuse for an identical configuration.
- [x] Bump frozen report schema to v11 and document the fingerprint inputs.
- [x] Verify the focused frozen benchmark suite (19 tests); full-suite verification is recorded in the handoff.
- [ ] Re-run matched evaluation after human review and rights clearance; the current source packet remains unreviewed and synthetic results remain workflow-only.

## LoRA runner success-path regression — 2026-10-29

- [x] Exercise the successful training orchestration with mocked model/trainer objects; verify train/validation dataset wiring, local-only loader arguments, adapter persistence, and the schema-v5 validation-only manifest digest without loading checkpoint weights.
- [x] Run the training test module: 29 tests passed.
- [ ] Run and evaluate a new LoRA adapter on a human-reviewed, rights-cleared benchmark; the mock test does not establish model quality.

## Live Fine-tune verification — 2026-10-29

- [x] Verify the current checkout is healthy on port 4004 and the Fine-tune page reports API connected.
- [x] Check the page at 1600px and 390px CSS widths; document and body widths match the viewport, and the mobile navigation collapses to an accessible menu button.
- [x] Confirm the review queue still has 423 candidates / 141 source groups / 0 reviewed labels / 0 eligible groups; no review decision was saved.
- [x] Confirm the browser console has no errors or warnings.
- [ ] Complete a screen-reader and automated axe audit; visual/DOM checks do not replace either.
