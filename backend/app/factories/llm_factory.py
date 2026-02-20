import json
import logging
from typing import Any, Dict, Optional

from llama_index.core.llms import LLM

from app.core.exceptions import ConfigurationError

PROVIDER_GEMINI = "gemini"
PROVIDER_OPENAI = "openai"
PROVIDER_MISTRAL = "mistral"
PROVIDER_ANTHROPIC = "anthropic"
PROVIDER_OLLAMA = "ollama"
DEFAULT_TEMP = 0.7

logger = logging.getLogger(__name__)


class LLMFactory:
    """Factory to create LLM instances."""

    @staticmethod
    def create_llm(
        provider: str,
        model_name: str,
        api_key: str,
        temperature: float = DEFAULT_TEMP,
        top_k: Optional[int] = None,
        output_class: Any = None,
        base_url: Optional[str] = None,
    ) -> Any:
        provider_clean = provider.lower().strip()

        # P0 FIX: key is not required for local
        if not api_key and provider_clean not in ["local", "ollama"]:
            raise ConfigurationError(f"API Key missing for provider {provider}")

        if not model_name and provider_clean not in ["local"]:
            raise ConfigurationError(f"No model configured for provider '{provider}'. Check the settings.")

        llm = None

        if provider_clean == PROVIDER_GEMINI:
            from llama_index.llms.google_genai import GoogleGenAI

            full_model_name = f"models/{model_name}" if not model_name.startswith("models/") else model_name
            # top_k is supported by GoogleGenAI
            llm = GoogleGenAI(model=full_model_name, api_key=api_key, temperature=temperature, top_k=top_k)
        elif provider_clean == PROVIDER_OPENAI:
            from llama_index.llms.openai import OpenAI

            # FIX: Enable stream_options to receive token usage in streaming mode
            # OpenAI doesn't use top_k (it uses top_p)
            llm = OpenAI(
                model=model_name,
                api_key=api_key,
                temperature=temperature,
                additional_kwargs={"stream_options": {"include_usage": True}},
            )
        elif provider_clean == PROVIDER_MISTRAL:
            from llama_index.llms.mistralai import MistralAI

            # MistralAI doesn't directly expose top_k in LLM class, but might support it in additional_kwargs
            # For now keep it simple to match existing contract
            llm = MistralAI(model=model_name, api_key=api_key, temperature=temperature)
        elif provider_clean == PROVIDER_ANTHROPIC:
            from llama_index.llms.anthropic import Anthropic

            # Anthropic supports top_k and temperature
            llm = Anthropic(model=model_name, api_key=api_key, temperature=temperature, top_k=top_k)
        elif provider_clean == PROVIDER_OLLAMA:
            from llama_index.llms.ollama import Ollama

            # P0: Prioritize passed base_url, then handle legacy api_key-as-url fallback
            final_base_url = base_url
            if not final_base_url:
                final_base_url = api_key if api_key and "http" in api_key else "http://localhost:11434"
                logger.warning(f"Ollama base_url missing in factory call, falling back to: {final_base_url}")

            # Top K supported via additional_kwargs in llama-index Ollama
            additional_kwargs = {}
            if top_k is not None:
                additional_kwargs["top_k"] = top_k

            llm = Ollama(
                model=model_name,
                base_url=final_base_url,
                temperature=temperature,
                additional_kwargs=additional_kwargs,
                request_timeout=360.0,
            )
        elif provider_clean == "local":
            # Support for Local LLMs (LM Studio, Ollama, etc.) via OpenAILike
            from llama_index.llms.openai_like import OpenAILike

            # P0: Use base_url if provided, default to standard LM Studio port if not
            final_api_base = base_url or "http://localhost:1234/v1"
            llm = OpenAILike(
                model=model_name or "local-model",
                api_key=api_key or "not-needed",
                api_base=final_api_base,
                temperature=temperature,
                is_chat_model=True,
            )
        else:
            raise ConfigurationError(f"Unsupported LLM provider: {provider}")

        if output_class:
            return llm.as_structured_llm(output_class)

        return llm
