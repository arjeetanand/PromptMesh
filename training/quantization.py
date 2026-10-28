import importlib.util


QUANTIZATION_METHODS = {
    "bnb_int8": {
        "label": "bitsandbytes LLM.int8",
        "weight_bits": 8,
        "quant_type": "LLM.int8",
    },
    "bnb_nf4": {
        "label": "bitsandbytes NF4",
        "weight_bits": 4,
        "quant_type": "NF4",
    },
}


def quantization_runtime():
    if importlib.util.find_spec("bitsandbytes") is None:
        return {"available": False, "methods": [], "reason": "Install the optional bitsandbytes dependency to enable quantized inference."}
    try:
        import bitsandbytes
        import torch
    except (ImportError, OSError, RuntimeError):
        return {"available": False, "methods": [], "reason": "bitsandbytes could not load in this Python environment."}
    device = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
    return {
        "available": True,
        "backend": "bitsandbytes",
        "version": bitsandbytes.__version__,
        "device": device,
        "methods": [
            {"id": method_id, **details, "calibration_required": False}
            for method_id, details in QUANTIZATION_METHODS.items()
        ],
        "calibration_note": "INT8 and NF4 quantize weights on load; this comparison does not use a calibration dataset. AWQ/GPTQ calibration is a separate method.",
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
    raise ValueError("Unsupported quantization method")
