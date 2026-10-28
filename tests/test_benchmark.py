import hashlib
import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from training import benchmark
from training.registry import artifact_tree_sha256


class JobRecorder:
    def __init__(self):
        self.updates = []

    def update(self, job_id, changes):
        self.updates.append((job_id, changes))


class FakeTokenizer:
    def encode(self, text, add_special_tokens=False):
        return text.split()


class FrozenBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.dataset_dir = root / "datasets"
        self.dataset_dir.mkdir()
        self.runs_dir = root / "runs"
        self.selections_dir = root / "selections"
        self.benchmarks_dir = root / "benchmarks"
        self.rows = [
            {
                "group_id": f"source-{index}",
                "input": f"Private source text {index}",
                "output": {"organization": f"Org {index}", "year": 2024, "claim": f"claim {index}"},
            }
            for index in range(200)
        ]
        content = "".join(json.dumps(row) + "\n" for row in self.rows).encode("utf-8")
        self.dataset_digest = hashlib.sha256(content).hexdigest()
        (self.dataset_dir / "reviewed.jsonl").write_bytes(content)
        card = {
            "schema_version": 1,
            "dataset_id": "reviewed",
            "dataset_sha256": self.dataset_digest,
            "task": "entity_extraction",
            "source": {"description": "Public reports", "authorization_or_license": "CC BY 4.0"},
            "grouping": {"unit": "source document", "policy": "One source per group"},
            "annotation": {
                "guidelines_version": "v1",
                "review_status": "human_reviewed",
                "all_labels_human_reviewed": True,
                "total_examples": 200,
                "reviewed_examples": 200,
                "total_source_groups": 200,
                "reviewed_source_groups": 200,
                "reviewed_at_utc": "2026-10-28T12:00:00Z",
                "reviewer_role": "domain reviewer",
            },
            "limitations": ["Synthetic test fixture; not model evidence"],
        }
        (self.dataset_dir / "reviewed.card.json").write_text(json.dumps(card), encoding="utf-8")

        run_id = "a" * 32
        run_dir = self.runs_dir / run_id
        adapter_dir = run_dir / "adapter"
        adapter_dir.mkdir(parents=True)
        (adapter_dir / "adapter_config.json").write_text("{}", encoding="utf-8")
        self.adapter_manifest = {
            "schema_version": 4,
            "status": "completed",
            "run_id": run_id,
            "base_model": "Qwen/Qwen3-0.6B",
            "base_revision": "base-revision",
            "tokenizer_revision": "base-revision",
            "dataset_id": "reviewed",
            "dataset_sha256": self.dataset_digest,
            "metrics_split": "validation",
            "test_split_used": False,
            "split_seed": 42,
            "split_strategy": "group-year-stratified-v1",
            "adapter_sha256": artifact_tree_sha256(adapter_dir),
            "environment": {
                "device": "cpu", "python_version": "3.12-test", "source_revision": "a" * 40,
                "source_dirty": False, "packages": {"torch": "test"},
            },
        }
        (run_dir / "manifest.json").write_text(json.dumps(self.adapter_manifest), encoding="utf-8")
        self.adapter_run_id = run_id
        self.patchers = [
            patch("training.datasets.DATASET_DIR", self.dataset_dir),
            patch("training.registry.RUNS_DIR", self.runs_dir),
            patch.object(benchmark, "SELECTIONS_DIR", self.selections_dir),
            patch.object(benchmark, "BENCHMARKS_DIR", self.benchmarks_dir),
        ]
        for patcher in self.patchers:
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(self.temp.cleanup)

    def _select_prompt(self, candidate="Custom extractor:\n{{text}}"):
        jobs = JobRecorder()
        request = types.SimpleNamespace(
            dataset_id="reviewed",
            adapter_run_id=self.adapter_run_id,
            candidate_prompts=[candidate],
        )
        validation_groups = {
            row["group_id"] for row in benchmark.split_dataset(self.rows)["validation"]
        }
        generated_groups = []

        def generate(_model, _tokenizer, prompt, rows):
            generated_groups.append({row["group_id"] for row in rows})
            if prompt.startswith("Custom extractor"):
                return [json.dumps(row["output"]) for row in rows]
            return ["not json"] * len(rows)

        with patch.object(benchmark, "_load_local_model", return_value=(object(), object(), "cpu", types.SimpleNamespace(__version__="test"))), \
             patch.object(benchmark, "_generate", side_effect=generate), \
             patch.object(benchmark, "runtime_metadata", return_value={
                 "device": "cpu", "source_revision": "b" * 40, "source_dirty": True,
             }):
            benchmark.run_prompt_selection("selection-job", request, jobs)
        self.assertEqual(generated_groups, [validation_groups, validation_groups])
        result = next(changes["result"] for job_id, changes in jobs.updates if job_id == "selection-job" and "result" in changes)
        return result["selection_id"], jobs

    def test_prompt_selection_uses_validation_gold_and_persists_hashes(self):
        selection_id, jobs = self._select_prompt()
        selection = benchmark.load_prompt_selection(selection_id)

        self.assertEqual(selection["metrics_split"], "validation")
        self.assertFalse(selection["test_split_used"])
        self.assertEqual(selection["split_strategy"], "group-year-stratified-v1")
        self.assertEqual(selection["selected_prompt_id"], "candidate-1")
        self.assertEqual(selection["environment"]["device"], "cpu")
        self.assertEqual(selection["environment"]["source_revision"], "b" * 40)
        self.assertTrue(selection["environment"]["source_dirty"])
        result = next(changes["result"] for _job_id, changes in jobs.updates if "result" in changes)
        self.assertEqual(result["environment"]["device"], "cpu")
        self.assertEqual(len(selection["selection_sha256"]), 64)
        self.assertNotIn("Private source text", json.dumps(selection))

    def test_paired_exact_match_interval_weights_examples_within_resampled_groups(self):
        gold = {"organization": "Northstar", "year": 2024, "claim": "opened a lab"}
        rows = [
            {"group_id": group_id, "output": gold}
            for group_id in ("group-a", "group-a", "group-a", "group-b")
        ]
        reference = ["not json", "not json", "not json", json.dumps(gold)]
        comparison = [json.dumps(gold), json.dumps(gold), json.dumps(gold), "not json"]

        interval = benchmark._record_accuracy_difference_ci(
            rows, reference, comparison, "reference", "comparison"
        )

        self.assertEqual(interval["method"], "paired source-group bootstrap percentile interval")
        self.assertEqual(interval["direction"], "comparison minus reference")
        self.assertEqual(interval["estimate"], 0.5)
        self.assertEqual((interval["lower"], interval["upper"]), (-1.0, 1.0))
        self.assertEqual(interval["source_groups"], 2)
        with self.assertRaisesRegex(ValueError, "match a non-empty frozen test split"):
            benchmark._record_accuracy_difference_ci(rows, reference[:-1], comparison, "reference", "comparison")

    def test_paired_interval_is_zero_when_arms_match_on_every_source_group(self):
        gold = {"organization": "Northstar", "year": 2024, "claim": "opened a lab"}
        rows = [
            {"group_id": group_id, "output": gold}
            for group_id in ("group-a", "group-a", "group-b", "group-b")
        ]
        predictions = [json.dumps(gold), json.dumps(gold), "not json", "not json"]

        interval = benchmark._record_accuracy_difference_ci(
            rows, predictions, predictions, "reference", "comparison"
        )

        self.assertEqual(interval["estimate"], 0.0)
        self.assertEqual((interval["lower"], interval["upper"]), (0.0, 0.0))

    def test_frozen_report_compares_matched_arms_and_cannot_be_reused_for_a_sweep(self):
        selection_id, _ = self._select_prompt()
        jobs = JobRecorder()

        def generate(_model, _tokenizer, prompt, rows):
            if prompt.startswith("Custom extractor"):
                return [json.dumps(row["output"]) for row in rows]
            return ["not json"] * len(rows)

        request = types.SimpleNamespace(selection_id=selection_id, adapter_run_id=self.adapter_run_id)
        fake_torch = types.SimpleNamespace(__version__="test")
        with patch.object(benchmark, "_load_local_model", return_value=(object(), FakeTokenizer(), "cpu", fake_torch)) as load_model, \
             patch.object(benchmark, "_generate", side_effect=generate), \
             patch.object(benchmark, "runtime_metadata", return_value={
                 "device": "cpu", "source_revision": "c" * 40, "source_dirty": False,
             }):
            benchmark.run_frozen_benchmark("benchmark-job", request, jobs)
            first_result = next(changes["result"] for job_id, changes in jobs.updates if job_id == "benchmark-job" and "result" in changes)
            report = first_result["report"]
            self.assertEqual(report["schema_version"], 3)
            self.assertEqual(report["metrics_split"], "test")
            self.assertEqual(report["split_strategy"], "group-year-stratified-v1")
            self.assertFalse(report["test_split_used_for_selection"])
            self.assertEqual(report["metrics"]["base_initial_prompt"]["record_exact_match"], 0.0)
            self.assertEqual(report["metrics"]["base_validation_selected_prompt"]["record_exact_match"], 1.0)
            self.assertEqual(report["metrics"]["lora_validation_selected_prompt"]["record_exact_match"], 1.0)
            prompt_delta = report["metrics"]["base_validation_selected_prompt"]["paired_record_exact_match_delta_95ci"]
            lora_delta = report["metrics"]["lora_validation_selected_prompt"]["paired_record_exact_match_delta_95ci"]
            self.assertEqual(prompt_delta["estimate"], 1.0)
            self.assertEqual(prompt_delta["reference"], "Base · extraction/v1")
            self.assertEqual(lora_delta["estimate"], 0.0)
            self.assertEqual(lora_delta["reference"], "Base · validation-selected prompt")
            self.assertEqual(report["test_examples"], 30)
            self.assertEqual(report["test_source_groups"], 30)
            self.assertEqual(report["adapter_environment"]["python_version"], "3.12-test")
            self.assertEqual(report["adapter_environment"]["source_revision"], "a" * 40)
            self.assertFalse(report["adapter_environment"]["source_dirty"])
            self.assertEqual(report["prompt_selection_environment"]["device"], "cpu")
            self.assertEqual(report["prompt_selection_environment"]["source_revision"], "b" * 40)
            self.assertTrue(report["prompt_selection_environment"]["source_dirty"])
            self.assertEqual(report["environment"]["device"], "cpu")
            self.assertEqual(report["environment"]["source_revision"], "c" * 40)
            self.assertFalse(report["environment"]["source_dirty"])
            self.assertEqual(report["metrics"]["lora_validation_selected_prompt"]["record_exact_match_95ci"]["method"], "source-group bootstrap percentile interval")
            report_path = self.benchmarks_dir / "reviewed" / self.dataset_digest / "final.json"
            reservation_path = self.benchmarks_dir / "reviewed" / self.dataset_digest / "reservation.json"
            self.assertTrue(reservation_path.is_file())
            self.assertNotIn("Private source text", report_path.read_text(encoding="utf-8"))

            load_model.reset_mock()
            benchmark.run_frozen_benchmark("benchmark-job-repeat", request, jobs)
            self.assertEqual(load_model.call_count, 0, "same frozen config should return its existing report without rerunning test inference")

        other_selection_id, _ = self._select_prompt("Different candidate:\n{{text}}")
        other_request = types.SimpleNamespace(selection_id=other_selection_id, adapter_run_id=self.adapter_run_id)
        with patch.object(benchmark, "_load_local_model", side_effect=AssertionError("test model must not be loaded")):
            with self.assertLogs(benchmark.logger, level="ERROR"):
                with self.assertRaisesRegex(ValueError, "final report already exists"):
                    benchmark.run_frozen_benchmark("benchmark-job-sweep", other_request, jobs)

    def test_quantized_inference_is_measured_on_the_same_test_rows_and_marked_calibration_free(self):
        selection_id, _ = self._select_prompt()
        jobs = JobRecorder()
        fake_torch = types.SimpleNamespace(__version__="test")
        generated_inputs = []
        loader_calls = []

        class FakeModel:
            def get_memory_footprint(self):
                return 123456

        def load_model(_manifest, _adapter_path=None, quantization_method=None):
            loader_calls.append(quantization_method)
            return FakeModel(), FakeTokenizer(), "cpu", fake_torch

        def generate(_model, _tokenizer, prompt, rows, max_new_tokens=128):
            generated_inputs.append((max_new_tokens, [row.get("group_id") for row in rows]))
            if "group_id" not in rows[0]:
                return ["synthetic canary"]
            if prompt.startswith("Custom extractor"):
                return [json.dumps(row["output"]) for row in rows]
            return ["not json"] * len(rows)

        request = types.SimpleNamespace(
            selection_id=selection_id,
            adapter_run_id=self.adapter_run_id,
            quantization_methods=["bnb_nf4"],
        )
        runtime = {
            "available": True,
            "version": "0.50.0-test",
            "device": "cpu",
            "methods": [{"id": "bnb_nf4"}],
            "calibration_note": "No calibration corpus used.",
        }
        with patch.object(benchmark, "quantization_runtime", return_value=runtime), \
             patch.object(benchmark, "_load_local_model", side_effect=load_model), \
             patch.object(benchmark, "_generate", side_effect=generate):
            benchmark.run_frozen_benchmark("quantized-job", request, jobs)

        report = next(changes["result"]["report"] for job_id, changes in jobs.updates if job_id == "quantized-job" and "result" in changes)
        variant = report["quantized_inference"]["variants"][0]
        self.assertEqual(report["environment"]["device"], "cpu")
        self.assertIn("torch", report["environment"]["packages"])
        self.assertEqual(loader_calls, ["bnb_nf4", None, None, "bnb_nf4"])
        self.assertEqual(generated_inputs[0], (8, [None]))
        self.assertEqual(generated_inputs[-1][1], generated_inputs[-2][1])
        self.assertEqual(report["metrics_split"], "test")
        self.assertFalse(report["quantized_inference"]["calibration_required"])
        self.assertFalse(variant["calibration_required"])
        self.assertEqual(variant["model_footprint_bytes"], 123456)
        self.assertEqual(variant["metrics"]["record_exact_match"], 1.0)
        quantized_delta = variant["metrics"]["paired_record_exact_match_delta_95ci"]
        self.assertEqual(quantized_delta["estimate"], 0.0)
        self.assertEqual(quantized_delta["reference"], "Full-precision LoRA control")
        self.assertIn("not QLoRA", report["quantized_inference"]["adapter_training_method"])

    def test_failed_test_inference_reserves_holdout_and_blocks_retry(self):
        selection_id, _ = self._select_prompt()
        request = types.SimpleNamespace(selection_id=selection_id, adapter_run_id=self.adapter_run_id)
        jobs = JobRecorder()
        fake_torch = types.SimpleNamespace(__version__="test")

        with patch.object(benchmark, "_load_local_model", return_value=(object(), object(), "cpu", fake_torch)), patch.object(benchmark, "_generate", side_effect=RuntimeError("inference failed")):
            with self.assertLogs(benchmark.logger, level="ERROR"):
                with self.assertRaisesRegex(RuntimeError, "inference failed"):
                    benchmark.run_frozen_benchmark("benchmark-job-fail", request, jobs)

        reservation_path = self.benchmarks_dir / "reviewed" / self.dataset_digest / "reservation.json"
        self.assertTrue(reservation_path.is_file())
        with patch.object(benchmark, "_load_local_model", side_effect=AssertionError("reservation must be checked before loading")):
            with self.assertLogs(benchmark.logger, level="ERROR"):
                with self.assertRaisesRegex(ValueError, "already reserved"):
                    benchmark.run_frozen_benchmark("benchmark-job-retry", request, jobs)

    def test_only_one_process_can_reserve_the_frozen_holdout(self):
        path = benchmark._reservation_path("reviewed", self.dataset_digest)
        benchmark._reserve_frozen_benchmark("reviewed", self.dataset_digest, "b" * 64, "c" * 32)

        self.assertTrue(path.is_file())
        with self.assertRaisesRegex(ValueError, "already reserved"):
            benchmark._reserve_frozen_benchmark("reviewed", self.dataset_digest, "d" * 64, "e" * 32)


if __name__ == "__main__":
    unittest.main()
