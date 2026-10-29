# PromptMesh résumé-evidence plan

## Overview

Build PromptMesh into a reproducible structured-extraction study that can support claims about prompt evaluation, local LoRA/SFT, inference, and quantization. The tracked 48-row demo is synthetic workflow data only. Human-reviewed data and measured results must come from an authorized real dataset and declared hardware; neither may be inferred from the demo.

## Architecture decisions

- Keep the existing `group_id` JSONL contract and deterministic source-group splits.
- Use validation data for prompt and adapter selection. Keep the reserved test split out of training and prompt selection; reserve it before inference and do not retry after a possible test access.
- Use deterministic gold-label metrics as primary evidence. Keep the configured LLM judge as an optional heuristic diagnostic.
- Store dataset hash, prompt/version hash, base model and tokenizer revisions, adapter identity, seed, split counts, hardware, and inference settings with every benchmark report.
- Install only a hardware-compatible quantization backend after the path is selected and authorized. bitsandbytes 0.50.0 is installed in the project `.venv` with prior approval; do not download additional model weights without approval.

## Task list

Tasks and checkpoints are tracked in the repository's existing `CHECKLIST.md`.

### Phase 1: Stop test-set feedback during selection

1. **Fine-tuning selection metrics:** score the base and LoRA adapter on validation rows during training; reserve the test rows; label old adapter results as legacy test metrics. Add a regression that proves the training comparison receives validation rows. (Implemented, verified, and committed as `68204e1`.)
2. **Prompt-selection boundary:** keep the existing LLM-judge evolution workflow as a heuristic optimization tool. Candidate prompts can be copied into the Fine-tune validation selector, which compares them with `extraction/v1` using gold validation metrics before final evaluation.

### Checkpoint: selection boundary

- [x] LoRA training selection uses validation rows only; the final-test split is not scored during training.
- [x] UI labels distinguish validation metrics from historical exposed test results and reserved final-test counts; prompt evolution identifies its heuristic optimization scores.
- [x] Regression checks cover validation-only LoRA scoring and prompt-evolution score provenance.
- [x] Local LoRA training scores validation only; prompt selection scores validation only; the frozen evaluator uses the test split only after selection.
- [x] A frozen report cannot be rerun with a different prompt selection or adapter for the same dataset fingerprint; source-group and input identities cannot be reused across dataset versions.

### Phase 2: Human-reviewed benchmark and matched comparison

3. **Benchmark provenance:** validate the user-authored card against exact dataset bytes and require a local review attestation and complete counts before selection/evaluation. Both validation and test splits need the minimum size. Templates are ready; no reviewed dataset has been supplied, and the card cannot independently prove the review occurred.
4. **Validation prompt selector:** compare `extraction/v1` plus up to three candidate prompts on grouped validation rows using exact match, field accuracy, and JSON-valid rate. Save a hash-checked selection record with adapter/data/card/model provenance.
5. **Frozen benchmark runner:** reserve the test source-group and input identities before scoring; compare base+initial prompt, base+validation-selected prompt, and LoRA+the same selected prompt on the identical untouched test rows. Save aggregate metrics, source-group bootstrap intervals, split/model/tokenizer/prompt/adapter/data/card hashes, device and inference settings. Use only cached pinned weights. A failed or completed holdout cannot be reused by changing only its dataset ID or training rows; the next final run needs disjoint source groups and inputs.
6. **Benchmark UI and report:** add validation-selection and final-report controls to Fine-tune; show the test report as a separate frozen result.

### Checkpoint: quality evidence

- [ ] A user supplies an authorized, representative corpus and performs human label review; the local card remains a self-attestation.
- [x] Prompt-only and LoRA report arms use identical untouched examples after validation-based selection.
- [x] Reports carry data/card/model/tokenizer/prompt/adapter hashes and revisions, exact split counts, hardware, decoding settings, and grouped uncertainty intervals.
- [x] Add aggregate per-arm failure counts for invalid JSON/schema and field mismatches, overall and by gold year; retain no source text or generated answers in the report.
- [ ] Inspect real model outputs and failure patterns on the supplied, human-reviewed corpus.

### Phase 3: Quantized inference study

7. **Backend decision:** bitsandbytes 0.50.0 is installed in the project `.venv`; the host-context runtime reports MPS, and the synthetic INT8/NF4 workflow smoke is complete. Quanto remains uninstalled. Ask before installing further packages or downloading new weights.
8. **Matched inference report:** run unquantized and quantized variants on the same frozen benchmark and hardware; record quality, warm/cold latency, peak memory, precision, and serving settings. The runner now fingerprints cold/warm latency and memory protocols; CUDA reports allocator peaks and MPS reports non-peak driver snapshots. A human-reviewed run and backend-appropriate memory results are still pending.
9. **UI disclosure:** show backend/hardware and keep quantization claims absent until the measured comparison completes.

### Checkpoint: efficiency evidence

- [ ] Both variants use the same source checkpoint, prompt, and test inputs.
- [ ] Quantization method and hardware are recorded and inference runs complete locally.
- [ ] Quality, latency, and peak-memory results are visible with limitations.

## Current verified gaps

- `training/runner.py` trains LoRA on train rows and scores the base/adapter on validation only; schema-v5 manifests record validation provenance plus effective SFT, LoRA, precision, and model-loading settings. A one-epoch synthetic MPS smoke saved a schema-v5 adapter with a valid configuration digest and rendered the live settings disclosure; its 6 validation examples are workflow evidence only, and the final test remained reserved. Schema-v4 adapters remain available for inference but are not eligible for new frozen reports. Prompt selection and the frozen matched benchmark are implemented in `training/benchmark.py` and exposed in the Fine-tune UI. Frozen report schema v11 embeds and fingerprints adapter training configuration, inference environment, processor/device identity, selected quantization backend versions, and effective method settings alongside aggregate failure counts.
- `optimization/evolver.py` still scores revisions on user-supplied optimization inputs with an LLM judge. It is not directly wired to the gold validation selector; users paste a candidate into the Fine-tune flow to score it.
- The repository contains only the synthetic demo dataset. The tracked card template remains `unreviewed`; no user-authorized human-reviewed corpus or real model benchmark exists. The card is checked as a self-attestation and is not an independent review audit.
- The private review workbench's 12-per-year pilot now maximizes normalized HTTPS host diversity within each reviewed year, and schema-v3 cards record candidate IDs, years, hosts, URLs, and selected IDs. Schema-v2 year-only cards remain loadable. A draft-only projection can select 12 hosts per year, but no labels or reuse decisions are reviewed and this is not a representativeness claim.
- Training, saved-adapter inference, and final evaluation use `local_files_only=True`; training and benchmark evaluation also pin the cached Qwen revision. These paths do not fetch model weights.
- The host-context `.venv` probe and live API both report MPS; the default command sandbox reports MPS unavailable because it lacks host device access. bitsandbytes 0.50.0 is available and was exercised with synthetic smoke inputs; Quanto is not installed. No real-data quantized comparison exists.
- Run manifests now capture the effective trainer and LoRA settings and the Fine-tune UI surfaces them. A disposable Python 3.12/macOS ARM64 environment installed the app requirements and 47-pin training lock; all pins matched, `pip check` passed, required imports succeeded, and 108 Python tests pass. General app requirements remain unpinned.

## Risks and open questions

| Risk / question | Impact | Mitigation |
|---|---|---|
| No human-reviewed dataset is available in the repository | Cannot substantiate quality claims | Use an authorized redacted dataset supplied by the user; keep it gitignored |
| Prompt evolution still selects revisions on its supplied inputs | Judge scores can overfit the optimization set | Treat evolution as heuristic generation; use the gold validation selector before any final report |
| No human-reviewed, rights-cleared benchmark is available | Cannot support real-data quality or quantization claims | Wait for human source/label/reuse review; keep synthetic smoke results labeled as workflow evidence |
| Quanto is not installed | No W8A8 calibration comparison is available | Install only after selecting this backend and receiving authorization; INT8/NF4 bitsandbytes remain available |
| Hosted judge/model calls may send example text externally and incur cost | Privacy and cost exposure | Keep hosted calls out of benchmark runs unless specifically authorized |
