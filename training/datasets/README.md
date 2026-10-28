# Local fine-tuning datasets

The tracked `entity_extraction_demo.jsonl` file is synthetic and is only a small end-to-end demo. It contains 48 paraphrases of 16 facts; each fact shares a `group_id`, so variants from one fact stay together when PromptMesh creates train, validation, and test splits.

Add private datasets as additional `.jsonl` files in this directory. They are ignored by Git. Use one JSON object per line with exactly these fields:

```json
{"group_id":"source-document-001","input":"Source text to extract from.","output":{"organization":"Example Co","year":2024,"claim":"opened a clinic in Pune"}}
```

## Prepare a reviewed benchmark

Use `entity_extraction_template.jsonl.example` as a row-format guide. Copy it to
`<dataset_id>.jsonl`, remove the comment, and replace every placeholder with an
authorized source example and its human-checked labels. Keep related passages
and paraphrases under the same `group_id`.

Copy `benchmark_card.template.json` to `<dataset_id>.card.json` and fill in the
dataset ID and SHA-256 shown in dataset readiness, source permission, grouping
policy, annotation guideline version, review counts, review date, reviewer role,
and known limitations. A changed JSONL file has a new fingerprint, so update the
card only after reviewing the changed examples again. Do not add personal names,
private source URLs, or sensitive text to the card. Both the dataset and filled
card remain ignored by Git; only these two templates are tracked.

Leave `review_status` as `unreviewed` until every benchmark label has been
checked by a human against its source. These files prepare the benchmark
provenance. Prompt selection and final benchmark evaluation require a matching
card marked reviewer-attested. This is a local self-attestation; PromptMesh
cannot independently verify that a reviewer checked the labels. Ordinary
training remains available for experimentation. No human-reviewed benchmark
has been supplied. Do not report a quality result from the synthetic demo.

Both the validation and frozen test splits must contain at least 30 examples
across 10 source groups.
Prompt selection compares the built-in `extraction/v1` template with your
candidate using validation labels only. After selection, the frozen runner
compares the prompted base and the matching LoRA adapter on the same reserved
test rows once per dataset fingerprint. A reservation is written before test
inference; if an error occurs after that point, treat the holdout as consumed
and make a new dataset version before another final run. It requires the matching adapter to
have validation-only metrics and a valid artifact hash. The benchmark runner
uses the pinned model revision from the local cache and will not download model
weights. It writes aggregate results and a group-bootstrap interval under
`training/benchmarks/`; it does not save example text or model outputs there.

`group_id` identifies a source or related example family. Keep paraphrases, chunks, or variants from the same source under one group so they cannot leak across splits. The `output` must contain exactly `organization`, `year`, and `claim`; values are strings or `null`, and `year` is a four-digit integer or `null`.

Do not use model-generated labels as gold data without human review. The demo set is not a benchmark and should not support a résumé performance claim.

The Fine-tune page reports deterministic split counts and a SHA-256 fingerprint
for each valid dataset. Completed adapter manifests keep the fingerprint so a
run can be tied back to the JSONL contents it used.
