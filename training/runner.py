import hashlib
import importlib.util
import json
import logging
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from training.datasets import (
    format_sft_rows,
    load_dataset_snapshot,
    SPLIT_SEED,
    split_counts,
    split_dataset,
    split_strategy,
)
from training.environment import runtime_metadata
from training.holdout_registry import DEFAULT_BENCHMARKS_DIR as BENCHMARKS_DIR, assert_rows_unseen
from training.manifest import (
    ADAPTER_MANIFEST_SCHEMA_VERSION,
    training_configuration_sha256,
    training_configuration_snapshot,
)
from training.metrics import score_predictions
from training.registry import RUNS_DIR, artifact_tree_sha256


BASE_MODEL_ID = "Qwen/Qwen3-0.6B"
logger = logging.getLogger(__name__)
TRAINING_PACKAGES = ("torch", "transformers", "peft", "trl", "datasets", "accelerate")


def training_runtime():
    missing = [name for name in TRAINING_PACKAGES if importlib.util.find_spec(name) is None]
    device = "unavailable"
    if not missing:
        import torch

        device = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
    return {"available": not missing, "missing": missing, "device": device, "base_model": BASE_MODEL_ID}


def _resolve_cached_base_revision():
    from huggingface_hub import snapshot_download

    snapshot = Path(snapshot_download(BASE_MODEL_ID, local_files_only=True))
    if snapshot.parent.name != "snapshots":
        raise RuntimeError("Could not identify the cached base-model revision")
    return snapshot.name


def _model_inputs(model, tokenizer, prompt_template, row):
    from core.types import render_prompt

    prompt = render_prompt(prompt_template, {"text": row["input"]})
    prompt += "\nReturn only a JSON object with exactly these keys: organization, year, claim. Use null for missing fields."
    return tokenizer.apply_chat_template(
        [{"role": "user", "content": prompt}],
        tokenize=True,
        add_generation_prompt=True,
        return_tensors="pt",
        enable_thinking=False,
    ).to(next(model.parameters()).device)


def _generate(model, tokenizer, prompt_template, rows, max_new_tokens=128, return_token_counts=False):
    import torch

    outputs = []
    token_counts = []
    for row in rows:
        inputs = _model_inputs(model, tokenizer, prompt_template, row)
        input_length = inputs["input_ids"].shape[-1]
        with torch.inference_mode():
            generated = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )
        generated_tokens = generated[0, input_length:]
        outputs.append(tokenizer.decode(generated_tokens, skip_special_tokens=True).strip())
        if return_token_counts:
            token_counts.append(int(generated_tokens.numel()))
    return (outputs, token_counts) if return_token_counts else outputs


def _score_validation(model, tokenizer, prompt_template, splits):
    rows = splits["validation"]
    outputs = _generate(model, tokenizer, prompt_template, rows)
    return score_predictions(rows, outputs)


def _save_manifest(path, manifest):
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _sft_config_kwargs(request, output_dir):
    return {
        "output_dir": str(output_dir),
        "learning_rate": request.learning_rate,
        "num_train_epochs": request.epochs,
        "per_device_train_batch_size": 1,
        "per_device_eval_batch_size": 1,
        "gradient_accumulation_steps": 4,
        "eval_strategy": "epoch",
        "save_strategy": "no",
        "logging_steps": 1,
        "report_to": "none",
        "max_length": 512,
        "completion_only_loss": True,
        "gradient_checkpointing": False,
        "dataloader_num_workers": 0,
        "optim": "adamw_torch",
        "seed": 42,
        "data_seed": 42,
        "disable_tqdm": True,
        "bf16": False,
        "fp16": False,
    }


def run_lora_training(job_id, request, jobs):
    started = time.perf_counter()
    run_dir = None

    try:
        import torch
        from datasets import Dataset
        from peft import LoraConfig
        from transformers import AutoModelForCausalLM, AutoTokenizer, TrainerCallback
        from trl import SFTConfig, SFTTrainer

        from prompts.registry import PROMPT_BASE_PATH, PromptRegistry

        rows, dataset_hash = load_dataset_snapshot(request.dataset_id)
        splits = split_dataset(rows)
        assert_rows_unseen(
            splits["train"] + splits["validation"], BENCHMARKS_DIR, "LoRA training/validation data"
        )
        counts = split_counts(splits)
        prompt_version = "v1"
        prompt = PromptRegistry().load_with_metadata("extraction", prompt_version)["template"]
        prompt_path = PROMPT_BASE_PATH / "extraction" / f"{prompt_version}.yaml"
        prompt_hash = hashlib.sha256(prompt_path.read_bytes()).hexdigest()
        run_id = uuid.uuid4().hex
        run_dir = RUNS_DIR / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        adapter_dir = run_dir / "adapter"
        jobs.update(job_id, {"progress": 5, "stage": "loading_model"})
        device = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
        base_revision = _resolve_cached_base_revision()
        model_load_dtype = "float32"
        model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL_ID,
            revision=base_revision,
            dtype=getattr(torch, model_load_dtype),
            trust_remote_code=False,
            local_files_only=True,
        ).to(device)
        tokenizer_args = {
            "revision": base_revision,
            "trust_remote_code": False,
            "local_files_only": True,
        }
        tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_ID, **tokenizer_args)

        jobs.update(job_id, {"progress": 10, "stage": "evaluating_base"})
        base_metrics = _score_validation(model, tokenizer, prompt, splits)

        class ProgressCallback(TrainerCallback):
            def on_log(self, args, state, control, logs=None, **kwargs):
                logs = logs or {}
                steps = max(state.max_steps, 1)
                progress = 10 + min(70, int(70 * state.global_step / steps))
                payload = {"progress": progress, "stage": "training"}
                if "loss" in logs:
                    payload["training_loss"] = logs["loss"]
                if "eval_loss" in logs:
                    payload["validation_loss"] = logs["eval_loss"]
                jobs.update(job_id, payload)

        train_rows = Dataset.from_list(format_sft_rows(splits["train"], prompt))
        validation_rows = Dataset.from_list(format_sft_rows(splits["validation"], prompt))
        config = SFTConfig(**_sft_config_kwargs(request, run_dir / "checkpoint"))
        lora_config = LoraConfig(
            r=request.lora_rank,
            lora_alpha=request.lora_rank * 2,
            lora_dropout=0.05,
            bias="none",
            task_type="CAUSAL_LM",
            target_modules=["q_proj", "v_proj"],
        )
        training_configuration = training_configuration_snapshot(config, lora_config, model_load_dtype)
        trainer = SFTTrainer(
            model=model,
            args=config,
            train_dataset=train_rows,
            eval_dataset=validation_rows,
            processing_class=tokenizer,
            peft_config=lora_config,
            callbacks=[ProgressCallback()],
        )
        trainer.train()
        trainer.save_model(str(adapter_dir))
        adapter_hash = artifact_tree_sha256(adapter_dir)

        jobs.update(job_id, {"progress": 85, "stage": "evaluating_adapter"})
        adapter_metrics = _score_validation(trainer.model, tokenizer, prompt, splits)
        log_history = trainer.state.log_history
        training_losses = [entry["loss"] for entry in log_history if "loss" in entry]
        validation_losses = [entry["eval_loss"] for entry in log_history if "eval_loss" in entry]
        completed_at = datetime.now(timezone.utc).isoformat()
        metrics = {"base": base_metrics, "adapter": adapter_metrics}
        manifest = {
            "schema_version": ADAPTER_MANIFEST_SCHEMA_VERSION,
            "status": "completed",
            "run_id": run_id,
            "base_model": BASE_MODEL_ID,
            "base_revision": base_revision,
            "tokenizer_revision": base_revision,
            "dataset_id": request.dataset_id,
            "dataset_sha256": dataset_hash,
            "adapter_sha256": adapter_hash,
            "task": "entity_extraction",
            "prompt_version": f"extraction/{prompt_version}",
            "prompt_sha256": prompt_hash,
            "split_counts": counts,
            "split_seed": SPLIT_SEED,
            "split_strategy": split_strategy(rows),
            "metrics_split": "validation",
            "test_split_used": False,
            "environment": runtime_metadata(device),
            "training_configuration": training_configuration,
            "training_configuration_sha256": training_configuration_sha256(training_configuration),
            "hyperparameters": {
                "method": "LoRA + supervised fine-tuning",
                "lora_rank": request.lora_rank,
                "learning_rate": request.learning_rate,
                "epochs": request.epochs,
                "seed": 42,
                "device": device,
            },
            "metrics": metrics,
            "training_loss": training_losses,
            "validation_loss": validation_losses,
            "created_at": completed_at,
        }
        _save_manifest(run_dir / "manifest.json", manifest)
        jobs.update(job_id, {
            "status": "completed",
            "progress": 100,
            "stage": "completed",
            "result": {
                "run_id": run_id,
                "model_id": f"trained:{run_id}",
                "base_model": BASE_MODEL_ID,
                "dataset_id": request.dataset_id,
                "dataset_sha256": dataset_hash,
                "split_counts": counts,
                "split_seed": SPLIT_SEED,
                "split_strategy": split_strategy(rows),
                "metrics_split": "validation",
                "device": device,
                "metrics": metrics,
                "training_configuration": training_configuration,
                "training_loss": training_losses,
                "validation_loss": validation_losses,
                "elapsed_seconds": round(time.perf_counter() - started, 1),
            },
            "completed_at": completed_at,
        })
    except Exception as exc:
        logger.exception("LoRA training job %s failed", job_id)
        if run_dir:
            shutil.rmtree(run_dir, ignore_errors=True)
        jobs.update(job_id, {"status": "failed", "progress": 100, "error": str(exc) or type(exc).__name__})
        raise
