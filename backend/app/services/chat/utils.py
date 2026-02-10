import json
from typing import Any, Dict, Optional

from llama_index.core.llms import LLM

from app.core.exceptions import ConfigurationError

PROVIDER_GEMINI = "gemini"
PROVIDER_OPENAI = "openai"
PROVIDER_MISTRAL = "mistral"
PROVIDER_OLLAMA = "ollama"
DEFAULT_TEMP = 0.7


class LLMFactory:
    """Factory to create LLM instances."""

    @staticmethod
    def create_llm(
        provider: str, model_name: str, api_key: str, temperature: float = DEFAULT_TEMP, output_class: Any = None
    ) -> Any:
        provider_clean = provider.lower().strip()

        # P0 FIX: key is not required for local
        if not api_key and provider_clean not in ["local", "ollama"]:
            raise ConfigurationError(f"API Key missing for provider {provider}")

        llm = None

        if provider_clean == PROVIDER_GEMINI:
            from llama_index.llms.google_genai import GoogleGenAI

            full_model_name = f"models/{model_name}" if not model_name.startswith("models/") else model_name
            llm = GoogleGenAI(model=full_model_name, api_key=api_key, temperature=temperature)
        elif provider_clean == PROVIDER_OPENAI:
            from llama_index.llms.openai import OpenAI

            # FIX: Enable stream_options to receive token usage in streaming mode
            llm = OpenAI(
                model=model_name,
                api_key=api_key,
                temperature=temperature,
                additional_kwargs={"stream_options": {"include_usage": True}},
            )
        elif provider_clean == PROVIDER_MISTRAL:
            from llama_index.llms.mistralai import MistralAI

            llm = MistralAI(model=model_name, api_key=api_key, temperature=temperature)
        elif provider_clean == PROVIDER_OLLAMA:
            from llama_index.llms.ollama import Ollama

            # For Ollama, api_key is typically not needed but we handle base_url via factory args if possible,
            # or rely on default/settings. Ideally, base_url should be passed or we assume "api_key" param holds URL if needed?
            # Actually, create_llm signature has api_key. We can misuse it or add kwargs.
            # But simpler: Settings usually hold the base_url, or we can treat 'api_key' as base_url for Ollama if user configures it there.
            # However, for now, let's assume standard local URL or valid one passed in settings.
            # We will use the api_key parameter to pass the Base URL for Ollama to keep signature simple.
            base_url = api_key if api_key and "http" in api_key else "http://localhost:11434"
            llm = Ollama(model=model_name, base_url=base_url, temperature=temperature, request_timeout=360.0)
        elif provider_clean == "local":
            # Support for Local LLMs (LM Studio, Ollama, etc.) via OpenAILike
            from llama_index.llms.openai_like import OpenAILike

            # Default to LM Studio port if not specified in env/settings, but usually handled by env.
            # We assume settings_service provides the base URL if needed, or we use default.
            # For now, simplistic implementation assuming standard local setup.
            llm = OpenAILike(
                model=model_name or "local-model",
                api_key=api_key or "not-needed",
                api_base="http://localhost:1234/v1",  # Standard LM Studio port
                temperature=temperature,
                is_chat_model=True,
            )
        else:
            raise ConfigurationError(f"Unsupported LLM provider: {provider}")

        if output_class:
            return llm.as_structured_llm(output_class)

        return llm


class EventFormatter:
    """Helper to format SSE events with centralized localization via PipelineRegistry."""

    @staticmethod
    def format(
        step_type: Any,
        status: Any,
        language: str,
        payload: Optional[Any] = None,
        duration: Optional[float] = None,
        label: Optional[str] = None,
    ) -> str:
        # P0 FIX: Ensure Enums are converted to strings/values for JSON
        step_val = step_type.value if hasattr(step_type, "value") else str(step_type)
        status_val = status.value if hasattr(status, "value") else str(status)

        # USER_REQUEST: Frontend handles I18n. Backend sends keys only.
        # We generally do NOT resolve labels here anymore.
        # But we respect explicit dynamic labels from callers (e.g. "Processing file X")
        final_label = label

        # If explicitly passed distinct "label" override, use it (dynamic info).
        # Otherwise send None so frontend uses generic I18n key.

        data = {"type": "step", "step_type": step_val, "status": status_val, "label": final_label}
        if payload is not None:
            data["payload"] = payload
        if duration is not None:
            data["duration"] = duration

        return json.dumps(data, default=str) + "\n"
