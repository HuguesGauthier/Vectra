import logging
import os
from app.core.settings import settings

logger = logging.getLogger(__name__)

# Global storage status (True = OK, False = Error)
_storage_status = True


def get_storage_status() -> bool:
    """Returns the current storage health status."""
    return _storage_status


def validate_data_mount() -> None:
    """
    Validates that the /data mount is correctly populated if VECTRA_DATA_PATH is set.
    Logs a warning if the mount seems broken (e.g. virtual drive issue).
    This function is intended to be called during application startup (API and Worker).
    """
    if not settings.VECTRA_DATA_PATH:
        return

    # If running natively on Windows (not in Docker), /data mount doesn't exist.
    # We skip validation as paths are accessed directly.
    import sys

    if sys.platform == "win32" and not os.path.exists("/.dockerenv"):
        return

    # For other non-containerized environments in development, also skip.
    if not os.path.exists("/.dockerenv") and settings.ENV == "development":
        return

    global _storage_status
    try:
        data_path = "/data"
        if os.path.exists(data_path):
            # We no longer mark as offline if empty, because it's normal on fresh install.
            # We just log a hint.
            _storage_status = True
            try:
                contents = os.listdir(data_path)
                if not contents:
                    logger.info(f"📂 [STORAGE] Data mount '/data' is active but currently empty.")
                else:
                    logger.info(f"📂 [STORAGE] Data mount active: {len(contents)} items found in /data")
            except Exception as list_err:
                _storage_status = False
                logger.error(f"🚨 [STORAGE ERROR] Cannot read '/data' content: {list_err}")
        else:
            _storage_status = False
            logger.error("🚨 [STORAGE ERROR] The '/data' directory does not exist inside the container.")
    except Exception as e:
        _storage_status = False
        logger.error(f"⚠️ Failed to validate data mount: {e}")
