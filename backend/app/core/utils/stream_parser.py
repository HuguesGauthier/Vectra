import json
import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, Generator, Optional, Union

logger = logging.getLogger(__name__)


class StreamParserState(Enum):
    NORMAL = auto()
    BUFFERING_TAG = auto()
    INSIDE_BLOCK = auto()


@dataclass
class StreamEvent:
    type: str  # "token" or "block"
    content: Any  # str for token, dict for block


class StreamBlockParser:
    """
    Robust state-machine parser for extracting structured blocks (e.g. :::table ... :::)
    from a continuous text stream.

    Why: Regex on accumulating strings is O(N^2) and fragile with split tokens.
    This parser is O(N) and handles token fragmentation safely.
    """

    def __init__(self, start_tag: str = ":::table", end_tag: str = ":::"):
        self.state = StreamParserState.NORMAL
        self.buffer = ""
        self.block_buffer = ""
        self.start_tag = start_tag
        self.end_tag = end_tag

    def feed(self, chunk: Union[str, Any]) -> Generator[StreamEvent, None, None]:
        """
        Process a new chunk of text and yield events.
        """
        if not isinstance(chunk, str):
            if chunk is not None:
                logger.debug(f"StreamBlockParser received non-string chunk: {type(chunk)}")
            return

        for char in chunk:
            yield from self._process_char(char)

    def flush(self) -> Generator[StreamEvent, None, None]:
        """
        Flush any remaining buffer as text tokens.
        Call this when the stream ends.
        """
        if self.buffer:
            yield StreamEvent(type="token", content=self.buffer)
            self.buffer = ""

        # If we were inside a block but it never closed, treat as failed and dump raw text
        if self.state == StreamParserState.INSIDE_BLOCK and self.block_buffer:
            logger.warning("Stream ended while inside a block. Dumping raw block buffer.")
            # Reconstruct what was swallowed
            yield StreamEvent(type="token", content=self.start_tag + self.block_buffer)
            self.block_buffer = ""
            self.state = StreamParserState.NORMAL

    def _process_char(self, char: str) -> Generator[StreamEvent, None, None]:
        """Core state machine logic."""
        if self.state == StreamParserState.NORMAL:
            if char == self.start_tag[0]:
                self.state = StreamParserState.BUFFERING_TAG
                self.buffer += char
            else:
                yield StreamEvent(type="token", content=char)

        elif self.state == StreamParserState.BUFFERING_TAG:
            self.buffer += char

            # Check if this qualifies as the start of our tag
            if self.start_tag.startswith(self.buffer):
                if self.buffer == self.start_tag:
                    # Transition to Block Mode
                    self.state = StreamParserState.INSIDE_BLOCK
                    self.buffer = ""  # Swallow tag
                    self.block_buffer = ""
            else:
                # It's not our tag, flush and return to normal
                yield StreamEvent(type="token", content=self.buffer)
                self.buffer = ""
                self.state = StreamParserState.NORMAL

        elif self.state == StreamParserState.INSIDE_BLOCK:
            self.block_buffer += char

            # Check for end tag
            if self.block_buffer.endswith(self.end_tag):
                content_str = self.block_buffer[: -len(self.end_tag)].strip()

                try:
                    if content_str:
                        data = json.loads(content_str)
                        yield StreamEvent(type="block", content=data)
                    else:
                        logger.warning("Empty block content found.")

                    self.state = StreamParserState.NORMAL
                    self.block_buffer = ""

                except json.JSONDecodeError:
                    # simplistic check: ":::" ends the block.
                    # If parse fails, we fallback to text dump.
                    logger.warning(f"Failed to parse JSON block: {content_str[:50]}...")
                    full_text = self.start_tag + self.block_buffer
                    yield StreamEvent(type="token", content=full_text)

                    self.state = StreamParserState.NORMAL
                    self.block_buffer = ""
