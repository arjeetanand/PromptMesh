import gc
import hashlib
import json
import logging
import os
import platform
import random
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from prompts.registry import PROMPT_BASE_PATH, PromptRegistry
from training.datasets import SPLIT_SEED, benchmark_card_status, load_dataset_snapshot, split_dataset, split_strategy
from training.environment import runtime_metadata
from training.metrics import score_predictions
from training.quantization import QUANTIZATION_METHODS, bitsandbytes_config, quantization_runtime
from training.registry import get_benchmark_adapter
from training.runner import BASE_MODEL_ID, _generate


SELECTIONS_DIR = Path(__file__).parent / "selections"
BENCHMARKS_DIR = Path(__file__).parent / "benchmarks"
MAX_PROMPT_CANDIDATES = 3
SELECTION_ID_RE = re.compile(r"^[a-f0-9]{32}$")
logger = logging.getLogger(__name__)


def _json_digest(value):
    content = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _write_private_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as output:
        output.write(payload)


def _selection_path(selection_id, *, create=False):
    if not isinstance(selection_id, str) or not SELECTION_ID_RE.fullmatch(selection_id):
        raise ValueError("Prompt selection id is invalid")
    if SELECTIONS_DIR.is_symlink():
        raise ValueError("Prompt selection directory is invalid")
    if create:
        SELECTIONS_DIR.mkdir(parents=True, exist_ok=True)
    root = SELECTIONS_DIR.resolve()
    path = SELECTIONS_DIR / f"{selection_id}.json"
    if path.is_symlink() or path.resolve().parent != root:
        raise ValueError("Prompt selection path is invalid")
    return path


def _benchmark_report_path(dataset_id, dataset_digest):
    if not isinstance(dataset_id, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}", dataset_id):
        raise ValueError("Benchmark dataset id is invalid")
    if not isinstance(dataset_digest, str) or not re.fullmatch(r"[a-f0-9]{64}", dataset_digest):
        raise ValueError("Benchmark dataset fingerprint is invalid")
    if BENCHMARKS_DIR.is_symlink():
        raise ValueError("Benchmark report directory is invalid")
    root = BENCHMARKS_DIR.resolve()
    dataset_dir = BENCHMARKS_DIR / dataset_id
    if dataset_dir.is_symlink() or dataset_dir.resolve().parent != root:
        raise ValueError("Benchmark dataset report directory is invalid")
    version_dir = dataset_dir / dataset_digest
    if version_dir.is_symlink() or version_dir.resolve().parent != dataset_dir.resolve():
        raise ValueError("Benchmark version report directory is invalid")
    path = version_dir / "final.json"
    if path.is_symlink():
        raise ValueError("Final benchmark report path is invalid")
    return path


def load_prompt_selection(selection_id):
    path = _selection_path(selection_id)
    if not path.is_file():
        raise ValueError("Prompt selection is not available")
    try:
        selection = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Prompt selection record is invalid") from exc
    if not isinstance(selection, dict) or selection.get("schema_version") != 2 or selection.get("selection_id") != selection_id:
        raise ValueError("Prompt selection record identity is invalid")
    digest = selection.pop("selection_sha256", None)
    if not isinstance(digest, str) or digest != _json_digest(selection):
        raise ValueError("Prompt selection record fingerprint does not match")
    selection["selection_sha256"] = digest
    return selection


def _load_local_model(manifest, adapter_path=None, quantization_method=None):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    device = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
    model_id = manifest["base_model"]
    revision = manifest["base_revision"]
    tokenizer = AutoTokenizer.from_pretrained(
        model_id,
        revision=manifest["tokenizer_revision"],
        trust_remote_code=False,
        local_files_only=True,
    )
    if quantization_method:
        model_dtype = torch.float16 if device in ("mps", "cuda") else torch.float32
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            revision=revision,
            dtype=model_dtype,
            quantization_config=bitsandbytes_config(quantization_method, torch, device),
            device_map={"": device},
            trust_remote_code=False,
            local_files_only=True,
        )
        if adapter_path:
            from peft import PeftModel

            model = PeftModel.from_pretrained(model, adapter_path, is_trainable=False)
    elif adapter_path:
        from peft import AutoPeftModelForCausalLM

        model = AutoPeftModelForCausalLM.from_pretrained(
            adapter_path,
            revision=revision,
            dtype=torch.float32,
            trust_remote_code=False,
            local_files_only=True,
        )
    else:
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            revision=revision,
            dtype=torch.float32,
            trust_remote_code=False,
            local_files_only=True,
        )
    if quantization_method:
        model = model.eval()
    else:
        model = model.to(device).eval()
    return model, tokenizer, device, torch


def _prompt_sha256(template):
    return hashlib.sha256(template.encode("utf-8")).hexdigest()


def _model_footprint_bytes(model):
    try:
        return int(model.get_memory_footprint())
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return None


def _generation_performance(tokenizer, predictions, elapsed_seconds):
    generated_tokens = sum(len(tokenizer.encode(text, add_special_tokens=False)) for text in predictions)
    return {
        "inference_seconds": round(elapsed_seconds, 4),
        "generated_tokens": generated_tokens,
        "tokens_per_second": round(generated_tokens / elapsed_seconds, 3) if elapsed_seconds > 0 else None,
    }


def _clear_device_cache(torch, device):
    gc.collect()
    if device == "mps":
        torch.mps.empty_cache()
    elif device == "cuda":
        torch.cuda.empty_cache()


def validate_prompt_template(template):
    from core.types import render_prompt

    if not isinstance(template, str) or not re.search(r"\{\{\s*text\s*\}\}", template):
        raise ValueError("Every prompt must include a {{text}} input placeholder")
    render_prompt(template, {"text": "prompt validation"})


def _reviewed_dataset(dataset_id):
    rows, dataset_digest = load_dataset_snapshot(dataset_id)
    status = benchmark_card_status(dataset_id, rows, dataset_digest)
    if not status["card_ready"]:
        raise ValueError(status.get("reason") or "A matching reviewer-attested benchmark card is required")
    if not status["validation_ready"] or not status["final_test_ready"]:
        raise ValueError("Validation and final-test splits each need at least 30 examples across 10 source groups")
    return rows, dataset_digest, status


def run_prompt_selection(job_id, request, jobs):
    try:
        if not 1 <= len(request.candidate_prompts) <= MAX_PROMPT_CANDIDATES:
            raise ValueError(f"Provide 1–{MAX_PROMPT_CANDIDATES} prompt candidates")
        rows, dataset_digest, card_status = _reviewed_dataset(request.dataset_id)
        current_split_strategy = split_strategy(rows)
        adapter_path, adapter = get_benchmark_adapter(
            request.adapter_run_id, request.dataset_id, dataset_digest, current_split_strategy
        )
        if adapter["base_model"] != BASE_MODEL_ID:
            raise ValueError("The selected adapter uses an unsupported base model")

        splits = split_dataset(rows)
        validation_rows = splits["validation"]
        if not validation_rows:
            raise ValueError("The validation split is empty")
        metadata = PromptRegistry().load_with_metadata("extraction", "v1")
        initial_prompt = metadata["template"]
        initial_prompt_source_hash = hashlib.sha256(
            (PROMPT_BASE_PATH / "extraction" / "v1.yaml").read_bytes()
        ).hexdigest()
        candidates = [{"id": "extraction/v1", "prompt": initial_prompt}]
        candidates.extend(
            {"id": f"candidate-{index}", "prompt": prompt}
            for index, prompt in enumerate(request.candidate_prompts, start=1)
        )
        for candidate in candidates:
            validate_prompt_template(candidate["prompt"])

        jobs.update(job_id, {"progress": 5, "stage": "loading_local_model"})
        model, tokenizer, device, torch = _load_local_model(adapter)
        scored = []
        for index, candidate in enumerate(candidates):
            jobs.update(job_id, {
                "progress": 10 + int(80 * index / len(candidates)),
                "stage": "scoring_validation_prompt",
                "message": f"Scoring prompt {index + 1} of {len(candidates)} on validation only.",
            })
            predictions = _generate(model, tokenizer, candidate["prompt"], validation_rows)
            metrics = score_predictions(validation_rows, predictions)
            scored.append({
                "id": candidate["id"],
                "prompt": candidate["prompt"],
                "prompt_sha256": _prompt_sha256(candidate["prompt"]),
                "metrics": metrics,
            })
        chosen_index = max(
            range(len(scored)),
            key=lambda index: (
                scored[index]["metrics"]["record_exact_match"],
                scored[index]["metrics"]["field_accuracy"],
                scored[index]["metrics"]["json_valid_rate"],
                -index,
            ),
        )
        selection_id = uuid.uuid4().hex
        selection = {
            "schema_version": 2,
            "selection_id": selection_id,
            "dataset_id": request.dataset_id,
            "dataset_sha256": dataset_digest,
            "benchmark_card_sha256": card_status["card_sha256"],
            "adapter_run_id": request.adapter_run_id,
            "adapter_sha256": adapter["adapter_sha256"],
            "base_model": adapter["base_model"],
            "base_revision": adapter["base_revision"],
            "tokenizer_revision": adapter["tokenizer_revision"],
            "metrics_split": "validation",
            "test_split_used": False,
            "split_seed": SPLIT_SEED,
            "split_strategy": current_split_strategy,
            "validation_examples": len(validation_rows),
            "validation_source_groups": len({row["group_id"] for row in validation_rows}),
            "selection_rule": "record_exact_match, then field_accuracy, then json_valid_rate; ties keep the earlier prompt",
            "initial_prompt_source_sha256": initial_prompt_source_hash,
            "candidates": scored,
            "selected_prompt_id": scored[chosen_index]["id"],
            "selected_prompt": scored[chosen_index]["prompt"],
            "selected_prompt_sha256": scored[chosen_index]["prompt_sha256"],
            "device": device,
            "environment": runtime_metadata(device),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        selection["selection_sha256"] = _json_digest(selection)
        _write_private_json(_selection_path(selection_id, create=True), selection)
        jobs.update(job_id, {
            "status": "completed",
            "progress": 100,
            "stage": "completed",
            "result": {
                "selection_id": selection_id,
                "dataset_id": request.dataset_id,
                "adapter_run_id": request.adapter_run_id,
                "dataset_sha256": dataset_digest,
                "metrics_split": "validation",
                "validation_examples": len(validation_rows),
                "selected_prompt_id": selection["selected_prompt_id"],
                "selected_prompt_sha256": selection["selected_prompt_sha256"],
                "environment": selection["environment"],
                "candidates": [
                    {"id": item["id"], "prompt_sha256": item["prompt_sha256"], "metrics": item["metrics"]}
                    for item in scored
                ],
            },
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as exc:
        logger.exception("Validation prompt selection job %s failed", job_id)
        jobs.update(job_id, {"status": "failed", "progress": 100, "error": str(exc) or type(exc).__name__})
        raise


def _record_accuracy_ci(rows, predictions, seed=42, samples=1000):
    from training.metrics import _is_exact_record, _parse_output

    groups = {}
    for row, prediction in zip(rows, predictions):
        exact = _is_exact_record(row, _parse_output(prediction))
        current = groups.setdefault(row["group_id"], [0, 0])
        current[0] += int(exact)
        current[1] += 1
    group_values = list(groups.values())
    if len(group_values) < 2:
        return None
    rng = random.Random(seed)
    bootstrap = []
    for _ in range(samples):
        selected = [group_values[rng.randrange(len(group_values))] for _ in group_values]
        total_correct = sum(item[0] for item in selected)
        total_examples = sum(item[1] for item in selected)
        bootstrap.append(total_correct / total_examples)
    bootstrap.sort()
    return {
        "method": "source-group bootstrap percentile interval",
        "confidence_level": 0.95,
        "lower": round(bootstrap[int(samples * 0.025)], 4),
        "upper": round(bootstrap[min(samples - 1, int(samples * 0.975))], 4),
        "source_groups": len(group_values),
        "resamples": samples,
        "seed": seed,
    }


def _existing_report(dataset_id, dataset_digest, configuration_digest):
    path = _benchmark_report_path(dataset_id, dataset_digest)
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("An existing final benchmark report is unreadable; do not overwrite it") from exc
        if not isinstance(existing, dict):
            raise ValueError("An existing final benchmark report is invalid")
        report_hash = existing.pop("report_sha256", None)
        if report_hash != _json_digest(existing):
            raise ValueError("An existing final benchmark report failed its integrity check")
        if existing.get("configuration_sha256") != configuration_digest:
            raise ValueError("A final report already exists for this dataset fingerprint; create a new dataset version before another test run")
        return existing | {"report_sha256": report_hash}, False
    return None


def _reservation_path(dataset_id, dataset_digest):
    return _benchmark_report_path(dataset_id, dataset_digest).with_name("reservation.json")


def _reject_reserved_benchmark(dataset_id, dataset_digest):
    if _reservation_path(dataset_id, dataset_digest).exists():
        raise ValueError("A frozen test run is already reserved and may have accessed this holdout; create a new dataset version before another run")


def _reserve_frozen_benchmark(dataset_id, dataset_digest, configuration_digest, selection_id):
    reservation = {
        "schema_version": 1,
        "dataset_id": dataset_id,
        "dataset_sha256": dataset_digest,
        "configuration_sha256": configuration_digest,
        "selection_id": selection_id,
        "reserved_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        _write_private_json(_reservation_path(dataset_id, dataset_digest), reservation)
    except FileExistsError as exc:
        raise ValueError("A frozen test run is already reserved and may have accessed this holdout; create a new dataset version before another run") from exc


def _complete_report(report):
    report["report_sha256"] = _json_digest(report)
    path = _benchmark_report_path(report["dataset_id"], report["dataset_sha256"])
    try:
        _write_private_json(path, report)
        return report, True
    except FileExistsError:
        existing = _existing_report(report["dataset_id"], report["dataset_sha256"], report["configuration_sha256"])
        if existing is None:
            raise
        return existing


def run_frozen_benchmark(job_id, request, jobs):
    try:
        requested_methods = list(getattr(request, "quantization_methods", []))
        if len(requested_methods) != len(set(requested_methods)) or any(method not in QUANTIZATION_METHODS for method in requested_methods):
            raise ValueError("Quantization methods must be unique supported methods")
        quantization_methods = sorted(requested_methods)
        selection = load_prompt_selection(request.selection_id)
        rows, dataset_digest, card_status = _reviewed_dataset(selection["dataset_id"])
        if dataset_digest != selection["dataset_sha256"] or card_status["card_sha256"] != selection["benchmark_card_sha256"]:
            raise ValueError("Dataset or benchmark card changed after validation prompt selection")
        current_split_strategy = split_strategy(rows)
        if selection.get("split_seed") != SPLIT_SEED or selection.get("split_strategy") != current_split_strategy:
            raise ValueError("Dataset split policy changed after validation prompt selection")
        adapter_path, adapter = get_benchmark_adapter(
            request.adapter_run_id, selection["dataset_id"], dataset_digest, current_split_strategy
        )
        if request.adapter_run_id != selection["adapter_run_id"] or adapter["adapter_sha256"] != selection["adapter_sha256"]:
            raise ValueError("The adapter differs from the validation-selected adapter")
        if adapter["base_model"] != selection["base_model"] or adapter["base_revision"] != selection["base_revision"]:
            raise ValueError("The adapter checkpoint differs from validation prompt selection")
        readiness = benchmark_card_status(selection["dataset_id"], rows, dataset_digest)
        if not readiness["final_test_ready"]:
            raise ValueError("The reserved final-test split is below the minimum example or source-group count")
        splits = split_dataset(rows)
        test_rows = splits["test"]
        test_groups = len({row["group_id"] for row in test_rows})
        if len(test_rows) != readiness["final_test_examples"] or test_groups != readiness["final_test_source_groups"]:
            raise ValueError("Dataset changed while preparing the final test split")
        configuration = {
            "selection_sha256": selection["selection_sha256"],
            "adapter_run_id": request.adapter_run_id,
            "adapter_sha256": adapter["adapter_sha256"],
            "selected_prompt_sha256": selection["selected_prompt_sha256"],
            "dataset_sha256": dataset_digest,
            "benchmark_card_sha256": card_status["card_sha256"],
        }
        if quantization_methods:
            configuration["quantization_methods"] = quantization_methods
        configuration_digest = _json_digest(configuration)
        existing = _existing_report(selection["dataset_id"], dataset_digest, configuration_digest)
        if existing:
            final_report, created = existing
            jobs.update(job_id, {
                "status": "completed",
                "progress": 100,
                "stage": "completed",
                "result": {"report": final_report, "created": created},
                "completed_at": datetime.now(timezone.utc).isoformat(),
            })
            return
        _reject_reserved_benchmark(selection["dataset_id"], dataset_digest)

        quant_runtime = None
        if quantization_methods:
            quant_runtime = quantization_runtime()
            available_methods = {item["id"] for item in quant_runtime.get("methods", [])}
            if not quant_runtime["available"] or not set(quantization_methods).issubset(available_methods):
                raise ValueError(quant_runtime.get("reason") or "The requested quantization backend is unavailable")

        baseline_prompt = next(item["prompt"] for item in selection["candidates"] if item["id"] == "extraction/v1")
        selected_prompt = selection["selected_prompt"]

        # Exercise every selected backend with a fixed synthetic input before reserving the one-shot test split.
        for index, method in enumerate(quantization_methods):
            jobs.update(job_id, {
                "progress": 2 + int(2 * index / max(len(quantization_methods), 1)),
                "stage": "checking_quantized_backend",
                "message": "Checking the selected quantized backend using a fixed synthetic prompt.",
            })
            canary_model, canary_tokenizer, canary_device, canary_torch = _load_local_model(
                adapter, adapter_path, quantization_method=method
            )
            try:
                if canary_device != quant_runtime["device"]:
                    raise ValueError("Quantized and full-precision inference resolved to different devices")
                _generate(
                    canary_model,
                    canary_tokenizer,
                    selected_prompt,
                    [{"input": "Northstar announced a research center in 2024."}],
                    max_new_tokens=8,
                )
            finally:
                del canary_model
                _clear_device_cache(canary_torch, canary_device)

        jobs.update(job_id, {"progress": 5, "stage": "loading_local_base_model"})
        base_load_started = time.perf_counter()
        base_model, tokenizer, device, torch = _load_local_model(adapter)
        base_load_seconds = time.perf_counter() - base_load_started
        _reserve_frozen_benchmark(selection["dataset_id"], dataset_digest, configuration_digest, request.selection_id)
        jobs.update(job_id, {"progress": 15, "stage": "scoring_frozen_test"})
        baseline_started = time.perf_counter()
        baseline_predictions = _generate(base_model, tokenizer, baseline_prompt, test_rows)
        baseline_seconds = time.perf_counter() - baseline_started
        baseline_metrics = score_predictions(test_rows, baseline_predictions)
        if selection["selected_prompt_sha256"] == _prompt_sha256(baseline_prompt):
            selected_predictions = baseline_predictions
            selected_metrics = baseline_metrics
            selected_seconds = baseline_seconds
        else:
            selected_started = time.perf_counter()
            selected_predictions = _generate(base_model, tokenizer, selected_prompt, test_rows)
            selected_seconds = time.perf_counter() - selected_started
            selected_metrics = score_predictions(test_rows, selected_predictions)
        baseline_ci = _record_accuracy_ci(test_rows, baseline_predictions)
        selected_ci = baseline_ci if selected_predictions is baseline_predictions else _record_accuracy_ci(test_rows, selected_predictions)
        del base_model
        _clear_device_cache(torch, device)

        jobs.update(job_id, {"progress": 55, "stage": "scoring_frozen_adapter"})
        adapter_load_started = time.perf_counter()
        adapted_model, adapter_tokenizer, _, _ = _load_local_model(adapter, adapter_path)
        adapter_load_seconds = time.perf_counter() - adapter_load_started
        adapter_footprint = _model_footprint_bytes(adapted_model)
        adapter_inference_started = time.perf_counter()
        adapter_predictions = _generate(adapted_model, adapter_tokenizer, selected_prompt, test_rows)
        adapter_inference_seconds = time.perf_counter() - adapter_inference_started
        adapter_metrics = score_predictions(test_rows, adapter_predictions)
        adapter_ci = _record_accuracy_ci(test_rows, adapter_predictions)
        adapter_performance = {
            "load_seconds": round(adapter_load_seconds, 4),
            **_generation_performance(adapter_tokenizer, adapter_predictions, adapter_inference_seconds),
            "model_footprint_bytes": adapter_footprint,
        }
        del adapted_model
        _clear_device_cache(torch, device)

        quantized_variants = []
        for index, method in enumerate(quantization_methods):
            jobs.update(job_id, {
                "progress": 65 + int(25 * index / max(len(quantization_methods), 1)),
                "stage": "scoring_quantized_adapter",
                "message": f"Scoring {QUANTIZATION_METHODS[method]['label']} on the same frozen test rows.",
            })
            quantized_load_started = time.perf_counter()
            quantized_model, quantized_tokenizer, quantized_device, quantized_torch = _load_local_model(
                adapter, adapter_path, quantization_method=method
            )
            quantized_load_seconds = time.perf_counter() - quantized_load_started
            model_footprint = _model_footprint_bytes(quantized_model)
            inference_started = time.perf_counter()
            predictions = _generate(quantized_model, quantized_tokenizer, selected_prompt, test_rows)
            inference_seconds = time.perf_counter() - inference_started
            metrics = score_predictions(test_rows, predictions)
            metrics["record_exact_match_95ci"] = _record_accuracy_ci(test_rows, predictions)
            quantized_variants.append({
                "id": method,
                **QUANTIZATION_METHODS[method],
                "backend": "bitsandbytes",
                "backend_version": quant_runtime["version"],
                "device": quantized_device,
                "compute_dtype": "float16" if quantized_device in ("mps", "cuda") else "float32",
                "double_quantization": method == "bnb_nf4",
                "llm_int8_threshold": 6.0 if method == "bnb_int8" else None,
                "calibration_required": False,
                "load_seconds": round(quantized_load_seconds, 4),
                **_generation_performance(quantized_tokenizer, predictions, inference_seconds),
                "model_footprint_bytes": model_footprint,
                "metrics": metrics,
            })
            del quantized_model
            _clear_device_cache(quantized_torch, quantized_device)

        report = {
            "schema_version": 2,
            "status": "completed",
            "dataset_id": selection["dataset_id"],
            "dataset_sha256": dataset_digest,
            "benchmark_card_sha256": card_status["card_sha256"],
            "selection_id": request.selection_id,
            "selection_sha256": selection["selection_sha256"],
            "base_model": adapter["base_model"],
            "base_revision": adapter["base_revision"],
            "tokenizer_revision": adapter["tokenizer_revision"],
            "initial_prompt_source_sha256": selection["initial_prompt_source_sha256"],
            "adapter_run_id": request.adapter_run_id,
            "adapter_sha256": adapter["adapter_sha256"],
            "adapter_environment": adapter.get("environment"),
            "prompt_selection_environment": selection.get("environment"),
            "selected_prompt_id": selection["selected_prompt_id"],
            "selected_prompt_sha256": selection["selected_prompt_sha256"],
            "metrics_split": "test",
            "test_split_used_for_selection": False,
            "split_seed": SPLIT_SEED,
            "split_strategy": current_split_strategy,
            "test_examples": len(test_rows),
            "test_source_groups": test_groups,
            "inference": {"max_new_tokens": 128, "do_sample": False, "temperature": None},
            "performance": {
                "base_full_precision_load_seconds": round(base_load_seconds, 4),
                "base_initial_prompt_inference_seconds": round(baseline_seconds, 4),
                "base_selected_prompt_inference_seconds": round(selected_seconds, 4),
                "lora_full_precision": adapter_performance,
                "memory_note": "Model footprint is not peak device memory; cold single-run timings are not a throughput benchmark.",
            },
            "hardware": {
                "device": device,
                "machine": platform.machine(),
                "processor": platform.processor() or None,
                "torch_version": str(torch.__version__),
            },
            "environment": runtime_metadata(device),
            "metrics": {
                "base_initial_prompt": {**baseline_metrics, "record_exact_match_95ci": baseline_ci},
                "base_validation_selected_prompt": {**selected_metrics, "record_exact_match_95ci": selected_ci},
                "lora_validation_selected_prompt": {**adapter_metrics, "record_exact_match_95ci": adapter_ci},
            },
            "configuration_sha256": configuration_digest,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if quantization_methods:
            report["quantized_inference"] = {
                "backend": "bitsandbytes",
                "backend_version": quant_runtime["version"],
                "calibration_required": False,
                "calibration_note": quant_runtime["calibration_note"],
                "adapter_training_method": "Full-precision LoRA + SFT; this inference comparison is not QLoRA training.",
                "variants": quantized_variants,
            }
        final_report, created = _complete_report(report)
        jobs.update(job_id, {
            "status": "completed",
            "progress": 100,
            "stage": "completed",
            "result": {"report": final_report, "created": created},
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as exc:
        logger.exception("Frozen benchmark job %s failed", job_id)
        jobs.update(job_id, {"status": "failed", "progress": 100, "error": str(exc) or type(exc).__name__})
        raise
