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
source permission, grouping policy, annotation guideline version, review counts,
review date, reviewer role, and known limitations. Do not add personal names,
private source URLs, or sensitive text to the card. Both the dataset and filled
card remain ignored by Git; only these two templates are tracked.

Leave `review_status` as `unreviewed` until every benchmark label has been
checked by a human against its source. These files prepare the benchmark
provenance, but the current training flow does not enforce the card yet and no
human-reviewed benchmark has been verified. Do not report a quality result from
the synthetic demo.

`group_id` identifies a source or related example family. Keep paraphrases, chunks, or variants from the same source under one group so they cannot leak across splits. The `output` must contain exactly `organization`, `year`, and `claim`; values are strings or `null`, and `year` is a four-digit integer or `null`.

Do not use model-generated labels as gold data without human review. The demo set is not a benchmark and should not support a résumé performance claim.

The Fine-tune page reports deterministic split counts and a SHA-256 fingerprint
for each valid dataset. Completed adapter manifests keep the fingerprint so a
run can be tied back to the JSONL contents it used.
