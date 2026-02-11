import json
import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, Generator, Optional

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

    START_TAG = ":::table"
    END_TAG = ":::"
    
    def __init__(self):
        self.state = StreamParserState.NORMAL
        self.buffer = ""
        self.block_buffer = ""
        
    def feed(self, chunk: str) -> Generator[StreamEvent, None, None]:
        """
        Process a new chunk of text and yield events.
        """
        # We process character by character to be absolutely robust against
        # widely fragmented tokens (e.g. ":", ":", ":", "t", "a", "b", "l", "e")
        # Optimization: We could process by chunk if we are careful, but char-by-char 
        # is safer and fast enough for LLM stream speeds.
        
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
            
        # If we were inside a block but it never closed, we treat it as failed
        # and dump the raw text.
        if self.state == StreamParserState.INSIDE_BLOCK and self.block_buffer:
            logger.warning("Stream ended while inside a block. Dumping raw block buffer.")
            # We recreate the start tag because we swallowed it when entering the block
            yield StreamEvent(type="token", content=self.START_TAG + self.block_buffer)
            self.block_buffer = ""
            self.state = StreamParserState.NORMAL

    def _process_char(self, char: str) -> Generator[StreamEvent, None, None]:
        if self.state == StreamParserState.NORMAL:
            if char == ":":
                self.state = StreamParserState.BUFFERING_TAG
                self.buffer += char
            else:
                yield StreamEvent(type="token", content=char)
                
        elif self.state == StreamParserState.BUFFERING_TAG:
            self.buffer += char
            
            # Check if we assume it's a start tag
            if self.START_TAG.startswith(self.buffer):
                if self.buffer == self.START_TAG:
                    # Transition to Block Mode
                    self.state = StreamParserState.INSIDE_BLOCK
                    self.buffer = ""  # Clear buffer (swallow tag)
                    self.block_buffer = ""
            else:
                # It's not our tag (e.g. "::foo"), flush buffer and return to normal
                yield StreamEvent(type="token", content=self.buffer)
                self.buffer = ""
                self.state = StreamParserState.NORMAL
                
        elif self.state == StreamParserState.INSIDE_BLOCK:
            self.block_buffer += char
            
            # Check for end tag
            if self.block_buffer.endswith(self.END_TAG):
                # Try to parse content
                # block_buffer is ".... content :::"
                content_str = self.block_buffer[: -len(self.END_TAG)].strip()
                
                # Check if it's REALLY the end (heuristic for json: balanced braces?) 
                # For now, simplistic check: ":::" ends the block.
                # If content is valid JSON, we emit block.
                try:
                    if content_str:
                        data = json.loads(content_str)
                        yield StreamEvent(type="block", content=data)
                    else:
                        logger.warning("Empty block content found.")
                        
                    self.state = StreamParserState.NORMAL
                    self.block_buffer = ""
                    
                except json.JSONDecodeError:
                    # Maybe it wasn't the end? Or malformed?
                    # If we simply encountered ":::" inside a string/json, we might be premature.
                    # BUT, ":::" is a reserved protocol delimiter. We assume it's the end.
                    # If parse fails, we fallback to text dump.
                    logger.warning(f"Failed to parse JSON block: {content_str[:50]}...")
                    # Fallback: Treat as text
                    logger.info("Falling back to text emission for failed block.")
                    # Reconstruct what we swallowed
                    full_text = self.START_TAG + self.block_buffer
                    yield StreamEvent(type="token", content=full_text)
                    
                    self.state = StreamParserState.NORMAL
                    self.block_buffer = ""
