import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from models.cohere_model import CohereModel
from training.datasets import dataset_path, dataset_sha256, list_datasets, load_dataset, split_counts, split_dataset
from training.metrics import score_predictions
from training.registry import get_adapter_path, list_adapters


class TrainingDatasetTests(unittest.TestCase):
    def test_dataset_ids_cannot_escape_the_local_dataset_directory(self):
        with self.assertRaises(ValueError):
            dataset_path("../outside")

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

        self.assertEqual(_generate(model, tokenizer, "Input: {{text}}", rows), ["prediction"])
        self.assertEqual(set(model.inputs), {"input_ids", "attention_mask", "max_new_tokens", "do_sample", "pad_token_id", "eos_token_id"})
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
