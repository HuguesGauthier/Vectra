from abc import ABC, abstractmethod
from typing import AsyncGenerator

from app.core.rag.types import PipelineContext, PipelineEvent


class BaseProcessor(ABC):
    """Abstract Base Class for all pipeline processors."""

    @abstractmethod
    async def process(self, ctx: PipelineContext) -> AsyncGenerator[PipelineEvent, None]:
        pass
