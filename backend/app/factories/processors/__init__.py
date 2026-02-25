"""
Processors package initialization.
"""

from app.factories.processors.base import FileProcessor, ProcessedDocument
from app.factories.processors.csv_processor import CsvProcessor
from app.factories.processors.office_processor import OfficeProcessor
from app.factories.processors.pdf_processor import PdfProcessor
from app.factories.processors.text_processor import TextProcessor

__all__ = [
    "FileProcessor",
    "ProcessedDocument",
    "CsvProcessor",
    "PdfProcessor",
    "OfficeProcessor",
    "TextProcessor",
]
