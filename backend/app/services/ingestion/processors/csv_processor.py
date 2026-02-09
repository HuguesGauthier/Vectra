import csv
import logging
from typing import Dict, Iterator, Optional

logger = logging.getLogger(__name__)


class CsvStreamProcessor:
    """
    Stream processor for CSV files.
    Reads CSV files line by line (generator) to avoid loading the entire file into memory.
    """

    def __init__(self, chunk_size: int = 100):
        self.chunk_size = chunk_size

    def iter_records(self, file_path: str, renaming_map: Optional[Dict[str, str]] = None) -> Iterator[Dict]:
        """
        Yields records from the CSV file as dictionaries.
        args:
            file_path: Absolute path to the CSV file.
            renaming_map: Optional dictionary to map CSV headers to new names.
        """
        if renaming_map is None:
            renaming_map = {}

        try:
            # open with utf-8-sig to handle potentially BOM
            with open(file_path, mode="r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)

                for row in reader:
                    # Apply renaming if provided
                    if renaming_map:
                        normalized_row = {}
                        for k, v in row.items():
                            # Handle potential None keys (parsing errors)
                            if k is None:
                                continue

                            key_to_use = renaming_map.get(k, k)
                            if key_to_use:
                                normalized_row[key_to_use] = v
                        yield normalized_row
                    else:
                        yield {k: v for k, v in row.items() if k is not None}

        except FileNotFoundError:
            logger.error(f"CSV File not found: {file_path}")
            raise
        except Exception as e:
            logger.error(f"Error reading CSV {file_path}: {e}")
            raise
