"""
Services package.
"""

# Expose modules to fix legacy import patterns or pytest collection issues
from . import assistant_service, chat_service

# Add others if needed, but this should fix the immediate AttributeError
