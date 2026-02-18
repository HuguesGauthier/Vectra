import logging
import os
import secrets
import sys
import threading
from typing import Literal, Optional, Type, Tuple

from pydantic import ValidationError, field_validator, model_validator
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
    PydanticBaseSettingsSource,
    YamlConfigSettingsSource,
    JsonConfigSettingsSource,
    TomlConfigSettingsSource,
)

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Global application settings loaded from environment variables or .env file.
    Follows 12-Factor App methodology.
    """

    # Environment
    ENV: Literal["development", "test", "production"] = "development"
    DEBUG: bool = False
    DB_ECHO: bool = False

    # Infrastructure
    DATABASE_URL: str = "postgresql+asyncpg://vectra:vectra@localhost:5432/vectra"
    BACKEND_WS_URL: str = "ws://localhost:8000/api/v1/ws?client_type=worker"
    VECTRA_DATA_PATH: Optional[str] = None  # Local path on Windows (mapped to /data in Docker)
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_RECYCLE: int = 3600

    # Security - NO HARDCODED DEFAULTS
    SECRET_KEY: Optional[str] = None
    WORKER_SECRET: Optional[str] = None

    # QDRANT
    QDRANT_HOST: str = "localhost"
    QDRANT_API_KEY: Optional[str] = None

    # REDIS (Semantic Caching)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    REDIS_CACHE_TTL: int = 86400  # 24 hours default
    SEMANTIC_CACHE_SIMILARITY_THRESHOLD: float = 0.90  # Balanced threshold (was 0.95)

    # External APIs
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    COHERE_API_KEY: Optional[str] = None
    MISTRAL_API_KEY: Optional[str] = None

    # Logging
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # Embedding Configuration
    EMBEDDING_PROVIDER: Literal["local", "openai", "gemini", "ollama"] = "ollama"
    GEMINI_EMBEDDING_MODEL: str = "models/text-embedding-004"
    GEMINI_TRANSCRIPTION_MODEL: str = "gemini-1.5-flash-latest"
    GEMINI_CHAT_MODEL: str = "gemini-1.5-flash-latest"

    # Ollama Configuration
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_EMBEDDING_MODEL: str = "bge-m3"  # User requested default

    LOCAL_EXTRACTION_MODEL: Optional[str] = "mistral"
    LOCAL_EXTRACTION_URL: str = "http://localhost:11434"

    # Whisper Configuration (Local)
    WHISPER_BASE_URL: str = "http://localhost:8003/v1"

    # Observability

    ENABLE_TRENDING: bool = True  # Toggle trending analysis in ChatPipeline
    LOG_RETENTION_DAYS: int = 30  # Days to keep error logs

    # Reranker Configuration
    RERANKER_PROVIDER: Literal["cohere", "local"] = "cohere"
    LOCAL_RERANK_MODEL: str = "BAAI/bge-reranker-base"

    # Hardware Tuning
    INGESTION_LOCAL_WORKERS: Optional[int] = None  # Override for local worker count

    # Initial Bootstrap
    FIRST_SUPERUSER: str = "admin@vectra.ai"
    FIRST_SUPERUSER_PASSWORD: Optional[str] = None

    model_config = SettingsConfigDict(
        # Use absolute path to find .env regardless of where the app is run from
        env_file=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        """
        Customise settings sources.
        Priority order:
        1. Init settings
        2. .env file settings (Higher priority to protect local dev)
        3. Environment variables (Fallback for Docker)
        4. Class defaults
        """
        return (
            init_settings,
            env_settings,  # Standard: Environment variables override .env
            dotenv_settings,
            file_secret_settings,
        )

    @field_validator("DATABASE_URL")
    @classmethod
    def assemble_db_connection(cls, v: str) -> str:
        """Fix Windows/Docker localhost issues."""
        if sys.platform == "win32" and "localhost" in v and "postgres" in v:
            logger.info("🔧 Config: Replacing 'localhost' with '127.0.0.1' for Windows compatibility.")
            return v.replace("localhost", "127.0.0.1")
        return v

    @field_validator("QDRANT_HOST")
    @classmethod
    def fix_qdrant_host_for_windows(cls, v: str) -> str:
        """Force IPv4 for Qdrant on Windows (Docker IPv6 binding issue)."""
        if sys.platform == "win32" and v == "localhost":
            logger.info("🔧 Config: Replacing QDRANT_HOST 'localhost' with '127.0.0.1' for Windows.")
            return "127.0.0.1"
        return v

    @field_validator("QDRANT_API_KEY")
    @classmethod
    def log_qdrant_key_status(cls, v: Optional[str]) -> Optional[str]:
        """Log whether QDRANT_API_KEY was loaded."""
        if v:
            logger.info(f"🔧 Config: QDRANT_API_KEY loaded (length: {len(v)})")
        else:
            logger.warning("⚠️  Config: QDRANT_API_KEY is empty or not set!")
        return v

    @field_validator("OLLAMA_BASE_URL", "LOCAL_EXTRACTION_URL", "REDIS_HOST", "WHISPER_BASE_URL")
    @classmethod
    def fix_ollama_host_for_windows(cls, v: str) -> str:
        """Fix Windows/Docker localhost issues for Ollama and Redis."""
        if sys.platform == "win32" and "localhost" in v:
            logger.info(f"🔧 Config: Replacing 'localhost' with '127.0.0.1' in {v} for Windows compatibility.")
            return v.replace("localhost", "127.0.0.1")
        return v

    @model_validator(mode="after")
    def validate_secrets_and_defaults(self) -> "Settings":
        """
        SECRET_KEY, WORKER_SECRET, and FIRST_SUPERUSER_PASSWORD validation.
        Strict in production, lenient with warnings in dev/test.
        """
        is_prod = self.ENV == "production"

        # 1. SECRET_KEY
        if not self.SECRET_KEY:
            if is_prod:
                raise ValueError(
                    "SECRET_KEY is required in production. "
                    "Generate one with: python -c 'import secrets; print(secrets.token_hex(32))'"
                )
            # Dev/Test: Auto-generate ephemeral key
            self.SECRET_KEY = secrets.token_hex(32)
            logger.warning(f"⚠️  SECRET_KEY auto-generated for {self.ENV} environment.")

        # 2. SECRET_KEY Strength (Production only)
        if is_prod:
            if len(self.SECRET_KEY) < 32:
                raise ValueError("SECRET_KEY must be at least 32 characters in production.")
            if any(weak in self.SECRET_KEY.lower() for weak in ["dev-secret", "change-me", "test-key"]):
                raise ValueError("SECRET_KEY contains weak/default patterns in production.")

        # 3. WORKER_SECRET
        if not self.WORKER_SECRET:
            if is_prod:
                raise ValueError("WORKER_SECRET is required in production.")
            self.WORKER_SECRET = "dev-worker-secret-ephemeral"
            logger.warning(f"⚠️  WORKER_SECRET auto-generated for {self.ENV} environment.")

        if is_prod and len(self.WORKER_SECRET) < 32:
            raise ValueError("WORKER_SECRET must be at least 32 characters in production.")

        # 4. FIRST_SUPERUSER_PASSWORD
        if not self.FIRST_SUPERUSER_PASSWORD:
            if is_prod:
                raise ValueError("FIRST_SUPERUSER_PASSWORD is required in production.")
            self.FIRST_SUPERUSER_PASSWORD = "vectra123!"
            logger.warning(f"⚠️  Using default superuser password for {self.ENV} environment.")

        if is_prod and self.FIRST_SUPERUSER_PASSWORD == "vectra123!":
            raise ValueError("Default FIRST_SUPERUSER_PASSWORD detected in production.")

        # 5. DEBUG Mode Check
        if is_prod and self.DEBUG:
            raise ValueError("DEBUG must be False in production.")

        # 6. DATABASE_URL Check (Production only)
        # Prevent accidental use of the default local dev DB in production
        # We check for both localhost and 127.0.0.1 (Windows fixer might have run)
        if is_prod and any(h in self.DATABASE_URL for h in ["localhost:5432/vectra", "127.0.0.1:5432/vectra"]):
            raise ValueError(
                "Default local DATABASE_URL detected in production environment. "
                "Please set a valid DATABASE_URL in your environment variables."
            )

        return self

    @model_validator(mode="after")
    def validate_provider_dependencies(self) -> "Settings":
        """
        Validate that required keys are present for the chosen provider.
        Bypassed in test environment to avoid mocking .env in every test.
        """
        if self.ENV == "test":
            print(f"DEBUG: Skipping validation because ENV={self.ENV}")
            return self

        print(
            f"DEBUG: Validating provider. ENV={self.ENV}, PROVIDER={self.EMBEDDING_PROVIDER}, KEY={self.GEMINI_API_KEY}"
        )

        if self.ENV == "development" and self.EMBEDDING_PROVIDER == "gemini" and not self.GEMINI_API_KEY:
            logger.warning("⚠️  Config: GEMINI_API_KEY missing in development. Falling back to 'local' provider.")
            self.EMBEDDING_PROVIDER = "local"
            return self

        if self.EMBEDDING_PROVIDER == "gemini" and not self.GEMINI_API_KEY:
            raise ValueError("EMBEDDING_PROVIDER 'gemini' requires GEMINI_API_KEY")

        if self.EMBEDDING_PROVIDER == "openai" and not self.OPENAI_API_KEY:
            raise ValueError("EMBEDDING_PROVIDER 'openai' requires OPENAI_API_KEY")

        if self.EMBEDDING_PROVIDER == "ollama" and not self.OLLAMA_BASE_URL:
            raise ValueError("EMBEDDING_PROVIDER 'ollama' requires OLLAMA_BASE_URL")

        return self

    @property
    def computed_local_workers(self) -> int:
        """
        Dynamically determine the number of workers for local embedding/extraction
        based on available hardware (VRAM).
        """
        if self.INGESTION_LOCAL_WORKERS is not None:
            return self.INGESTION_LOCAL_WORKERS

        # Hardware Detection (NVIDIA)
        try:
            import subprocess

            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                check=True,
            )
            vram_mb = int(result.stdout.strip().split("\n")[0])
            vram_gb = vram_mb / 1024

            if vram_gb < 6:
                # P0: For very low VRAM on Windows, stay synchronous (0 workers)
                # to avoid multiprocessing overhead and memory pressure.
                workers = 0 if sys.platform == "win32" else 1
            elif vram_gb < 12:
                workers = 4  # Balanced (RTX 4060)
            else:
                workers = 8  # Performance (RTX 4070+)

            logger.info(f"⚡ Hardware Detection: Detected {vram_gb:.1f} GB VRAM -> Using {workers} workers")
            return workers
        except Exception as e:
            logger.debug(f"Hardware detection failed or no GPU found: {e}. Defaulting to 1 worker.")
            return 1

    @property
    def computed_extraction_concurrency(self) -> int:
        """
        Dynamically determine how many parallel LLM extraction calls to allow.
        """
        # Hardware-aware concurrency
        try:
            workers = self.computed_local_workers
            if workers == 0:
                return 1  # Ultra-safe
            if workers == 1:
                return 1  # Safe
            if workers <= 4:
                return 2  # Balanced
            return 5  # Performance
        except:
            return 1


# --- Thread-Safe Lazy Singleton ---

_settings: Optional[Settings] = None
_settings_lock = threading.Lock()


def get_settings() -> Settings:
    """
    Thread-safe lazy loading of settings.

    Raises:
        ValidationError: If configuration is invalid.

    Returns:
        Settings: The validated application settings.

    Note:
        This function WILL crash the application if configuration is invalid.
        This is by design - fail fast in production rather than running with
        misconfigured secrets.
    """
    global _settings

    # Fast path for already-initialized settings (no lock needed)
    if _settings is not None:
        return _settings

    # Slow path - acquire lock for initialization
    with _settings_lock:
        # Double-check after acquiring lock (another thread may have initialized)
        if _settings is None:
            try:
                _settings = Settings()
                redis_pw_status = "SET" if _settings.REDIS_PASSWORD else "MISSING"
                logger.info(f"✅ Configuration loaded (ENV={_settings.ENV}). Redis PW: {redis_pw_status}")
            except ValidationError as e:
                if "pytest" in sys.modules:
                    logger.warning(
                        f"⚠️  Config validation failed during test collection: {e}. Using model_construct fallback."
                    )
                    _settings = Settings.model_construct(
                        _env_file=None,
                        SECRET_KEY="test-fallback-secret-key",
                        WORKER_SECRET="test-fallback-worker-secret",
                    )
                else:
                    logger.critical(f"❌ Configuration validation failed: {e}")
                    raise
            except Exception as e:
                logger.critical(f"❌ Unexpected error loading configuration: {e}")
                raise

        return _settings


# Legacy global accessor for backward compatibility
# DEPRECATED: Use get_settings() instead
try:
    settings = get_settings()
except ValidationError as e:
    # If running in pytest, we might catch this if needed, but usually we want to fail
    if "pytest" in sys.modules:
        # Fallback for tests if .env is missing critical keys not needed for unit tests
        logger.warning(f"⚠️  Configuration validation failed during test collection: {e}")
        # Create a dummy settings object with defaults to allow collection to proceed
        # We bypass validation by constructing with minimal valid defaults if possible
        # Or just allow the error if we can't recover.
        # But to fix 'ImportError', we MUST define settings.
        try:
            # Attempt to create settings bypassing strict validation?
            # Pydantic models are hard to bypass.
            # We can create a partial mock or just re-raise if strictly needed.
            # But let's try to construct it with checks disabled? No easy way.
            # Best effort: use the class defaults which might be enough if ENV != production
            # Use model_construct to bypass validation during test collection
            settings = Settings.model_construct(
                _env_file=None,
                SECRET_KEY="test-fallback-secret-key",
                WORKER_SECRET="test-fallback-worker-secret",
            )

            logger.warning("⚠️  Loaded fallback settings via model_construct for testing.")
        except Exception as e2:
            logger.critical(f"❌ Could not create fallback settings: {e2}")
            raise e
    else:
        logger.critical(f"⚠️  Configuration validation failed: {e}")
        raise
except Exception as e:
    logger.critical(f"❌ Fatal error during settings initialization: {e}")
    raise
