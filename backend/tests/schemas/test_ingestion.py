import pytest
from app.schemas.ingestion import (
    IngestionStatus,
    BaseIngestionConfig,
    FileIngestionConfig,
    FolderIngestionConfig,
    SqlIngestionConfig,
    IngestionConfig,
    ColumnType,
    IndexingStrategy,
)


def test_ingestion_status_enum():
    """Test IngestionStatus enum values."""
    assert IngestionStatus.PENDING == "PENDING"
    assert IngestionStatus.PROCESSING == "PROCESSING"
    assert IngestionStatus.COMPLETED == "COMPLETED"
    assert IngestionStatus.FAILED == "FAILED"


def test_base_ingestion_config_defaults():
    """Test BaseIngestionConfig default values."""
    config = BaseIngestionConfig()
    assert config.enabled is True


def test_file_ingestion_config_defaults():
    """Test FileIngestionConfig default values."""
    config = FileIngestionConfig()
    assert config.extensions == ["*"]
    assert config.enabled is True
    assert config.max_size_mb == 20
    assert config.path is None


def test_file_ingestion_config_custom():
    """Test FileIngestionConfig with custom values."""
    config = FileIngestionConfig(extensions=[".pdf", ".docx"], enabled=False, max_size_mb=50, path="/custom/path")
    assert config.extensions == [".pdf", ".docx"]
    assert config.enabled is False
    assert config.max_size_mb == 50
    assert config.path == "/custom/path"


def test_folder_ingestion_config_defaults():
    """Test FolderIngestionConfig default values."""
    config = FolderIngestionConfig(path="/test/path")
    assert config.path == "/test/path"
    assert config.recursive is True
    assert config.patterns == ["*"]


def test_folder_ingestion_config_custom():
    """Test FolderIngestionConfig with custom values."""
    config = FolderIngestionConfig(path="/custom/path", recursive=False, patterns=["*.pdf", "*.txt"])
    assert config.path == "/custom/path"
    assert config.recursive is False
    assert config.patterns == ["*.pdf", "*.txt"]


def test_sql_ingestion_config_defaults():
    """Test SqlIngestionConfig default values."""
    config = SqlIngestionConfig(host="localhost", database="testdb", user="testuser", password="testpass")
    assert config.host == "localhost"
    assert config.port == 1433
    assert config.database == "testdb"
    assert config.user == "testuser"
    assert config.password == "testpass"
    assert config.db_schema == "dbo"
    assert config.type == "mssql"
    assert config.connection_string is None
    assert config.views == []


def test_sql_ingestion_config_schema_alias():
    """Test SqlIngestionConfig schema field aliasing."""
    # Test with 'schema' alias
    config = SqlIngestionConfig(
        host="localhost", database="testdb", user="testuser", password="testpass", schema="custom_schema"
    )
    assert config.db_schema == "custom_schema"


def test_ingestion_config_defaults():
    """Test IngestionConfig default values."""
    config = IngestionConfig()
    assert config.batch_size == 50
    assert config.workers == 4
    assert config.chunk_size == 1024
    assert config.chunk_overlap == 200


def test_column_type_enum():
    """Test ColumnType enum values."""
    assert ColumnType.SEMANTIC == "SEMANTIC"
    assert ColumnType.FILTER_EXACT == "FILTER_EXACT"
    assert ColumnType.FILTER_RANGE == "FILTER_RANGE"


def test_indexing_strategy_defaults():
    """Test IndexingStrategy default values."""
    config = IndexingStrategy(renaming_map={"Old Name": "old_name"})
    assert config.renaming_map == {"Old Name": "old_name"}
    assert config.semantic_cols == []
    assert config.filter_exact_cols == []
    assert config.filter_range_cols == []
    assert config.start_year_col is None
    assert config.end_year_col is None
    assert config.primary_id_col is None


def test_indexing_strategy_custom():
    """Test IndexingStrategy with custom values."""
    config = IndexingStrategy(
        renaming_map={"Product Name": "product_name"},
        semantic_cols=["description", "title"],
        filter_exact_cols=["category", "brand"],
        filter_range_cols=["price"],
        start_year_col="start_year",
        end_year_col="end_year",
        primary_id_col="product_id",
    )
    assert config.renaming_map == {"Product Name": "product_name"}
    assert config.semantic_cols == ["description", "title"]
    assert config.filter_exact_cols == ["category", "brand"]
    assert config.filter_range_cols == ["price"]
    assert config.start_year_col == "start_year"
    assert config.end_year_col == "end_year"
    assert config.primary_id_col == "product_id"
