import time

from models.base import BaseLLM
from training.registry import get_adapter_path


class TrainedAdapterModel(BaseLLM):
    def __init__(self, run_id):
        self.run_id = run_id
        self.model = None
        self.tokenizer = None
        self.device = None

    def _load(self):
        if self.model is not None:
            return
        import torch
        from peft import AutoPeftModelForCausalLM
        from transformers import AutoTokenizer

        adapter_path, manifest = get_adapter_path(self.run_id)
        self.device = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
        tokenizer_args = {"trust_remote_code": False}
        if manifest.get("base_revision"):
            tokenizer_args["revision"] = manifest["base_revision"]
        self.tokenizer = AutoTokenizer.from_pretrained(manifest["base_model"], **tokenizer_args)
        self.model = AutoPeftModelForCausalLM.from_pretrained(
            adapter_path,
            dtype=torch.float32,
            trust_remote_code=False,
            revision=manifest.get("base_revision"),
        ).to(self.device).eval()

    def run(self, prompt: str, params: dict):
        import torch

        self._load()
        messages = [{"role": "user", "content": prompt}]
        input_ids = self.tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt",
            enable_thinking=False,
        ).to(self.device)
        input_length = input_ids["input_ids"].shape[-1]
        start = time.perf_counter()
        if self.device == "mps":
            torch.mps.synchronize()
        with torch.inference_mode():
            generated = self.model.generate(
                **input_ids,
                max_new_tokens=params.get("max_tokens", 128),
                do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )
        if self.device == "mps":
            torch.mps.synchronize()
        latency = round((time.perf_counter() - start) * 1000)
        output_ids = generated[0, input_length:]
        return {
            "output": self.tokenizer.decode(output_ids, skip_special_tokens=True).strip(),
            "tokens": int(output_ids.numel()),
            "latency_ms": latency,
            "model": f"trained:{self.run_id}",
        }
