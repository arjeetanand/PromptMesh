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

- [ ] Create a human-reviewed, versioned gold benchmark with grouped train/validation/test splits; keep prompt evolution and model selection on validation data only.
- [ ] Compare base, prompt-only, and LoRA results on the same untouched test examples; report task metrics and uncertainty.
- [ ] Measure quantized versus unquantized inference quality, latency, and memory on a declared backend and hardware.
- [ ] Publish a reproducible run manifest and demo that distinguish synthetic workflow checks from model-quality evidence.

## Gold benchmark workflow

- [x] Validate the reviewer card against the exact JSONL fingerprint, review/count metadata, and source-group split; keep synthetic data ineligible.
- [x] Mark readiness as a self-attested review card, not independently verified human review; require at least 30 validation and test examples across 10 source groups each.
- [x] Compare extraction/v1 and a candidate prompt on gold validation data only, and save a hash-checked selection record tied to a validation-only schema-v3 LoRA adapter.
- [x] Reserve the frozen test set before inference, then compare base+initial prompt, base+selected prompt, and LoRA+selected prompt on identical test rows; include aggregate metrics and source-group bootstrap intervals.
- [x] Store selection/report artifacts locally with private permissions and keep them out of Git.
- [x] Add Fine-tune UI controls and background-job progress/result states for prompt selection and final benchmarking.
- [x] Review Fine-tune at desktop in Edge and inspect 1440px, 768px, and 390px layouts; synthetic data is blocked and the inspector reports no horizontal overflow. No physical phone test was performed.
- [x] Rerun the full Python suite (51 passed), UI job checks (8 passed), syntax checks, and whitespace validation.
- [x] Open PR #2 targeting `main` after verifying PR #1 was already merged; leave PR #2 unmerged.
- [x] Add optional bitsandbytes LLM.int8 and NF4 runtime configuration and Fine-tune controls for a quantized inference comparison.
- [x] Run a fixed synthetic backend canary before reserving test data; record matched test metrics, grouped intervals, load/inference time, generated-token rate, and model footprint.
- [x] Explain that bitsandbytes methods do not use an offline calibration corpus; keep AWQ/GPTQ calibration and QLoRA training explicitly separate.
- [x] Define `organization` as the claim actor in extraction prompt definition 1.1.0 and the annotation guide.
- [x] Prepare a private 19-row public-source candidate review packet with source URLs, draft labels, rights status, and reviewer fields; keep it outside the loadable dataset directory.
- [x] Add regression coverage for INT8/NF4 configuration, identical test rows, calibration labeling, and invalid or unavailable API selections.
- [x] Assert that the loaded extraction prompt definition 1.1.0 keeps the actor/recipient rule.
- [x] Check Fine-tune at 1440px and 390px in Edge; the document has no horizontal overflow or browser console errors.
- [ ] Restart the current host server with the new API and verify the adapter-attached NF4/INT8 canary on MPS; this sandbox could not expose its 6004 server to the browser.
- [ ] Supply and human-review an authorized real dataset, train a new schema-v3 adapter, and run a real frozen benchmark; no model-quality result exists yet.
- [ ] Run the quantized comparison on that reviewed corpus; no real quality result or calibration experiment has been produced.
## Navigation and background-job follow-up

- [x] Add a Back to overview control to every non-overview page.
- [x] Allow local LoRA training and prompt evolution progress dialogs to close while polling continues in the open tab.
- [x] Show running, paused, completed, and failed status in the top bar; link completion to its results without changing the current page.
- [x] Add four Node regression checks for LoRA/evolution progress dismissal, reopening, completion status, and results navigation.
- [x] Verify tab navigation and responsive header behavior in the browser.
- [x] Include the navigation and background-job follow-up in PR #1 targeting `main`.
