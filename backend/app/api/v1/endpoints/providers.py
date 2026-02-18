from typing import Annotated, Any, List

from fastapi import APIRouter, Depends

from app.core.model_catalog import SUPPORTED_CHAT_MODELS
from app.schemas.provider import ProviderInfo
from app.services.settings_service import SettingsService, get_settings_service

router = APIRouter()


@router.get("/", response_model=List[ProviderInfo])
async def get_providers(
    service: Annotated[SettingsService, Depends(get_settings_service)],
) -> Any:
    """
    Retrieve the list of supported providers and their configuration status.
    This allows the frontend to dynamically display available options.
    """
    providers = []

    # Helper to check if key exists (in DB or Env via SettingsService fallback)
    async def is_configured(key: str) -> bool:
        val = await service.get_value(key)
        if val is None:
            return False
        val = str(val).strip()
        # Consider empty or single asterisks (masked) as not configured
        return bool(val and val != "" and not all(c == "*" for c in val))

    # --- Embedding Providers ---
    # Ollama
    providers.append(
        ProviderInfo(
            id="ollama",
            name="Ollama (Local)",
            type="embedding",
            description="GPU Accelerated & Efficient",
            configured=await is_configured("ollama_base_url") or True,  # Default is configured (localhost)
            is_active=True,
        )
    )

    # Gemini
    providers.append(
        ProviderInfo(
            id="gemini",
            name="Google Gemini",
            type="embedding",
            description="Google DeepMind",
            configured=await is_configured("gemini_api_key"),
            is_active=True,
        )
    )

    # OpenAI
    providers.append(
        ProviderInfo(
            id="openai",
            name="OpenAI",
            type="embedding",
            description="Standard Industry Model",
            configured=await is_configured("openai_api_key"),
            is_active=True,
        )
    )

    # --- Chat Providers ---
    # Ollama (Local)
    providers.append(
        ProviderInfo(
            id="ollama",
            name="Ollama (Local)",
            type="chat",
            description="Run models locally",
            configured=True,
            is_active=True,
        )
    )

    # Gemini
    providers.append(
        ProviderInfo(
            id="gemini",
            name="Google Gemini",
            type="chat",
            description="Google DeepMind",
            configured=await is_configured("gemini_api_key"),
            is_active=True,
            supported_models=SUPPORTED_CHAT_MODELS.get("gemini", []),
        )
    )

    # OpenAI
    providers.append(
        ProviderInfo(
            id="openai",
            name="OpenAI",
            type="chat",
            description="ChatGPT",
            configured=await is_configured("openai_api_key"),
            is_active=True,
            supported_models=SUPPORTED_CHAT_MODELS.get("openai", []),
        )
    )

    # Mistral
    providers.append(
        ProviderInfo(
            id="mistral",
            name="Mistral AI",
            type="chat",
            description="European Champion",
            configured=await is_configured("mistral_api_key"),
            is_active=True,
            supported_models=SUPPORTED_CHAT_MODELS.get("mistral", []),
        )
    )

    # --- Rerank Providers ---

    # Local (FastEmbed)
    providers.append(
        ProviderInfo(
            id="local",
            name="Local Reranker (FastEmbed)",
            type="rerank",
            description="Private & Efficient (CPU)",
            configured=True,  # FastEmbed is built-in
            is_active=True,
        )
    )

    # Cohere
    providers.append(
        ProviderInfo(
            id="cohere",
            name="Cohere",
            type="rerank",
            description="Industry leader in Reranking",
            configured=await is_configured("cohere_api_key"),
            is_active=True,
        )
    )

    return providers
