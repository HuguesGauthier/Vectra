import logging
from abc import ABC, abstractmethod
from typing import AsyncGenerator

from app.services.chat.types import ChatContext


class ChatProcessorError(Exception):
    """
    Base exception for all chat processor errors.

    Attributes:
        original_error (Exception | None): The underlying cause, if any.
    """

    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message)
        self.original_error = original_error


class BaseChatProcessor(ABC):
    """
    Abstract base class for all chat processors.

    Enforces a common interface and provides standard logging capabilities.

    Attributes:
        logger (logging.Logger): Class-specific logger instance.
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def process(self, ctx: ChatContext) -> AsyncGenerator[str, None]:
        """
        Process the chat context and yield streaming responses.

        Args:
            ctx (ChatContext): The current chat session context containing state and dependencies.

        Yields:
            str: JSON-formatted string chunks representing the streaming response.

        Raises:
            ChatProcessorError: If critical processing failure occurs.
        """
        pass
