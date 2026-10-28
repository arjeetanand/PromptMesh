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
- [x] Commit and push the LoRA/SFT implementation and design-token follow-up (`8a4e0db`, `31ba8a0`, `7767a81`) to PR #1; do not merge it.
- [ ] Reconfirm the live PR target is `main` when the GitHub API is reachable.

## Illustration follow-up

- [x] Read the referenced illustration task and inspect PromptMesh's hero and true empty states.
- [x] Generate an original two-pose PromptMesh companion and optimize the transparent images as WebP.
- [x] Add the companion to the overview and empty run-history states with reduced-motion-aware animation.
- [x] Verify image loading, desktop/mobile rendering, and the history empty state in the browser.
- [x] Commit this follow-up locally on `codex/promptmesh-illustrations`; do not push or merge without approval.

## Section illustration follow-up

- [x] Add a compact companion vignette to every non-overview workspace page, with a motif specific to that page.
- [x] Verify all six sections at desktop and 390px mobile widths with no horizontal overflow.
- [x] Include the section illustrations in the current task branch for the existing PR targeting `main`.

## Evaluation reliability follow-up

- [x] Create a dedicated branch from the current clean PromptMesh tree.
- [x] Fix classification and verification scoring weights and prevent judge outages from returning a score.
- [x] Propagate judge failures through the scorer, app jobs, CLI, and diagnostic script.
- [x] Add regression tests and clarify the LLM-judge scope in the UI and README.
- [x] Run the complete suite (29 passed), Python compilation, JavaScript syntax check, and diff check.
- [x] Verify the Evaluate label, API connection, mobile layout at 390px, and browser console.
- [ ] Commit and update PR #1 targeting `main`; do not merge.

## Next résumé milestones

- [ ] Create a human-reviewed, versioned gold benchmark with grouped train/validation/test splits; keep prompt evolution and model selection on validation data only.
- [ ] Compare base, prompt-only, and LoRA results on the same untouched test examples; report task metrics and uncertainty.
- [ ] Measure quantized versus unquantized inference quality, latency, and memory on a declared backend and hardware.
- [ ] Publish a reproducible run manifest and demo that distinguish synthetic workflow checks from model-quality evidence.
