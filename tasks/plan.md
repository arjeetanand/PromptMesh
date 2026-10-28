# PromptMesh résumé-evidence plan

## Overview

Build PromptMesh into a reproducible structured-extraction study that can support claims about prompt evaluation, local LoRA/SFT, inference, and quantization. The tracked 48-row demo is synthetic workflow data only. Human-reviewed data and measured results must come from an authorized real dataset and declared hardware; neither may be inferred from the demo.

## Architecture decisions

- Keep the existing `group_id` JSONL contract and deterministic source-group splits.
- Use validation data for prompt, hyperparameter, and adapter selection. Do not expose final-test scores during iterative training or prompt evolution.
- Use deterministic gold-label metrics as primary evidence. Keep the configured LLM judge as an optional heuristic diagnostic.
- Store dataset hash, prompt/version hash, base model and tokenizer revisions, adapter identity, seed, split counts, hardware, and inference settings with every benchmark report.
- Do not install a quantization backend or download additional model weights until a compatible path is selected and authorized.

## Task list

Tasks and checkpoints are tracked in the repository's existing `CHECKLIST.md`.

### Phase 1: Stop test-set feedback during selection

1. **Fine-tuning selection metrics:** score the base and LoRA adapter on validation rows during training; reserve the test rows; label old adapter results as legacy test metrics. Add a regression that proves the training comparison receives validation rows. (Implemented, verified, and committed as `68204e1`.)
2. **Prompt-evolution split:** keep candidate generation and selection on an optimization set, then add a separate, explicit final evaluation path that reports deterministic gold metrics only after prompt selection is frozen. The current UI labels optimization inputs and LLM-judge heuristics; it cannot enforce separation from a future benchmark yet.

### Checkpoint: selection boundary

- [x] LoRA training selection uses validation rows only; the final-test split is not scored during training.
- [x] UI labels distinguish validation metrics from historical exposed test results and reserved final-test counts; prompt evolution identifies its heuristic optimization scores.
- [x] Regression checks cover validation-only LoRA scoring and prompt-evolution score provenance.
- [ ] Prompt evolution and training cannot access examples reserved for the final benchmark, and a separate frozen evaluator exists.

### Phase 2: Human-reviewed benchmark and matched comparison

3. **Benchmark provenance:** accept a user-authorized, human-reviewed dataset; enforce review/provenance metadata without committing private examples. A JSONL row template and an unreviewed card template are now prepared; no reviewed dataset has been supplied.
4. **Frozen benchmark runner:** compare the base model with a selected prompt-only configuration and a selected LoRA adapter on one untouched test split. Record exact data, model, tokenizer, prompt, adapter, seed, metrics, and failure slices; report uncertainty when sample size allows.
5. **Benchmark UI and report:** make validation results usable during iteration and show the final test report as a distinct, frozen result.

### Checkpoint: quality evidence

- [ ] Human review is verified from the dataset card and the user-provided source.
- [ ] Prompt-only and LoRA scores use identical untouched examples.
- [ ] Results are reproducible from saved hashes/revisions and include failure analysis.

### Phase 3: Quantized inference study

6. **Backend decision:** choose an installed, hardware-compatible quantization backend; ask before installing packages or downloading new weights.
7. **Matched inference report:** run unquantized and quantized variants on the same frozen benchmark and hardware; record quality, warm/cold latency, peak memory, precision, and serving settings.
8. **UI disclosure:** show backend/hardware and keep quantization claims absent until the measured comparison completes.

### Checkpoint: efficiency evidence

- [ ] Both variants use the same source checkpoint, prompt, and test inputs.
- [ ] Quantization method and hardware are recorded and inference runs complete locally.
- [ ] Quality, latency, and peak-memory results are visible with limitations.

## Current verified gaps

- `training/runner.py` now computes base and adapter selection metrics on validation rows only. New manifests mark `metrics_split: validation`, `test_split_used: false`, the prompt hash/version, and tokenizer revision. No final-test benchmark runner exists yet.
- `optimization/evolver.py` evaluates and selects prompt candidates on the same supplied `task_inputs` using LLM-judge scores. The UI now calls these optimization inputs and the export records score method, input role, and count; there is no gold-label scoring or enforced final-test boundary for this flow.
- The repository contains only the synthetic demo dataset. The card template remains `unreviewed`; no human-review provenance or user-authorized benchmark corpus is present, and the training flow does not enforce the card yet.
- The live PromptMesh API reports MPS and its server process has loaded the Apple Metal driver, while a fresh CLI probe reports MPS unavailable. Reconcile this before quantization measurements. `mlx`, `mlx_lm`, `llama_cpp`, and `bitsandbytes` are not installed.

## Risks and open questions

| Risk / question | Impact | Mitigation |
|---|---|---|
| No human-reviewed dataset is available in the repository | Cannot substantiate quality claims | Use an authorized redacted dataset supplied by the user; keep it gitignored |
| Prompt evolution still selects revisions on its supplied inputs | Scores can overfit the evolution set | Route candidate selection through validation and keep the final benchmark separate |
| No compatible quantization runtime is installed; the app/CLI MPS reports differ | No valid quantized measurement yet | Reconcile the live runtime and choose a supported backend before requesting installation |
| Hosted judge/model calls may send example text externally and incur cost | Privacy and cost exposure | Keep hosted calls out of benchmark runs unless specifically authorized |
