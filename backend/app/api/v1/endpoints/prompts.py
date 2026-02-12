import logging
import time
from typing import Annotated, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.exceptions import FunctionalError, TechnicalError
from app.core.security import get_current_user
from app.models.user import User
from app.services.prompt_service import PromptService, get_prompt_service

# Initialize logger
logger = logging.getLogger(__name__)

router = APIRouter()


class OptimizeRequest(BaseModel):
    """
    Schema for prompt optimization request.

    Attributes:
        instruction: The user instruction to optimize.
        connector_ids: List of connector IDs to provide context for optimization.
    """

    instruction: str = Field(..., min_length=1, max_length=5000, description="The user instruction to optimize")
    connector_ids: List[str] = Field(
        default_factory=list, description="List of connector IDs to provide context for optimization"
    )


class OptimizeResponse(BaseModel):
    """
    Schema for prompt optimization response.

    Attributes:
        optimized_instruction: The optimized version of the instruction.
    """

    optimized_instruction: str = Field(..., description="The optimized version of the instruction")


@router.post("/optimize", response_model=OptimizeResponse)
async def optimize_prompt(
    request: OptimizeRequest,
    service: Annotated[PromptService, Depends(get_prompt_service)],
    current_user: Annotated[User, Depends(get_current_user)],  # 🛡️ SECURITY: Require Auth
) -> OptimizeResponse:
    """
    Optimizes a user instruction using LLM and context from connectors.

    Args:
        request: The optimization request containing instruction and connector IDs.
        service: The prompt service instance.
        current_user: The currently authenticated user.

    Returns:
        OptimizeResponse: The response containing the optimized instruction.

    Raises:
        FunctionalError: If there's a functional error during optimization.
        TechnicalError: If there's a technical error during optimization.
    """
    start_time = time.time()
    func_name = "optimize_prompt"
    logger.info(
        "START | %s | User: %s | Params: {'connector_count': %d}",
        func_name,
        current_user.email,
        len(request.connector_ids),
    )

    try:
        # Note: connector_ids currently unused in service but kept for future RAG context injection
        optimized_text = await service.optimize_instruction(request.instruction)

        elapsed = round((time.time() - start_time) * 1000, 2)
        logger.info("FINISH | %s | Status: Success | Duration: %sms", func_name, elapsed)

        return OptimizeResponse(optimized_instruction=optimized_text)

    except (FunctionalError, TechnicalError) as e:
        logger.error("❌ FAIL | %s | Known Error: %s (Code: %s)", func_name, e.message, e.error_code, exc_info=True)
        raise e
    except Exception as e:
        logger.error("❌ FAIL | %s | Error: %s", func_name, str(e), exc_info=True)
        raise TechnicalError(message=f"Failed to optimize prompt: {e}", error_code="PROMPT_OPTIMIZATION_FAILED")
