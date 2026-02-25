import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# WCAG Standards: Relative luminance coefficients (Rec. 709)
LUMINANCE_R = 0.2126
LUMINANCE_G = 0.7152
LUMINANCE_B = 0.0722
CONTRAST_THRESHOLD = 0.5  # Mid-point (normalized 0-1)

HEX_REGEX = re.compile(r"^#?([a-f0-9]{3}|[a-f0-9]{6})$", re.IGNORECASE)
RGB_REGEX = re.compile(r"^rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)$", re.IGNORECASE)


def calculate_contrast_text_color(bg_color: Optional[str]) -> str:
    """
    Determines optimized text color (black/white) for contrast based on background.
    Supports Hex (#FFF, #FFFFFF) and RGB (rgb(255,255,255)) formats.
    """
    if not bg_color or not isinstance(bg_color, str):
        return "white"

    color = bg_color.strip().lower()
    r, g, b = 0, 0, 0

    try:
        # 1. Hex Parsing
        hex_match = HEX_REGEX.match(color)
        if hex_match:
            hex_val = color.lstrip("#")
            if len(hex_val) == 3:
                hex_val = "".join([c * 2 for c in hex_val])
            r, g, b = int(hex_val[0:2], 16), int(hex_val[2:4], 16), int(hex_val[4:6], 16)

        # 2. RGB Parsing
        elif color.startswith("rgb"):
            rgb_match = RGB_REGEX.match(color)
            if rgb_match:
                r, g, b = map(int, rgb_match.groups())
            else:
                logger.warning(f"Invalid RGB format: '{color}'. Defaulting to white.")
                return "white"

        else:
            logger.debug(f"Unsupported color format '{color}'. Defaulting to white.")
            return "white"

        # 3. Relative Luminance Calculation (0.0 to 1.0)
        # Normalized to 0-1 range based on Rec. 709
        brightness = (r * LUMINANCE_R + g * LUMINANCE_G + b * LUMINANCE_B) / 255

        return "black" if brightness > CONTRAST_THRESHOLD else "white"

    except Exception as e:
        logger.error(f"Unexpected error calculating contrast for '{bg_color}': {e}")
        return "white"
