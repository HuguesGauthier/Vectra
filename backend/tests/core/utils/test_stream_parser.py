import pytest
import json
from app.core.utils.stream_parser import StreamBlockParser, StreamEvent

class TestStreamBlockParser:
    def test_normal_text_flow(self):
        """Should yield tokens immediately for normal text."""
        parser = StreamBlockParser()
        events = list(parser.feed("Hello World"))
        
        assert len(events) == 11
        assert events[0].type == "token"
        assert events[0].content == "H"
        
    def test_complete_block_parsing(self):
        """Should capture a complete block and yield it as an event."""
        parser = StreamBlockParser()
        json_data = {"key": "value"}
        block_str = f":::table {json.dumps(json_data)} :::"
        
        events = list(parser.feed(block_str))
        
        # Should yield 0 tokens (swallowed) and 1 block
        assert len(events) == 1
        assert events[0].type == "block"
        assert events[0].content == json_data
        
    def test_fragmented_tags(self):
        """Should handle split tags correctly."""
        parser = StreamBlockParser()
        chunks = [":", ":", ":", "t", "able", " ", "{}", " ", ":", ":", ":"]
        
        events = []
        for chunk in chunks:
            events.extend(parser.feed(chunk))
            
        assert len(events) == 1
        assert events[0].type == "block"
        assert events[0].content == {}
        
    def test_mixed_content(self):
        """Should handle text before and after block."""
        parser = StreamBlockParser()
        text = "Start :::table {} ::: End"
        
        events = list(parser.feed(text))
        
        # Expectations:
        # "Start " -> tokens
        # ":::table {} :::" -> block
        # " End" -> tokens
        
        types = [e.type for e in events]
        assert "block" in types
        assert types.count("token") == len("Start  End")
        
    def test_invalid_tag_flush(self):
        """Should flush buffer if it looked like a tag but wasn't."""
        parser = StreamBlockParser()
        events = list(parser.feed("::foo"))
        
        # Should yield tokens: ":", ":", "f", "o", "o"
        assert len(events) == 5
        assert "".join([e.content for e in events]) == "::foo"
        
    def test_unclosed_block_flush(self):
        """Should flush raw text if block is never closed."""
        parser = StreamBlockParser()
        # Feed start of block
        list(parser.feed(":::table {data}"))
        
        # Flush
        events = list(parser.flush())
        
        # Should contain the raw swallowed headers
        content = "".join([e.content for e in events])
        assert ":::table {data}" in content
