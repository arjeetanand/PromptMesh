from models.ollama_model import OllamaModel
from models.cohere_model import CohereModel
from models.oci_chat_model import OCIChatModel

OCI_CONFIG_PATH = r"C:\Users\Arjeet\Desktop\projects\prompt\mcp\ociConfig\config"
OCI_ENDPOINT = "https://inference.generativeai.us-chicago-1.oci.oraclecloud.com"
OCI_COMPARTMENT_ID = "ocid1.compartment.oc1..aaaaaaaaoqyfhwqbu763ifnjgilliobkopt7rot5q55amksr5spbdi5s573q"

MODEL_DEFINITIONS = {
    # --------------------
    # OLLAMA (LOCAL)
    # --------------------
    "llama3": {
    "type": "ollama",
    "model": "llama3"
    },

    "llama3-8b": {
        "type": "ollama",
        "model": "llama3:8b"
    },

    "llama3.2": {
        "type": "ollama",
        "model": "llama3.2:latest"
    },

    "qwen2.5": {
        "type": "ollama",
        "model": "qwen2.5:latest"
    },

    "llava": {
        "type": "ollama",
        "model": "llava:latest"
    },
    
    # "mistral": {"type": "ollama", "model": "mistral"}


    # --------------------
    # COHERE PUBLIC API
    # --------------------
    "command-r": {"type": "cohere_public", "model": "command-r"},
    "command-r-plus": {"type": "cohere_public", "model": "command-r-plus"},

    # --------------------
    # OCI – COHERE (Command-A)
    # --------------------
    "command-a": {
        "type": "oci_chat",
        "provider": "cohere",
        "model_id": "ocid1.generativeaimodel.oc1.us-chicago-1.amaaaaaask7dceyapnibwg42qjhwaxrlqfpreueirtwghiwvv2whsnwmnlva",
    },
    "command-a-03-2025": {
        "type": "oci_chat",
        "provider": "cohere",
        "model_id": "ocid1.generativeaimodel.oc1.us-chicago-1.amaaaaaask7dceyapnibwg42qjhwaxrlqfpreueirtwghiwvv2whsnwmnlva",
    },
}


def get_model(model_name: str):
    """
    Returns a model adapter instance.

    Behavior:
    1. If model_name is defined in MODEL_DEFINITIONS, use that mapping.
    2. If model_name contains ':' (e.g. 'llama3:8b' or 'qwen2.5:latest'),
       treat it as a direct Ollama model identifier and return OllamaModel(model_name).
    3. Otherwise raise a clear ValueError.
    """
    # 1) registered mapping
    if model_name in MODEL_DEFINITIONS:
        cfg = MODEL_DEFINITIONS[model_name]

        if cfg["type"] == "ollama":
            return OllamaModel(cfg["model"])

        if cfg["type"] == "cohere_public":
            return CohereModel(cfg["model"])

        if cfg["type"] == "oci_chat":
            return OCIChatModel(
                model_id=cfg["model_id"],
                provider=cfg["provider"],
                compartment_id=OCI_COMPARTMENT_ID,
                endpoint=OCI_ENDPOINT,
                config_path=OCI_CONFIG_PATH,
            )

        raise ValueError(f"Invalid model type for registered model: {model_name}")

    # 2) accept direct Ollama model identifiers (common form: "model:tag")
    if ":" in model_name:
        # treat as Ollama locally served model id
        return OllamaModel(model_name)

    # 3) helpful error
    available = ", ".join(sorted(list(MODEL_DEFINITIONS.keys())))
    raise ValueError(
        f"Model not registered: {model_name}. "
        f"Known aliases: {available}. "
        f"Or pass a direct Ollama model id like 'llama3:8b'."
    )
