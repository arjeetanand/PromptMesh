import sys
import types
import unittest
from unittest.mock import patch

from training import quantization


class QuantizationTests(unittest.TestCase):
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
        self.assertIn("AWQ/GPTQ calibration is a separate method", runtime["calibration_note"])
        self.assertTrue(all(not method["calibration_required"] for method in runtime["methods"]))


if __name__ == "__main__":
    unittest.main()
