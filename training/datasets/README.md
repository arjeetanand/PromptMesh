# Local fine-tuning datasets

The tracked `entity_extraction_demo.jsonl` file is synthetic and is only a small end-to-end demo. It contains 48 paraphrases of 16 facts; each fact shares a `group_id`, so variants from one fact stay together when PromptMesh creates train, validation, and test splits.

Add private datasets as additional `.jsonl` files in this directory. They are ignored by Git. Use one JSON object per line with exactly these fields:

```json
{"group_id":"source-document-001","input":"Source text to extract from.","output":{"organization":"Example Co","year":2024,"claim":"opened a clinic in Pune"}}
```

## Prepare a reviewed benchmark

Use [ANNOTATION_GUIDE_v1.md](ANNOTATION_GUIDE_v1.md) as the versioned labeling
protocol and `entity_extraction_template.jsonl.example` as a row-format guide.
Copy the row example to `<dataset_id>.jsonl`, remove the comment, and replace
every placeholder with an authorized source example and labels checked against
that source by a human. Keep related passages and paraphrases under the same
`group_id`. The guide's examples are synthetic and must not be copied into a
benchmark.

Copy `benchmark_card.template.json` to `<dataset_id>.card.json` and fill in the
dataset ID and SHA-256 shown in dataset readiness, source permission, grouping
policy, annotation guideline version, review counts, review date, reviewer role,
and known limitations. A changed JSONL file has a new fingerprint, so update the
card only after reviewing the changed examples again. Do not add personal names,
private source URLs, or sensitive text to the card. The dataset and filled card
remain ignored by Git; the row/card templates and annotation guide are tracked.

Leave `review_status` as `unreviewed` until every benchmark label has been
checked by a human against its source. Set `guidelines_version` to
`entity-extraction-v1` when following the included guide. These files prepare
the benchmark provenance. Prompt selection and final benchmark evaluation
require a matching card marked `human_reviewed`; the gate validates the card
and dataset fingerprint, but review is still a local self-attestation. PromptMesh
cannot independently verify that a reviewer checked the labels. Ordinary
training remains available for experimentation. No human-reviewed benchmark
has been supplied. Do not report a quality result from the synthetic demo.

The current `extraction/v1` prompt definition (`1.1.0`) and the guide both use
the named actor/subject for `organization`; recipients and beneficiaries are
not the target label.

For datasets with at least 30 source groups, PromptMesh stratifies whole groups
by event-year signature. A signature with at least three groups contributes
one group to validation and one to test; additional held-out groups are
allocated toward 15% in each split. Sparse signatures stay in training.
Datasets with fewer than 30 groups keep the deterministic group-hash split.
Both strategies use seed 42 and are recorded with training, prompt-selection,
and final-benchmark results. This improves year coverage but does not balance
organizations, topics, source types, or writing styles.

Both the validation and frozen test splits must contain at least 30 examples
across 10 source groups.
For the current seed-42 split, one workable planning shape is 67 source groups
with three distinct, label-consistent examples per group; that yields 30
examples across 10 groups in each held-out split. Check the app's readiness
report after annotation because counts depend on group membership.
The local public-source review packet has 381 draft rows across 127 groups.
Its current split policy yields 267 training rows and 57 rows across 19 groups
in each held-out split. Each group has three controlled phrasings of one source
claim; these are not independent facts. Proposed years are still imbalanced:
66 groups are from 2024, 12 each from 2020, 2021, 2022, 2023, and 2025, and one
is undated. The packet remains review-only and is not representative. Review
each source, label, split, and reuse condition before using any examples.

After curation, one year-balanced pilot target would use 12 source groups from
each year 2020–2025, selecting 12 of the 66 proposed 2024 groups. With three
variants per group and seed 42, that 72-group target projects to 50/11/11
train/validation/test groups (150/33/33 rows). This is only a planning
projection over unreviewed labels, not a benchmark result or representativeness
claim.

The current seed-42 split projection from those **unreviewed proposed years**
is:

| Split | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | Undated |
|---|---:|---:|---:|---:|---:|---:|---:|
| Train groups | 8 | 9 | 9 | 8 | 46 | 8 | 1 |
| Validation groups | 2 | 2 | 1 | 2 | 10 | 2 | 0 |
| Test groups | 2 | 1 | 2 | 2 | 10 | 2 | 0 |

This preview is structural only, not the eventual reviewed benchmark composition.
Both held-out sets are dominated by 2024, and some year slices contain only one
source group. Curate a more balanced cohort before making broad quality claims.
Use **Fine-tune → Review source candidates** to review the local CSV by source
group. Check each wording against its linked source, edit labels, and record
reuse permission separately with evidence. The queue saves only to the ignored
CSV and is loopback-only. After enough groups are fully resolved and have
confirmed reuse evidence, **Build a reviewed dataset** exports only reviewed
variants to an ignored JSONL and creates a matching benchmark card with source
references. Excluded variants and unresolved groups stay out. Export requires
at least 30 examples across 10 source groups in both validation and final test;
it does not train a model or score the test set. Review and reuse decisions in
the card are local self-attestations, not independent proof of label quality
or reuse rights.
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
