import csv
import os
import sys
from unittest.mock import MagicMock
import pytest

# Mock dependencies globally for test collection
sys.modules["pyodbc"] = MagicMock()
sys.modules["vanna"] = MagicMock()
sys.modules["vanna.base"] = MagicMock()

from app.services.ingestion.processors.csv_processor import CsvStreamProcessor


@pytest.fixture
def processor():
    return CsvStreamProcessor()


def test_iter_records_basic(processor, tmp_path):
    """Happy Path: Reads a basic CSV file."""
    csv_file = tmp_path / "test.csv"
    content = "id,name\n1,Alice\n2,Bob"
    csv_file.write_text(content)

    records = list(processor.iter_records(str(csv_file)))
    assert len(records) == 2
    assert records[0] == {"id": "1", "name": "Alice"}
    assert records[1] == {"id": "2", "name": "Bob"}


def test_iter_records_with_renaming(processor, tmp_path):
    """Happy Path: Applies renaming map correctly."""
    csv_file = tmp_path / "test_rename.csv"
    content = "old_id,old_name\n1,Alice"
    csv_file.write_text(content)

    renaming_map = {"old_id": "id", "old_name": "full_name"}
    records = list(processor.iter_records(str(csv_file), renaming_map=renaming_map))

    assert len(records) == 1
    assert records[0] == {"id": "1", "full_name": "Alice"}


def test_iter_records_utf8_bom(processor, tmp_path):
    """Happy Path: Handles UTF-8 with BOM."""
    csv_file = tmp_path / "test_bom.csv"
    # UTF-8 BOM is \xef\xbb\xbf
    content = b"\xef\xbb\xbfid,name\n1,Alice"
    csv_file.write_bytes(content)

    records = list(processor.iter_records(str(csv_file)))
    assert len(records) == 1
    assert records[0] == {"id": "1", "name": "Alice"}


def test_iter_records_extra_columns(processor, tmp_path):
    """Worst Case: Handles rows with more columns than headers (None keys)."""
    csv_file = tmp_path / "test_extra.csv"
    # Row 2 has an extra comma
    content = "id,name\n1,Alice\n2,Bob,extra"
    csv_file.write_text(content)

    records = list(processor.iter_records(str(csv_file)))
    assert len(records) == 2
    # The extra column should be ignored (key is None in csv.DictReader)
    assert records[1] == {"id": "2", "name": "Bob"}


def test_iter_records_empty_file(processor, tmp_path):
    """Worst Case: Handles empty file."""
    csv_file = tmp_path / "empty.csv"
    csv_file.write_text("")

    records = list(processor.iter_records(str(csv_file)))
    assert len(records) == 0


def test_iter_records_file_not_found(processor):
    """Worst Case: Raises FileNotFoundError for missing path."""
    with pytest.raises(FileNotFoundError):
        list(processor.iter_records("non_existent.csv"))
