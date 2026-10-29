# Entity extraction annotation guide v1

- **Guideline ID:** `entity-extraction-v1`
- **Task prompt:** `extraction/v1` (definition `1.1.0`)
- **Output fields:** `organization`, `year`, `claim`

Use this protocol to create or review gold labels. Examples below are fictional
and illustrate decisions only; do not copy them into a benchmark.

## Unit of annotation

Each row should contain one source passage about one primary event. If a source
contains several distinct events, split it into separate rows and keep those
rows under the same `group_id`. If the passage has multiple equally plausible
organizations or events and no single target can be identified from the text,
exclude it instead of guessing. Keep enough surrounding text to resolve the
reference without relying on outside knowledge.

## Field rules

- **`organization`**: Use the named organization that performs the focal action
  in the claim (the actor/subject). Do not substitute a recipient or beneficiary
  just because it is also named. Preserve the name form used in the passage; do
  not expand an abbreviation, resolve an alias, infer a parent company, or
  choose a better-known entity from external knowledge. If the actor is not
  stated, use JSON `null`. Exclude passages with multiple equally central actors
  unless the task explicitly defines how to represent them.
- **`year`**: Use the four-digit year explicitly tied to the event, as an integer.
  Do not substitute the article's publication year, the current year, a decade,
  or a year inferred from relative wording such as “last year.” Use `null` if no
  event year is stated. If the passage ties different years to different events,
  split the events or exclude the ambiguous passage.
- **`claim`**: Write one concise, atomic description of what happened or is
  stated. Preserve the action, object, location, negation, and uncertainty or
  future modality when they affect meaning. Do not add causes, outcomes, or
  context absent from the passage. Use `null` only when no claim is stated.
- Use JSON `null`, not the strings `"null"`, `"unknown"`, or an empty string.
  Ambiguity is a reason to exclude or adjudicate a row, not a reason to guess.

The scorer compares text fields after case-folding, collapsing whitespace, and
removing trailing `. , ; :`. It does not treat aliases, synonyms, or
semantically equivalent claims as equal. Keep one canonical label style across
all rows, and resolve disagreements against the source before freezing the
dataset.

## Synthetic decision examples

These examples are guidance only and are not benchmark data.

Input: “A fictional report published in 2025 says Alder Transit opened a depot
in Kochi in 2024.”

```json
{"organization":"Alder Transit","year":2024,"claim":"opened a depot in Kochi"}
```

The event year is 2024; 2025 is only the publication year.

Input: “Fictional Transit Authority awarded a grant to Cedar Mobility in 2024 to open a
transit route.”

```json
{"organization":"Fictional Transit Authority","year":2024,"claim":"awarded a grant to Cedar Mobility to open a transit route"}
```

The agency is the actor that awarded the grant; Cedar Mobility is the recipient.

Input: “A fictional notice says Alder Transit may open a depot in Kochi next
year.”

```json
{"organization":"Alder Transit","year":null,"claim":"may open a depot in Kochi"}
```

Without a reference date, “next year” is not a four-digit event year. Preserve
“may” so a proposed action is not mislabeled as a completed event.

## Source grouping and leakage control

Assign one stable `group_id` per original source or fact family. Every excerpt,
chunk, paraphrase, or translation derived from that source must share the same
group. Do not create a new group merely to move a related example into another
split. PromptMesh assigns whole groups to train, validation, or final test.

## Review and freeze procedure

1. Confirm the source may be used for this purpose and retain its source
   reference and permission record in the authorized local project records.
2. Check every row against its source, including null fields, names, event
   years, and the wording of claims. Do not treat model-generated labels as gold
   until a human has checked and corrected them.
3. Resolve ambiguous labels before marking the dataset reviewed. A second
   reviewer or an adjudication pass on validation and test rows is recommended
   when available; record that process separately because the benchmark card
   stores only aggregate review counts.
4. After any row or label changes, recompute the dataset fingerprint and review
   the changed dataset again before updating its card.
5. Keep the final test set out of prompt selection, training decisions,
   calibration, and repeated experimentation. The frozen benchmark reserves it
   before inference; an interrupted run may consume that dataset version's
   holdout.

The benchmark card is a local self-attestation tied to the dataset SHA-256. It
does not prove reviewer identity, source permissions, or label correctness.
Keep source text, filled cards, and review notes private unless their licenses
and sharing permissions allow publication. Do not claim model quality from the
synthetic demo or from a reviewed card without a completed frozen evaluation.
