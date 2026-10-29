import sys
import types
import unittest
from contextlib import nullcontext
from unittest.mock import patch

from training import quantization


class QuantizationTests(unittest.TestCase):
    def test_calibration_sample_is_deterministic_grouped_and_label_free(self):
        train_rows = [
            {"group_id": f"group-{group}", "input": f"input {group}-{variant}", "output": {"year": 2024}}
            for group in range(20)
            for variant in range(3)
        ]

        first = quantization.select_calibration_rows(train_rows)
        second = quantization.select_calibration_rows(train_rows)

        self.assertEqual(first, second)
        self.assertEqual(len(first), quantization.CALIBRATION_GROUP_LIMIT)
        self.assertEqual(len({row["group_id"] for row in first}), len(first))
        self.assertTrue(all(set(row) == {"group_id", "input"} for row in first))
        self.assertEqual(
            first,
            quantization.select_calibration_rows(list(reversed(train_rows))),
            "input selection is independent of split row order",
        )

    def test_calibration_sample_rejects_empty_or_unbounded_configuration(self):
        with self.assertRaisesRegex(ValueError, "at least one training"):
            quantization.select_calibration_rows([])
        with self.assertRaisesRegex(ValueError, "positive integer"):
            quantization.select_calibration_rows([{"group_id": "g", "input": "x"}], 0)

    def test_nf4_config_uses_normal_float_and_double_quant_without_calibration(self):
        configs = []

        class FakeBitsAndBytesConfig:
            def __init__(self, **kwargs):
                configs.append(kwargs)

        fake_transformers = types.ModuleType("transformers")
        fake_transformers.BitsAndBytesConfig = FakeBitsAndBytesConfig
        fake_torch = types.SimpleNamespace(float16="fp16", float32="fp32")

        with patch.dict(sys.modules, {"transformers": fake_transformers}):
            quantization.bitsandbytes_config("bnb_nf4", fake_torch, "mps")

        self.assertEqual(configs, [{
            "load_in_4bit": True,
            "bnb_4bit_quant_type": "nf4",
            "bnb_4bit_compute_dtype": "fp16",
            "bnb_4bit_use_double_quant": True,
        }])

    def test_int8_config_does_not_claim_an_offline_calibration_set(self):
        configs = []

        class FakeBitsAndBytesConfig:
            def __init__(self, **kwargs):
                configs.append(kwargs)

        fake_transformers = types.ModuleType("transformers")
        fake_transformers.BitsAndBytesConfig = FakeBitsAndBytesConfig
        fake_torch = types.SimpleNamespace(float16="fp16", float32="fp32")

        with patch.dict(sys.modules, {"transformers": fake_transformers}):
            quantization.bitsandbytes_config("bnb_int8", fake_torch, "mps")

        self.assertEqual(configs, [{"load_in_8bit": True}])
        self.assertFalse(quantization.QUANTIZATION_METHODS["bnb_int8"].get("calibration_required", False))

    def test_runtime_reports_calibration_free_methods_and_separates_awq_gptq(self):
        fake_bnb = types.ModuleType("bitsandbytes")
        fake_bnb.__version__ = "0.50.0"
        fake_torch = types.SimpleNamespace(
            backends=types.SimpleNamespace(
                mps=types.SimpleNamespace(is_available=lambda: True),
                cuda=types.SimpleNamespace(is_available=lambda: False),
            )
        )
        with patch.object(quantization.importlib.util, "find_spec", return_value=object()), \
             patch.dict(sys.modules, {"bitsandbytes": fake_bnb, "torch": fake_torch}):
            runtime = quantization.quantization_runtime()

        self.assertTrue(runtime["available"])
        self.assertEqual(runtime["device"], "mps")
        self.assertIn("AWQ/GPTQ are not included", runtime["calibration_note"])
        self.assertTrue(all(not method["calibration_required"] for method in runtime["methods"]))

    def test_runtime_exposes_quanto_w8a8_when_the_optional_backend_loads(self):
        fake_bnb = types.ModuleType("bitsandbytes")
        fake_bnb.__version__ = "0.50.0"
        fake_optimum = types.ModuleType("optimum")
        fake_optimum.__path__ = []
        fake_quanto = types.ModuleType("optimum.quanto")
        fake_quanto.__version__ = "0.2.7"
        fake_torch = types.SimpleNamespace(
            backends=types.SimpleNamespace(
                mps=types.SimpleNamespace(is_available=lambda: True),
                cuda=types.SimpleNamespace(is_available=lambda: False),
            )
        )
        with patch.object(quantization.importlib.util, "find_spec", return_value=object()), \
             patch.dict(sys.modules, {
                 "bitsandbytes": fake_bnb,
                 "optimum": fake_optimum,
                 "optimum.quanto": fake_quanto,
                 "torch": fake_torch,
             }):
            runtime = quantization.quantization_runtime()

        methods = {method["id"]: method for method in runtime["methods"]}
        self.assertTrue(runtime["available"])
        self.assertEqual(runtime["device"], "mps")
        self.assertEqual(runtime["backends"], {"bitsandbytes": "0.50.0", "optimum-quanto": "0.2.7"})
        self.assertTrue(methods["quanto_int8_w8a8"]["calibration_required"])
        self.assertEqual(methods["quanto_int8_w8a8"]["activation_bits"], 8)

    def test_quanto_w8a8_calibrates_the_supplied_train_inputs_then_freezes(self):
        events = []

        class Calibration:
            def __init__(self, **kwargs):
                events.append(("calibration", kwargs))

            def __enter__(self):
                events.append("calibration_start")

            def __exit__(self, *_args):
                events.append("calibration_end")

        fake_quanto = types.ModuleType("optimum.quanto")
        fake_quanto.Calibration = Calibration
        fake_quanto.qint8 = "qint8"
        fake_quanto.quantize = lambda model, **kwargs: events.append(("quantize", kwargs))
        fake_quanto.freeze = lambda model: events.append("freeze")
        fake_optimum = types.ModuleType("optimum")
        fake_optimum.__path__ = []

        class FakeModel:
            def __init__(self):
                self.inputs = []

            def __call__(self, **kwargs):
                self.inputs.append(kwargs)

            def eval(self):
                events.append("eval")
                return self

        model = FakeModel()
        rows = [{"group_id": f"train-{i}", "input": f"train input {i}"} for i in range(2)]
        fake_torch = types.SimpleNamespace(no_grad=nullcontext)

        with patch.dict(sys.modules, {"optimum": fake_optimum, "optimum.quanto": fake_quanto}), \
             patch("training.runner._model_inputs", side_effect=lambda _m, _t, _p, row: {"input_ids": row["input"]}):
            metadata = quantization.apply_quanto_int8_calibration(
                model, object(), "Extract {{text}}", rows, fake_torch, "cpu"
            )

        self.assertEqual(events[0], ("quantize", {"weights": "qint8", "activations": "qint8"}))
        self.assertEqual(events[1], ("calibration", {"momentum": quantization.CALIBRATION_MOMENTUM}))
        self.assertEqual(model.inputs, [
            {"input_ids": "train input 0", "use_cache": False},
            {"input_ids": "train input 1", "use_cache": False},
        ])
        self.assertEqual(events[-2:], ["freeze", "eval"])
        self.assertGreaterEqual(metadata["calibration_seconds"], 0)
        self.assertGreaterEqual(metadata["quantization_seconds"], 0)


if __name__ == "__main__":
    unittest.main()
