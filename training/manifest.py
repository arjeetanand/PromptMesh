import hashlib
import json
import re
from enum import Enum


ADAPTER_MANIFEST_SCHEMA_VERSION = 5
TRAINING_CONFIGURATION_SCHEMA_VERSION = 1

TRAINER_CONFIGURATION_FIELDS = (
    "learning_rate",
    "num_train_epochs",
    "max_steps",
    "per_device_train_batch_size",
    "per_device_eval_batch_size",
    "gradient_accumulation_steps",
    "lr_scheduler_type",
    "warmup_steps",
    "weight_decay",
    "adam_beta1",
    "adam_beta2",
    "adam_epsilon",
    "max_grad_norm",
    "optim",
    "bf16",
    "fp16",
    "tf32",
    "seed",
    "data_seed",
    "eval_strategy",
    "eval_steps",
    "save_strategy",
    "logging_steps",
    "max_length",
    "truncation_mode",
    "dataset_text_field",
    "completion_only_loss",
    "assistant_only_loss",
    "gradient_checkpointing",
    "gradient_checkpointing_kwargs",
    "dataloader_num_workers",
    "dataloader_pin_memory",
    "dataloader_drop_last",
    "packing",
)

LORA_CONFIGURATION_FIELDS = (
    "r",
    "lora_alpha",
    "lora_dropout",
    "target_modules",
    "bias",
    "task_type",
    "init_lora_weights",
    "use_rslora",
    "use_dora",
    "modules_to_save",
    "fan_in_fan_out",
    "layers_to_transform",
    "layers_pattern",
    "rank_pattern",
    "alpha_pattern",
)


def _manifest_value(value):
    if isinstance(value, Enum):
        return _manifest_value(value.value)
    if isinstance(value, dict):
        return {str(key): _manifest_value(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (set, frozenset)):
        return sorted((_manifest_value(item) for item in value), key=lambda item: str(item))
    if isinstance(value, (list, tuple)):
        return [_manifest_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError(f"Unsupported training configuration value: {type(value).__name__}")


def _configuration_section(config, fields, section_name):
    missing = [field for field in fields if not hasattr(config, field)]
    if missing:
        raise ValueError(f"Missing effective {section_name} settings: {', '.join(missing)}")
    return {field: _manifest_value(getattr(config, field)) for field in fields}


def training_configuration_snapshot(trainer_config, lora_config, model_load_dtype):
    if not isinstance(model_load_dtype, str) or not model_load_dtype:
        raise ValueError("Model load dtype must be a non-empty string")
    return {
        "schema_version": TRAINING_CONFIGURATION_SCHEMA_VERSION,
        "trainer": _configuration_section(trainer_config, TRAINER_CONFIGURATION_FIELDS, "trainer"),
        "lora": _configuration_section(lora_config, LORA_CONFIGURATION_FIELDS, "LoRA"),
        "model_load": {
            "dtype": model_load_dtype,
            "local_files_only": True,
            "trust_remote_code": False,
        },
    }


def training_configuration_sha256(configuration):
    content = json.dumps(configuration, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def has_reproducible_training_configuration(manifest):
    configuration = manifest.get("training_configuration") if isinstance(manifest, dict) else None
    if not isinstance(configuration, dict):
        return False
    if configuration.get("schema_version") != TRAINING_CONFIGURATION_SCHEMA_VERSION:
        return False
    trainer = configuration.get("trainer")
    lora = configuration.get("lora")
    model_load = configuration.get("model_load")
    complete = (
        isinstance(trainer, dict)
        and set(TRAINER_CONFIGURATION_FIELDS).issubset(trainer)
        and isinstance(lora, dict)
        and set(LORA_CONFIGURATION_FIELDS).issubset(lora)
        and isinstance(model_load, dict)
        and isinstance(model_load.get("dtype"), str)
        and model_load.get("local_files_only") is True
        and model_load.get("trust_remote_code") is False
    )
    digest = manifest.get("training_configuration_sha256")
    return (
        complete
        and isinstance(digest, str)
        and re.fullmatch(r"[a-f0-9]{64}", digest) is not None
        and digest == training_configuration_sha256(configuration)
    )
