import time
import oci
from models.base import BaseLLM


class OCIChatModel(BaseLLM):
    def __init__(
        self,
        model_id: str,
        provider: str,   # "cohere" or "generic"
        compartment_id: str,
        endpoint: str,
        config_path: str,
        config_profile: str = "DEFAULT",
        default_params: dict | None = None,
    ):
        self.model_id = model_id
        self.provider = provider
        self.compartment_id = compartment_id
        self.default_params = default_params or {}

        self.config = oci.config.from_file(
            file_location=config_path,
            profile_name=config_profile
        )

        self.client = oci.generative_ai_inference.GenerativeAiInferenceClient(
            config=self.config,
            service_endpoint=endpoint,
            retry_strategy=oci.retry.NoneRetryStrategy(),
            timeout=(10, 240)
        )

    def run(self, prompt: str, params: dict):
        start = time.time()
        merged = {**self.default_params, **params}

        # --------------------------------------------------
        # COHERE (command-a)
        # --------------------------------------------------
        if self.provider == "cohere":
            chat_request = oci.generative_ai_inference.models.CohereChatRequest(
                message=prompt,
                max_tokens=merged.get("max_tokens", 600),
                temperature=merged.get("temperature", 1.0),
                frequency_penalty=merged.get("frequency_penalty", 0),
                top_p=merged.get("top_p", 0.75),
                top_k=merged.get("top_k", 0),
            )

        # --------------------------------------------------
        # GENERIC MODELS (Meta, Grok, Gemini, GPT-OSS)
        # --------------------------------------------------
        else:
            content = oci.generative_ai_inference.models.TextContent()
            content.text = prompt

            message = oci.generative_ai_inference.models.Message()
            message.role = "USER"
            message.content = [content]

            chat_request = oci.generative_ai_inference.models.GenericChatRequest()
            chat_request.api_format = (
                oci.generative_ai_inference.models.BaseChatRequest.API_FORMAT_GENERIC
            )
            chat_request.messages = [message]
            chat_request.max_tokens = merged.get("max_tokens", 2048)
            chat_request.temperature = merged.get("temperature", 1.0)
            chat_request.frequency_penalty = merged.get("frequency_penalty", 0)
            chat_request.presence_penalty = merged.get("presence_penalty", 0)
            chat_request.top_p = merged.get("top_p", 1.0)
            chat_request.top_k = merged.get("top_k", 1)

        chat_details = oci.generative_ai_inference.models.ChatDetails(
            compartment_id=self.compartment_id,
            serving_mode=oci.generative_ai_inference.models.OnDemandServingMode(
                model_id=self.model_id
            ),
            chat_request=chat_request
        )

        response = self.client.chat(chat_details)
        latency = int((time.time() - start) * 1000)

        token_count = 0
        if hasattr(response.data, "usage") and response.data.usage:
            token_count = getattr(response.data.usage, "total_tokens", 0)

        return {
            "output": response.data.chat_response.text,
            "tokens": token_count,
            "latency_ms": latency,
            "model": self.model_id
        }
