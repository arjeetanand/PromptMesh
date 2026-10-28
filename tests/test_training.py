import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from models.cohere_model import CohereModel
from training.datasets import (
    benchmark_card_status,
    dataset_path,
    dataset_sha256,
    list_datasets,
    load_benchmark_card,
    load_dataset,
    load_dataset_snapshot,
    split_counts,
    split_dataset,
)
from training.metrics import score_predictions
from training.registry import artifact_tree_sha256, get_adapter_path, get_benchmark_adapter, list_adapters


class TrainingDatasetTests(unittest.TestCase):
    def _write_reviewed_dataset(self, directory, count=12):
        rows = [
            {"group_id": f"source-{index}", "input": f"Source fact {index}.",
             "output": {"organization": f"Org {index}", "year": 2024, "claim": f"claim {index}"}}
            for index in range(count)
        ]
        dataset_path = Path(directory) / "reviewed.jsonl"
        dataset_bytes = "".join(json.dumps(row) + "\n" for row in rows).encode("utf-8")
        dataset_path.write_bytes(dataset_bytes)
        card = {
            "schema_version": 1,
            "dataset_id": "reviewed",
            "dataset_sha256": hashlib.sha256(dataset_bytes).hexdigest(),
            "task": "entity_extraction",
            "source": {"description": "Public reports", "authorization_or_license": "CC BY 4.0"},
            "grouping": {"unit": "source document", "policy": "One source per group"},
            "annotation": {
                "guidelines_version": "v1",
                "review_status": "human_reviewed",
                "all_labels_human_reviewed": True,
                "total_examples": len(rows),
                "reviewed_examples": len(rows),
                "total_source_groups": len(rows),
                "reviewed_source_groups": len(rows),
                "reviewed_at_utc": "2026-10-28T12:00:00Z",
                "reviewer_role": "domain reviewer",
            },
            "limitations": ["Small coverage of organization types"],
        }
        (Path(directory) / "reviewed.card.json").write_text(json.dumps(card), encoding="utf-8")
        return rows

    def test_dataset_ids_cannot_escape_the_local_dataset_directory(self):
        with self.assertRaises(ValueError):
            dataset_path("../outside")

    def test_dataset_snapshot_hashes_the_exact_bytes_that_were_parsed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self._write_reviewed_dataset(temp_dir)
            with patch("training.datasets.DATASET_DIR", Path(temp_dir)):
                rows, digest = load_dataset_snapshot("reviewed")
                self.assertEqual(rows, load_dataset("reviewed"))
                self.assertEqual(digest, dataset_sha256("reviewed"))

    def test_human_review_card_must_match_dataset_examples_and_source_groups(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            rows = self._write_reviewed_dataset(temp_dir)
            with patch("training.datasets.DATASET_DIR", Path(temp_dir)):
                card = load_benchmark_card("reviewed", rows)
                status = benchmark_card_status("reviewed", rows)

        self.assertEqual(card["annotation"]["review_status"], "human_reviewed")
        self.assertTrue(status["card_ready"])
        self.assertFalse(status["final_test_ready"])
        self.assertEqual(status["reviewed_examples"], len(rows))
        self.assertEqual(status["reviewed_source_groups"], len(rows))
        self.assertEqual(len(status["card_sha256"]), 64)

    def test_final_test_readiness_requires_minimum_examples_and_source_groups(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            rows = self._write_reviewed_dataset(temp_dir, count=200)
            with patch("training.datasets.DATASET_DIR", Path(temp_dir)):
                status = benchmark_card_status("reviewed", rows)

        self.assertTrue(status["card_ready"])
        self.assertTrue(status["validation_ready"])
        self.assertTrue(status["final_test_ready"])
        self.assertGreaterEqual(status["final_test_examples"], status["minimum_final_test_examples"])
        self.assertGreaterEqual(status["final_test_source_groups"], status["minimum_final_test_groups"])

    def test_missing_dataset_is_not_reported_as_a_missing_card(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("training.datasets.DATASET_DIR", Path(temp_dir)):
                status = benchmark_card_status("missing")

        self.assertEqual(status["status"], "missing_dataset")

    def test_benchmark_card_rejects_unreviewed_or_incomplete_labels(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            rows = self._write_reviewed_dataset(temp_dir)
            card_path = Path(temp_dir) / "reviewed.card.json"
            card = json.loads(card_path.read_text(encoding="utf-8"))
            card["annotation"]["review_status"] = "unreviewed"
            card["annotation"]["reviewed_examples"] -= 1
            card_path.write_text(json.dumps(card), encoding="utf-8")
            with patch("training.datasets.DATASET_DIR", Path(temp_dir)):
                status = benchmark_card_status("reviewed", rows)
                with self.assertRaisesRegex(ValueError, "human-reviewed"):
                    load_benchmark_card("reviewed", rows)

        self.assertFalse(status["card_ready"])
        self.assertEqual(status["status"], "invalid_card")

    def test_benchmark_card_rejects_a_stale_dataset_fingerprint(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            rows = self._write_reviewed_dataset(temp_dir)
            with (Path(temp_dir) / "reviewed.jsonl").open("ab") as dataset_file:
                dataset_file.write(b"\n")
            with patch("training.datasets.DATASET_DIR", Path(temp_dir)):
                status = benchmark_card_status("reviewed", rows)

        self.assertFalse(status["card_ready"])
        self.assertEqual(status["status"], "invalid_card")
        self.assertIn("does not match", status["reason"])

    def test_benchmark_card_path_rejects_a_symlink_outside_dataset_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir, tempfile.TemporaryDirectory() as outside_dir:
            rows = self._write_reviewed_dataset(temp_dir)
            outside = Path(outside_dir) / "outside.json"
            outside.write_text("{}", encoding="utf-8")
            (Path(temp_dir) / "reviewed.card.json").unlink()
            (Path(temp_dir) / "reviewed.card.json").symlink_to(outside)
            with patch("training.datasets.DATASET_DIR", Path(temp_dir)):
                with self.assertRaisesRegex(ValueError, "card path"):
                    load_benchmark_card("reviewed", rows)

    def test_synthetic_demo_is_never_marked_final_benchmark_ready(self):
        dataset = next(item for item in list_datasets() if item["id"] == "entity_extraction_demo")

        self.assertFalse(dataset["benchmark"]["card_ready"])
        self.assertEqual(dataset["benchmark"]["status"], "synthetic_only")

    def test_dataset_listing_exposes_its_content_fingerprint(self):
        dataset = next(item for item in list_datasets() if item["id"] == "entity_extraction_demo")

        self.assertEqual(dataset["sha256"], dataset_sha256("entity_extraction_demo"))
        self.assertEqual(len(dataset["sha256"]), 64)

    def test_demo_split_is_repeatable_and_keeps_related_examples_together(self):
        rows = load_dataset("entity_extraction_demo")
        splits = split_dataset(rows)
        groups = {name: {row["group_id"] for row in split} for name, split in splits.items()}

        self.assertEqual(split_counts(splits), split_counts(split_dataset(rows)))
        self.assertEqual(sum(split_counts(splits).values()), len(rows))
        self.assertFalse(groups["train"] & groups["validation"])
        self.assertFalse(groups["train"] & groups["test"])
        self.assertFalse(groups["validation"] & groups["test"])

    def test_held_out_metrics_count_invalid_json_as_incorrect(self):
        rows = [
            {"output": {"organization": "Northstar", "year": 2024, "claim": "opened a lab"}},
            {"output": {"organization": None, "year": None, "claim": None}},
        ]
        scores = score_predictions(rows, ['{"organization":"northstar","year":2024,"claim":"opened a lab."}', "not json"])

        self.assertEqual(scores["json_valid_rate"], 0.5)
        self.assertEqual(scores["record_exact_match"], 0.5)
        self.assertEqual(scores["field_accuracy"], 0.5)


class AdapterRegistryTests(unittest.TestCase):
    def test_only_completed_adapter_runs_are_loadable(self):
        run_id = "a" * 32
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir) / run_id
            adapter_dir = run_dir / "adapter"
            adapter_dir.mkdir(parents=True)
            (adapter_dir / "adapter_config.json").write_text("{}", encoding="utf-8")
            (run_dir / "manifest.json").write_text(json.dumps({"status": "completed", "run_id": run_id}), encoding="utf-8")
            with patch("training.registry.RUNS_DIR", Path(temp_dir)):
                adapter_path, manifest = get_adapter_path(run_id)
                self.assertEqual(adapter_path, adapter_dir.resolve())
                self.assertEqual(manifest["status"], "completed")
                with self.assertRaises(ValueError):
                    get_adapter_path("../outside")

    def test_frozen_benchmark_requires_matching_validation_adapter_and_artifact_hash(self):
        run_id = "d" * 32
        dataset_digest = "e" * 64
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir) / run_id
            adapter_dir = run_dir / "adapter"
            adapter_dir.mkdir(parents=True)
            config_path = adapter_dir / "adapter_config.json"
            config_path.write_text("{}", encoding="utf-8")
            manifest = {
                "schema_version": 3,
                "status": "completed",
                "run_id": run_id,
                "base_model": "Qwen/Qwen3-0.6B",
                "base_revision": "base-revision",
                "tokenizer_revision": "base-revision",
                "dataset_id": "reviewed",
                "dataset_sha256": dataset_digest,
                "adapter_sha256": artifact_tree_sha256(adapter_dir),
                "metrics_split": "validation",
                "test_split_used": False,
            }
            (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            with patch("training.registry.RUNS_DIR", Path(temp_dir)):
                self.assertEqual(
                    get_benchmark_adapter(run_id, "reviewed", dataset_digest)[1]["adapter_sha256"],
                    manifest["adapter_sha256"],
                )
                config_path.write_text("changed", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "artifact fingerprint"):
                    get_benchmark_adapter(run_id, "reviewed", dataset_digest)

    def test_frozen_benchmark_rejects_legacy_adapter_manifests(self):
        run_id = "f" * 32
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir) / run_id
            adapter_dir = run_dir / "adapter"
            adapter_dir.mkdir(parents=True)
            (adapter_dir / "adapter_config.json").write_text("{}", encoding="utf-8")
            (run_dir / "manifest.json").write_text(json.dumps({
                "status": "completed",
                "run_id": run_id,
                "metrics_split": "legacy_test",
            }), encoding="utf-8")
            with patch("training.registry.RUNS_DIR", Path(temp_dir)):
                with self.assertRaisesRegex(ValueError, "lacks the frozen-benchmark provenance"):
                    get_benchmark_adapter(run_id, "reviewed", "a" * 64)

    def test_adapters_without_a_metrics_split_are_marked_as_legacy_test_results(self):
        run_id = "b" * 32
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir) / run_id
            adapter_dir = run_dir / "adapter"
            adapter_dir.mkdir(parents=True)
            (adapter_dir / "adapter_config.json").write_text("{}", encoding="utf-8")
            (run_dir / "manifest.json").write_text(json.dumps({
                "status": "completed",
                "run_id": run_id,
                "base_model": "local-base",
                "dataset_id": "demo",
                "dataset_sha256": "a" * 64,
                "created_at": "2026-10-28T00:00:00+00:00",
                "metrics": {"adapter": {"record_exact_match": 0.0}},
            }), encoding="utf-8")

            with patch("training.registry.RUNS_DIR", Path(temp_dir)):
                adapters = list_adapters()

        self.assertEqual(adapters[0]["metrics_split"], "legacy_test")

    def test_new_adapter_manifest_keeps_validation_metric_label(self):
        run_id = "c" * 32
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir) / run_id
            adapter_dir = run_dir / "adapter"
            adapter_dir.mkdir(parents=True)
            (adapter_dir / "adapter_config.json").write_text("{}", encoding="utf-8")
            (run_dir / "manifest.json").write_text(json.dumps({
                "status": "completed",
                "run_id": run_id,
                "base_model": "local-base",
                "dataset_id": "demo",
                "dataset_sha256": "b" * 64,
                "created_at": "2026-10-28T00:00:00+00:00",
                "metrics_split": "validation",
                "metrics": {"adapter": {"record_exact_match": 0.5}},
            }), encoding="utf-8")

            with patch("training.registry.RUNS_DIR", Path(temp_dir)):
                adapters = list_adapters()

        self.assertEqual(adapters[0]["metrics_split"], "validation")

    def test_cohere_credentials_are_not_required_to_create_a_local_model(self):
        with patch("models.cohere_model.cohere.Client") as client:
            CohereModel("command-r")
        client.assert_not_called()


class TrainingRunnerTests(unittest.TestCase):
    def test_selection_metrics_use_validation_rows_not_final_test_rows(self):
        from training.runner import _score_validation

        validation_rows = [{"input": "validation", "output": {}}]
        test_rows = [{"input": "final test", "output": {}}]
        splits = {"validation": validation_rows, "test": test_rows}
        with (
            patch("training.runner._generate", return_value=["prediction"]) as generate,
            patch("training.runner.score_predictions", return_value={"record_exact_match": 1.0}) as score,
        ):
            result = _score_validation("model", "tokenizer", "prompt", splits)

        self.assertEqual(result, {"record_exact_match": 1.0})
        generate.assert_called_once_with("model", "tokenizer", "prompt", validation_rows)
        score.assert_called_once_with(validation_rows, ["prediction"])

    def test_generation_passes_token_batch_fields_and_slices_prompt(self):
        import torch
        from transformers import BatchEncoding

        from training.model import TrainedAdapterModel
        from training.runner import _generate

        class Tokenizer:
            eos_token_id = 0

            def apply_chat_template(self, *args, **kwargs):
                return BatchEncoding({
                    "input_ids": torch.tensor([[1, 2]]),
                    "attention_mask": torch.tensor([[1, 1]]),
                })

            def decode(self, output, skip_special_tokens):
                self.output = output.tolist()
                return "prediction"

        class Model:
            def __init__(self):
                self.parameter = torch.nn.Parameter(torch.zeros(1))

            def parameters(self):
                return iter([self.parameter])

            def generate(self, **inputs):
                self.inputs = inputs
                return torch.cat([inputs["input_ids"], torch.tensor([[3, 4]])], dim=-1)

        tokenizer = Tokenizer()
        model = Model()
        rows = [{"input": "example", "output": {}}]

        self.assertEqual(_generate(model, tokenizer, "Input: {{text}}", rows, max_new_tokens=17), ["prediction"])
        self.assertEqual(set(model.inputs), {"input_ids", "attention_mask", "max_new_tokens", "do_sample", "pad_token_id", "eos_token_id"})
        self.assertEqual(model.inputs["max_new_tokens"], 17)
        self.assertEqual(tokenizer.output, [3, 4])

        adapter = TrainedAdapterModel("a" * 32)
        adapter.model = model
        adapter.tokenizer = tokenizer
        adapter.device = "cpu"
        result = adapter.run("Input: example", {"max_tokens": 8})
        self.assertEqual(result["model"], "trained:" + "a" * 32)
        self.assertEqual(result["output"], "prediction")
        self.assertEqual(result["tokens"], 2)


if __name__ == "__main__":
    unittest.main()
