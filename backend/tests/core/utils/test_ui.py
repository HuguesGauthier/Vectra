import pytest
from app.core.utils.ui import calculate_contrast_text_color


def test_calculate_contrast_text_color_hex():
    # Happy Path: Hex (6 digits)
    assert calculate_contrast_text_color("#FFFFFF") == "black"  # White background -> black text
    assert calculate_contrast_text_color("#000000") == "white"  # Black background -> white text
    assert calculate_contrast_text_color("#7FFFFF") == "black"  # Light blue -> black text
    assert calculate_contrast_text_color("#00007F") == "white"  # Dark blue -> white text

    # Happy Path: Hex (3 digits)
    assert calculate_contrast_text_color("#FFF") == "black"
    assert calculate_contrast_text_color("#000") == "white"

    # Hex without # prefix
    assert calculate_contrast_text_color("FFFFFF") == "black"
    assert calculate_contrast_text_color("000000") == "white"


def test_calculate_contrast_text_color_rgb():
    # Happy Path: RGB
    assert calculate_contrast_text_color("rgb(255, 255, 255)") == "black"
    assert calculate_contrast_text_color("rgb(0, 0, 0)") == "white"
    assert calculate_contrast_text_color("rgb(128, 128, 128)") == "black"  # Brightness ~0.502 -> black


def test_calculate_contrast_text_color_edge_cases():
    # Edge Cases & Worst Case
    assert calculate_contrast_text_color("") == "white"
    assert calculate_contrast_text_color(None) == "white"
    assert calculate_contrast_text_color(123) == "white"  # Non-string
    assert calculate_contrast_text_color("#ZZZZZZ") == "white"  # Invalid hex
    assert calculate_contrast_text_color("rgb(abc, def, ghi)") == "white"  # Invalid RGB
    assert calculate_contrast_text_color("random string") == "white"
