import hashlib
import json
import sys
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

        with patch.object(benchmark, "_load_local_model", return_value=(object(), object(), "cpu", types.SimpleNamespace(__version__="test"), {})), \
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

    def test_gold_year_slices_report_group_counts_and_grouped_intervals(self):
        gold = {"organization": "Northstar", "year": 2024, "claim": "opened a lab"}
        rows = [
            {"group_id": "group-a", "output": gold},
            {"group_id": "group-a", "output": gold},
            {"group_id": "group-b", "output": gold},
            {"group_id": "group-c", "output": {**gold, "year": 2023}},
            {"group_id": "group-d", "output": {**gold, "year": None}},
        ]
        predictions = [
            json.dumps(gold), json.dumps(gold), "not json",
            json.dumps({**gold, "year": 2023}), json.dumps({**gold, "year": None}),
        ]

        slices = benchmark._metrics_by_gold_year(rows, predictions)

        self.assertEqual(list(slices), ["2023", "2024", "undated"])
        self.assertEqual(slices["2024"]["examples"], 3)
        self.assertEqual(slices["2024"]["source_groups"], 2)
        self.assertEqual(slices["2024"]["record_exact_match"], 0.6667)
        self.assertEqual(slices["2024"]["field_exact_match"]["year"], 0.6667)
        self.assertEqual(slices["2024"]["record_exact_match_95ci"]["source_groups"], 2)
        self.assertEqual(slices["2023"]["source_groups"], 1)
        self.assertIsNone(slices["2023"]["record_exact_match_95ci"])
        self.assertEqual(slices["undated"]["record_exact_match"], 1.0)

    def test_generation_timing_synchronizes_accelerators_and_uses_wall_clock(self):
        events = []
        fake_torch = types.SimpleNamespace(
            mps=types.SimpleNamespace(synchronize=lambda: events.append("mps")),
            cuda=types.SimpleNamespace(synchronize=lambda: events.append("cuda")),
        )

        def generate(*_args, **kwargs):
            self.assertTrue(kwargs["return_token_counts"])
            events.append("generate")
            return ["prediction"], [7]

        with patch.object(benchmark, "_generate", side_effect=generate), \
             patch.object(benchmark.time, "perf_counter", side_effect=[10.0, 12.0]):
            result = benchmark._measure_generation("model", "tokenizer", "prompt", [], fake_torch, "mps")

        self.assertEqual(result, (["prediction"], [7], 2.0))
        self.assertEqual(events, ["mps", "generate", "mps"])
        benchmark._synchronize_device(fake_torch, "cuda")
        benchmark._synchronize_device(fake_torch, "cpu")
        self.assertEqual(events, ["mps", "generate", "mps", "cuda"])

    def test_frozen_report_compares_matched_arms_and_cannot_be_reused_for_a_sweep(self):
        selection_id, _ = self._select_prompt()
        jobs = JobRecorder()

        def generate(_model, _tokenizer, prompt, rows, return_token_counts=False):
            if prompt.startswith("Custom extractor"):
                predictions = [json.dumps(row["output"]) for row in rows]
            else:
                predictions = ["not json"] * len(rows)
            return (predictions, [2] * len(rows)) if return_token_counts else predictions

        request = types.SimpleNamespace(selection_id=selection_id, adapter_run_id=self.adapter_run_id)
        fake_torch = types.SimpleNamespace(__version__="test")
        with patch.object(benchmark, "_load_local_model", return_value=(object(), FakeTokenizer(), "cpu", fake_torch, {})) as load_model, \
             patch.object(benchmark, "_generate", side_effect=generate), \
             patch.object(benchmark, "runtime_metadata", return_value={
                 "device": "cpu", "source_revision": "c" * 40, "source_dirty": False,
             }):
            benchmark.run_frozen_benchmark("benchmark-job", request, jobs)
            first_result = next(changes["result"] for job_id, changes in jobs.updates if job_id == "benchmark-job" and "result" in changes)
            report = first_result["report"]
            self.assertEqual(report["schema_version"], 5)
            self.assertEqual(report["metrics_split"], "test")
            self.assertEqual(report["split_strategy"], "group-year-stratified-v1")
            self.assertFalse(report["test_split_used_for_selection"])
            self.assertEqual(report["metrics"]["base_initial_prompt"]["record_exact_match"], 0.0)
            self.assertEqual(report["metrics"]["base_validation_selected_prompt"]["record_exact_match"], 1.0)
            self.assertEqual(report["metrics"]["lora_validation_selected_prompt"]["record_exact_match"], 1.0)
            self.assertEqual(report["performance"]["lora_full_precision"]["generated_tokens"], 60)
            self.assertIn("Synchronized wall-clock generation", report["performance"]["timing_method"])
            year_slice = report["metrics"]["lora_validation_selected_prompt"]["by_gold_year"]["2024"]
            self.assertEqual(year_slice["examples"], 30)
            self.assertEqual(year_slice["source_groups"], 30)
            self.assertEqual(year_slice["record_exact_match"], 1.0)
            self.assertEqual(year_slice["record_exact_match_95ci"]["method"], "source-group bootstrap percentile interval")
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

    def test_quantized_inference_uses_matched_test_rows_and_train_only_calibration(self):
        selection_id, _ = self._select_prompt()
        jobs = JobRecorder()
        fake_torch = types.SimpleNamespace(__version__="test")
        generated_inputs = []
        loader_calls = []
        calibration_calls = []
        train_groups = {row["group_id"] for row in benchmark.split_dataset(self.rows)["train"]}

        class FakeModel:
            def get_memory_footprint(self):
                return 123456

        def load_model(_manifest, _adapter_path=None, quantization_method=None, **kwargs):
            loader_calls.append(quantization_method)
            calibration_rows = kwargs.get("calibration_rows")
            if quantization_method == "quanto_int8_w8a8":
                calibration_calls.append(calibration_rows)
                self.assertTrue(calibration_rows)
                self.assertTrue(all(row["group_id"] in train_groups for row in calibration_rows))
                self.assertTrue(all(set(row) == {"group_id", "input"} for row in calibration_rows))
                return FakeModel(), FakeTokenizer(), "cpu", fake_torch, {
                    "calibration_seconds": 0.25,
                    "quantization_seconds": 0.5,
                }
            return FakeModel(), FakeTokenizer(), "cpu", fake_torch, {}

        def generate(_model, _tokenizer, prompt, rows, max_new_tokens=128, return_token_counts=False):
            generated_inputs.append((max_new_tokens, [row.get("group_id") for row in rows]))
            if "group_id" not in rows[0]:
                predictions = ["synthetic canary"]
            elif prompt.startswith("Custom extractor"):
                predictions = [json.dumps(row["output"]) for row in rows]
            else:
                predictions = ["not json"] * len(rows)
            return (predictions, [2] * len(rows)) if return_token_counts else predictions

        request = types.SimpleNamespace(
            selection_id=selection_id,
            adapter_run_id=self.adapter_run_id,
            quantization_methods=["bnb_nf4", "quanto_int8_w8a8"],
        )
        runtime = {
            "available": True,
            "version": "0.50.0-test",
            "backends": {"bitsandbytes": "0.50.0-test", "optimum-quanto": "0.2.7-test"},
            "device": "cpu",
            "methods": [{"id": "bnb_nf4"}, {"id": "quanto_int8_w8a8"}],
            "calibration_note": "Quanto uses training-only inputs.",
        }
        with patch.object(benchmark, "quantization_runtime", return_value=runtime), \
             patch.object(benchmark, "_load_local_model", side_effect=load_model), \
             patch.object(benchmark, "_generate", side_effect=generate):
            benchmark.run_frozen_benchmark("quantized-job", request, jobs)

        report = next(changes["result"]["report"] for job_id, changes in jobs.updates if job_id == "quantized-job" and "result" in changes)
        variant = report["quantized_inference"]["variants"][0]
        self.assertEqual(report["environment"]["device"], "cpu")
        self.assertIn("torch", report["environment"]["packages"])
        self.assertEqual(loader_calls, ["bnb_nf4", "quanto_int8_w8a8", None, None, "bnb_nf4", "quanto_int8_w8a8"])
        self.assertEqual(generated_inputs[0], (8, [None]))
        self.assertEqual(generated_inputs[-1][1], generated_inputs[-2][1])
        self.assertEqual(report["metrics_split"], "test")
        self.assertTrue(report["quantized_inference"]["calibration_required"])
        self.assertFalse(variant["calibration_required"])
        quanto_variant = report["quantized_inference"]["variants"][1]
        self.assertTrue(quanto_variant["calibration_required"])
        self.assertEqual(quanto_variant["calibration_seconds"], 0.25)
        self.assertEqual(quanto_variant["quantization_seconds"], 0.5)
        self.assertEqual(report["quantized_inference"]["calibration"]["split"], "train")
        self.assertEqual(report["quantized_inference"]["calibration"]["examples"], 16)
        self.assertEqual(report["quantized_inference"]["calibration"]["source_groups"], 16)
        self.assertEqual(len(calibration_calls), 2)
        self.assertEqual(calibration_calls[0], calibration_calls[1])
        self.assertEqual(variant["model_footprint_bytes"], 123456)
        self.assertEqual(variant["generated_tokens"], 60)
        self.assertEqual(variant["metrics"]["record_exact_match"], 1.0)
        self.assertEqual(variant["metrics"]["by_gold_year"]["2024"]["source_groups"], 30)
        quantized_delta = variant["metrics"]["paired_record_exact_match_delta_95ci"]
        self.assertEqual(quantized_delta["estimate"], 0.0)
        self.assertEqual(quantized_delta["reference"], "Full-precision LoRA control")
        self.assertIn("not QLoRA", report["quantized_inference"]["adapter_training_method"])

    def test_quanto_loader_merges_the_pinned_local_adapter_before_calibration(self):
        events = []
        tokenizer = object()
        calibration_rows = [{"group_id": "train-1", "input": "Training source"}]
        manifest = {
            "base_model": "Qwen/Qwen3-0.6B",
            "base_revision": "base-revision",
            "tokenizer_revision": "tokenizer-revision",
        }

        class FakeTokenizerLoader:
            @staticmethod
            def from_pretrained(*args, **kwargs):
                events.append(("tokenizer", args, kwargs))
                return tokenizer

        class FakeModel:
            def merge_and_unload(self, **kwargs):
                events.append(("merge", kwargs))
                return self

            def to(self, device):
                events.append(("device", device))
                return self

            def eval(self):
                events.append("eval")
                return self

        class FakePeftLoader:
            @staticmethod
            def from_pretrained(*args, **kwargs):
                events.append(("adapter", args, kwargs))
                return FakeModel()

        fake_torch = types.ModuleType("torch")
        fake_torch.float16 = "float16"
        fake_torch.float32 = "float32"
        fake_torch.backends = types.SimpleNamespace(
            mps=types.SimpleNamespace(is_available=lambda: False),
        )
        fake_torch.cuda = types.SimpleNamespace(is_available=lambda: False)
        fake_transformers = types.ModuleType("transformers")
        fake_transformers.AutoModelForCausalLM = object
        fake_transformers.AutoTokenizer = FakeTokenizerLoader
        fake_peft = types.ModuleType("peft")
        fake_peft.AutoPeftModelForCausalLM = FakePeftLoader
        metadata = {"calibration_seconds": 0.2, "quantization_seconds": 0.4}

        with patch.dict(sys.modules, {
            "torch": fake_torch,
            "transformers": fake_transformers,
            "peft": fake_peft,
        }), patch.object(benchmark, "apply_quanto_int8_calibration", return_value=metadata) as calibrate:
            model, loaded_tokenizer, device, torch, result_metadata = benchmark._load_local_model(
                manifest,
                Path("/private/local-adapter"),
                quantization_method="quanto_int8_w8a8",
                calibration_rows=calibration_rows,
                calibration_prompt="Extract {{text}}",
            )

        self.assertEqual(loaded_tokenizer, tokenizer)
        self.assertEqual(device, "cpu")
        self.assertIs(torch, fake_torch)
        self.assertIs(result_metadata, metadata)
        self.assertIn(("merge", {"safe_merge": True}), events)
        self.assertIn(("device", "cpu"), events)
        tokenizer_call = next(event for event in events if isinstance(event, tuple) and event[0] == "tokenizer")
        self.assertEqual(tokenizer_call[2]["revision"], "tokenizer-revision")
        self.assertTrue(tokenizer_call[2]["local_files_only"])
        adapter_call = next(event for event in events if isinstance(event, tuple) and event[0] == "adapter")
        self.assertEqual(adapter_call[1], (Path("/private/local-adapter"),))
        self.assertEqual(adapter_call[2]["revision"], "base-revision")
        self.assertTrue(adapter_call[2]["local_files_only"])
        calibrate.assert_called_once_with(
            model, tokenizer, "Extract {{text}}", calibration_rows, fake_torch, "cpu"
        )

    def test_failed_test_inference_reserves_holdout_and_blocks_retry(self):
        selection_id, _ = self._select_prompt()
        request = types.SimpleNamespace(selection_id=selection_id, adapter_run_id=self.adapter_run_id)
        jobs = JobRecorder()
        fake_torch = types.SimpleNamespace(__version__="test")

        with patch.object(benchmark, "_load_local_model", return_value=(object(), object(), "cpu", fake_torch, {})), patch.object(benchmark, "_generate", side_effect=RuntimeError("inference failed")):
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
