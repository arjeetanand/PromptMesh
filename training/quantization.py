"""Optional local inference quantization backends."""

import importlib
import importlib.metadata
import importlib.util
import random
import time


CALIBRATION_GROUP_LIMIT = 16
CALIBRATION_SEED = 42
CALIBRATION_MOMENTUM = 0.9
QUANTO_INT8_METHOD = "quanto_int8_w8a8"

QUANTIZATION_METHODS = {
    "bnb_int8": {
        "backend": "bitsandbytes",
        "label": "bitsandbytes LLM.int8",
        "weight_bits": 8,
        "activation_bits": None,
        "quant_type": "LLM.int8",
        "calibration_required": False,
    },
    "bnb_nf4": {
        "backend": "bitsandbytes",
        "label": "bitsandbytes NF4",
        "weight_bits": 4,
        "activation_bits": None,
        "quant_type": "NF4",
        "calibration_required": False,
    },
    QUANTO_INT8_METHOD: {
        "backend": "optimum-quanto",
        "label": "Quanto INT8 weights + INT8 activations",
        "weight_bits": 8,
        "activation_bits": 8,
        "quant_type": "qint8",
        "calibration_required": True,
    },
}


def select_calibration_rows(train_rows, max_groups=CALIBRATION_GROUP_LIMIT):
    """Choose one deterministic, label-free input from each sampled train group."""
    if not isinstance(max_groups, int) or max_groups < 1:
        raise ValueError("Quanto calibration group limit must be a positive integer")
    if not train_rows:
        raise ValueError("Quanto calibration requires at least one training-split source group")
    grouped_inputs = {}
    for row in train_rows:
        group_id = row.get("group_id")
        if not group_id:
            raise ValueError("Quanto calibration rows must have source-group IDs")
        grouped_inputs.setdefault(group_id, []).append(row["input"])
    group_ids = sorted(grouped_inputs)
    rng = random.Random(CALIBRATION_SEED)
    sampled_inputs = {
        group_id: rng.choice(sorted(grouped_inputs[group_id]))
        for group_id in group_ids
    }
    rng.shuffle(group_ids)
    return [
        {"group_id": group_id, "input": sampled_inputs[group_id]}
        for group_id in group_ids[:max_groups]
    ]


def apply_quanto_int8_calibration(model, tokenizer, prompt_template, calibration_rows, torch, device):
    """Apply Quanto W8A8 PTQ and record activation ranges on input-only samples."""
    if not calibration_rows:
        raise ValueError("Quanto calibration requires training-split inputs")
    from optimum.quanto import Calibration, freeze, qint8, quantize
    from training.runner import _model_inputs

    _synchronize_device(torch, device)
    quantization_started = time.perf_counter()
    quantize(model, weights=qint8, activations=qint8)
    _synchronize_device(torch, device)
    quantization_seconds = time.perf_counter() - quantization_started
    _synchronize_device(torch, device)
    calibration_started = time.perf_counter()
    with Calibration(momentum=CALIBRATION_MOMENTUM):
        for row in calibration_rows:
            inputs = _model_inputs(model, tokenizer, prompt_template, row)
            with torch.no_grad():
                model(**inputs, use_cache=False)
    _synchronize_device(torch, device)
    calibration_seconds = time.perf_counter() - calibration_started
    _synchronize_device(torch, device)
    freeze_started = time.perf_counter()
    freeze(model)
    _synchronize_device(torch, device)
    quantization_seconds += time.perf_counter() - freeze_started
    model.eval()
    return {
        "calibration_seconds": calibration_seconds,
        "quantization_seconds": quantization_seconds,
        "calibration_momentum": CALIBRATION_MOMENTUM,
    }


def _synchronize_device(torch, device):
    if device == "mps":
        torch.mps.synchronize()
    elif device == "cuda":
        torch.cuda.synchronize()


def _load_backend(module_name, distribution_name):
    try:
        spec = importlib.util.find_spec(module_name)
    except (ImportError, ModuleNotFoundError, ValueError):
        return None, None
    if spec is None:
        return None, None
    try:
        module = importlib.import_module(module_name)
    except (ImportError, OSError, RuntimeError):
        return None, None
    version = getattr(module, "__version__", None)
    if not version:
        try:
            version = importlib.metadata.version(distribution_name)
        except importlib.metadata.PackageNotFoundError:
            version = "unknown"
    return module, version


def quantization_runtime():
    backends = {}
    modules = {}
    for module_name, distribution_name in (
        ("bitsandbytes", "bitsandbytes"),
        ("optimum.quanto", "optimum-quanto"),
    ):
        module, version = _load_backend(module_name, distribution_name)
        if module is not None:
            backend_name = "optimum-quanto" if distribution_name == "optimum-quanto" else distribution_name
            backends[backend_name] = version
            modules[backend_name] = module

    if not modules:
        return {
            "available": False,
            "methods": [],
            "reason": "Install an optional local quantization backend from requirements-quantization.txt.",
            "calibration_note": "Quanto W8A8 uses label-free inputs from the training split only; bitsandbytes methods do not use offline calibration.",
        }
    try:
        import torch
    except (ImportError, OSError, RuntimeError):
        return {
            "available": False,
            "methods": [],
            "reason": "PyTorch could not load in this Python environment.",
            "calibration_note": "Quanto W8A8 uses label-free inputs from the training split only; bitsandbytes methods do not use offline calibration.",
        }

    mps = getattr(getattr(torch, "backends", None), "mps", None)
    device = "mps" if mps and mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
    methods = [
        {"id": method_id, **details, "backend_version": backends[details["backend"]]}
        for method_id, details in QUANTIZATION_METHODS.items()
        if details["backend"] in backends
    ]
    return {
        "available": bool(methods),
        "backend": next(iter(backends)) if len(backends) == 1 else "multiple",
        "version": next(iter(backends.values())) if len(backends) == 1 else None,
        "backends": backends,
        "device": device,
        "methods": methods,
        "calibration_note": "Quanto W8A8 calibrates activation ranges using label-free training-split inputs only; bitsandbytes LLM.int8 and NF4 do not use an offline calibration dataset. AWQ/GPTQ are not included.",
    }


def bitsandbytes_config(method_id, torch, device):
    from transformers import BitsAndBytesConfig

    if method_id == "bnb_int8":
        return BitsAndBytesConfig(load_in_8bit=True)
    if method_id == "bnb_nf4":
        return BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16 if device in ("mps", "cuda") else torch.float32,
            bnb_4bit_use_double_quant=True,
        )
    raise ValueError("Unsupported bitsandbytes quantization method")
