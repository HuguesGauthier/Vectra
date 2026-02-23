from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# --- Legacy/Existing Configs (Restored) ---
class IngestionStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class BaseIngestionConfig(BaseModel):
    """Base class for all ingestion configs"""

    model_config = ConfigDict(from_attributes=True)

    enabled: bool = True


class FileIngestionConfig(BaseModel):
    """
    Configuration for ingesting a specific file type.
    """

    model_config = ConfigDict(from_attributes=True)

    extensions: List[str] = ["*"]
    enabled: bool = True
    max_size_mb: int = 20
    path: Optional[str] = None


class FolderIngestionConfig(BaseModel):
    """
    Configuration for watching a folder.
    """

    model_config = ConfigDict(from_attributes=True)

    path: str
    recursive: bool = True
    patterns: List[str] = ["*"]


class SqlIngestionConfig(BaseModel):
    """
    Configuration for SQL Database.
    """

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    host: str
    port: int = 1433
    database: str
    user: str
    password: str
    db_schema: Optional[str] = Field("dbo", alias="schema", serialization_alias="schema")
    type: Optional[str] = "mssql"
    connection_string: Optional[str] = None
    views: List[str] = []


class IngestionConfig(BaseModel):
    """
    Global ingestion settings.
    """

    model_config = ConfigDict(from_attributes=True)

    batch_size: int = 50
    workers: int = 4
    chunk_size: int = 1024
    chunk_overlap: int = 200


# --- Smart Strategy Configs (New) ---


class ColumnType(str, Enum):
    SEMANTIC = "SEMANTIC"  # Embedding Source
    FILTER_EXACT = "FILTER_EXACT"  # Payload (Exact Match)
    FILTER_RANGE = "FILTER_RANGE"  # Payload (Range/Years)


class IndexingStrategy(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    renaming_map: Dict[str, str] = Field(description="Map old headers to snake_case")
    # Classification
    semantic_cols: List[str] = Field(default_factory=list)
    filter_exact_cols: List[str] = Field(default_factory=list)
    filter_range_cols: List[str] = Field(default_factory=list)

    # Special Logics
    start_year_col: Optional[str] = None
    end_year_col: Optional[str] = None

    primary_id_col: Optional[str] = None
