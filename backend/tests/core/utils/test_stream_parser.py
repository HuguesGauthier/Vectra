import pytest
import json
from app.core.utils.stream_parser import StreamBlockParser, StreamEvent


def test_stream_parser_happy_path():
    parser = StreamBlockParser()
    chunks = ["Hello ", ":::table\n", '{"key": "value"}', "\n:::", " world"]

    events = []
    for chunk in chunks:
        events.extend(list(parser.feed(chunk)))
    events.extend(list(parser.flush()))

    # Expected:
    # 'H', 'e', 'l', 'l', 'o', ' ' (tokens)
    # [:::table swallowed]
    # {"key": "value"} (block)
    # ' ', 'w', 'o', 'r', 'l', 'd' (tokens)

    # 6 "Hello " chars + 1 block + 6 " world" chars = 13 events
    assert len(events) == 13

    assert events[0].type == "token"
    assert events[0].content == "H"  # Wait, my parser yields char by char if not in block?
    # Actually, in NORMAL state:
    # 'H', 'e', 'l', 'l', 'o', ' ' are yielded as individual tokens.

    # Let's adjust the test to check combined content if needed,
    # or just check that we get a block event.

    tokens = [e.content for e in events if e.type == "token"]
    blocks = [e.content for e in events if e.type == "block"]

    assert "".join(tokens) == "Hello  world"
    assert len(blocks) == 1
    assert blocks[0] == {"key": "value"}


def test_stream_parser_fragmented_tag():
    parser = StreamBlockParser()
    # Heavily fragmented :::table
    chunks = [":", ":", ":", "t", "a", "b", "l", "e", '{"x":1}', ":", ":", ":"]

    events = []
    for chunk in chunks:
        events.extend(list(parser.feed(chunk)))
    events.extend(list(parser.flush()))

    blocks = [e.content for e in events if e.type == "block"]
    assert len(blocks) == 1
    assert blocks[0] == {"x": 1}
    assert "".join([e.content for e in events if e.type == "token"]) == ""


def test_stream_parser_multiple_blocks():
    parser = StreamBlockParser()
    stream = 'Text :::table {"id": 1} ::: More :::table {"id": 2} ::: End'

    events = []
    for char in stream:
        events.extend(list(parser.feed(char)))
    events.extend(list(parser.flush()))

    blocks = [e.content for e in events if e.type == "block"]
    assert len(blocks) == 2
    assert blocks[0] == {"id": 1}
    assert blocks[1] == {"id": 2}
    assert "Text " in "".join([e.content for e in events if e.type == "token"])
    assert " More " in "".join([e.content for e in events if e.type == "token"])
    assert " End" in "".join([e.content for e in events if e.type == "token"])


def test_stream_parser_malformed_json_fallback():
    parser = StreamBlockParser()
    # :::table {invalid} :::
    chunks = [":::table ", "{invalid}", " :::"]

    events = []
    for chunk in chunks:
        events.extend(list(parser.feed(chunk)))
    events.extend(list(parser.flush()))

    # Should fallback to tokens
    full_text = "".join([e.content for e in events if e.type == "token"])
    assert ":::table {invalid} :::" in full_text
    assert len([e for e in events if e.type == "block"]) == 0


def test_stream_parser_incomplete_block():
    parser = StreamBlockParser()
    # Stream ends before closing :::
    chunks = [":::table ", '{"valid": true}']

    events = []
    for chunk in chunks:
        events.extend(list(parser.feed(chunk)))
    events.extend(list(parser.flush()))

    full_text = "".join([e.content for e in events if e.type == "token"])
    assert ':::table {"valid": true}' in full_text


def test_stream_parser_custom_tags():
    parser = StreamBlockParser(start_tag="[[[DATA", end_tag="]]]")
    stream = 'Before [[[DATA {"test": 123} ]]] After'

    events = []
    for char in stream:
        events.extend(list(parser.feed(char)))
    events.extend(list(parser.flush()))

    blocks = [e.content for e in events if e.type == "block"]
    assert len(blocks) == 1
    assert blocks[0] == {"test": 123}
    assert "Before " in "".join([e.content for e in events if e.type == "token"])
    assert " After" in "".join([e.content for e in events if e.type == "token"])
