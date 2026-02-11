import asyncio
import logging
from pathlib import Path
from typing import Annotated, Optional

from fastapi import Depends
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.llms.google_genai import GoogleGenAI

from app.core.exceptions import ConfigurationError, ExternalDependencyError, TechnicalError
from app.services.settings_service import SettingsService, get_settings_service

logger = logging.getLogger(__name__)


class PromptService:
    """
    Service responsible for prompt optimization using LLM.
    Handles loading templates, managing LLM clients, and executing chat-based optimization.
    """

    # Class-level cache for the prompt template
    _CACHED_OPTIMIZER_PROMPT: Optional[str] = None
    _load_lock = asyncio.Lock()

    def __init__(self, settings_service: SettingsService):
        self.settings_service = settings_service

    async def _get_optimizer_prompt(self) -> str:
        """
        Loads the optimizer prompt from an external markdown file.
        Uses a thread pool for non-blocking file IO and caches the result.
        """
        if PromptService._CACHED_OPTIMIZER_PROMPT is not None:
            return PromptService._CACHED_OPTIMIZER_PROMPT

        async with self._load_lock:
            # Double check after lock acquisition
            if PromptService._CACHED_OPTIMIZER_PROMPT is not None:
                return PromptService._CACHED_OPTIMIZER_PROMPT

            try:
                current_dir = Path(__file__).parent
                prompt_path = current_dir.parent / "prompts" / "optimizer_prompt.md"

                # Offload blocking IO to a thread pool
                def read_file():
                    if not prompt_path.exists():
                        raise FileNotFoundError(f"Prompt file not found at {prompt_path}")
                    with open(prompt_path, "r", encoding="utf-8") as f:
                        return f.read()

                content = await asyncio.to_thread(read_file)
                PromptService._CACHED_OPTIMIZER_PROMPT = content
                logger.info(f"Loaded optimizer prompt from {prompt_path}")
                return content

            except Exception as e:
                logger.error(f"Failed to load optimizer prompt: {e}", exc_info=True)
                raise TechnicalError(f"Could not load system prompt: {e}")

    async def _get_llm_client(self) -> GoogleGenAI:
        """
        Initializes and returns the GoogleGenAI client based on current settings.
        """
        api_key = await self.settings_service.get_value("gemini_api_key")
        if not api_key:
            raise ConfigurationError("GEMINI_API_KEY is not set")

        model_name = await self.settings_service.get_value("gemini_chat_model")
        if not model_name:
            raise ConfigurationError("gemini_chat_model is not configured in settings")

        # Normalize model name for LlamaIndex
        if not model_name.startswith("models/"):
            model_name = f"models/{model_name}"

        return GoogleGenAI(model=model_name, api_key=api_key)

    async def optimize_instruction(self, user_input: str) -> str:
        """
        Optimizes a user instruction using Gemini AI.
        Splits the template into system and user contexts for better performance via Chat API.
        """
        # Input validation
        if not user_input or not user_input.strip():
            raise TechnicalError("user_input cannot be empty")

        # Security: Cap input length to prevent token abuse
        MAX_INPUT_LENGTH = 10000
        if len(user_input) > MAX_INPUT_LENGTH:
            logger.warning(f"Input truncated from {len(user_input)} to {MAX_INPUT_LENGTH} chars")
            user_input = user_input[:MAX_INPUT_LENGTH]

        try:
            # 1. Load prompt (async/safe)
            full_template = await self._get_optimizer_prompt()

            # 2. Split into System/User for Chat API
            # The template has a marker "# INPUT". Everything before is System Knowledge.
            split_marker = "# INPUT"
            if split_marker in full_template:
                parts = full_template.split(split_marker)
                system_content = parts[0].strip()
                # The second part contains the input placeholder instructions
                user_content_template = parts[1].strip()
            else:
                # Fallback if marker missing
                logger.warning("Optimizer prompt missing '# INPUT' marker. Using full context as system.")
                system_content = full_template
                user_content_template = "The following is the prompt you will improve:\n\n{user_input}"

            # 3. Initialize LLM (non-blocking settings)
            llm = await self._get_llm_client()

            # 4. Prepare Messages
            messages = [
                ChatMessage(role=MessageRole.SYSTEM, content=system_content),
                ChatMessage(role=MessageRole.USER, content=user_content_template.replace("{user_input}", user_input)),
            ]

            # 5. Call Gemini (Chat Mode)
            response = await llm.achat(messages)
            return response.message.content.strip()

        except ConfigurationError:
            raise
        except Exception as e:
            logger.error(f"Prompt optimization failed: {e}", exc_info=True)
            if "API" in str(e) or "quota" in str(e).lower():
                raise ExternalDependencyError(f"Gemini API Error: {e}")
            else:
                raise TechnicalError(f"Failed to optimize instruction: {e}")


async def get_prompt_service(
    settings_service: Annotated[SettingsService, Depends(get_settings_service)],
) -> PromptService:
    """Dependency for getting PromptService instance."""
    return PromptService(settings_service)
