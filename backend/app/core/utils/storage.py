import logging
import os
from app.core.settings import settings

logger = logging.getLogger(__name__)


def validate_data_mount() -> None:
    """
    Validates that the /data mount is correctly populated if VECTRA_DATA_PATH is set.
    Logs a warning if the mount seems broken (e.g. virtual drive issue).
    This function is intended to be called during application startup (API and Worker).
    """
    if not settings.VECTRA_DATA_PATH:
        return

    try:
        data_path = "/data"
        if os.path.exists(data_path):
            contents = os.listdir(data_path)
            if not contents:
                logger.warning("\n" + "!" * 80)
                logger.warning("🚨 [STORAGE WARNING] The '/data' volume mount is EMPTY.")
                logger.warning(f"👉 VECTRA_DATA_PATH is set to: {settings.VECTRA_DATA_PATH}")
                logger.warning("👉 This usually happens when using a Virtual/Network drive (G:, OneDrive, iCloud).")
                logger.warning("👉 FIX: Move your data to a physical drive (C: or D:) and update .env.")
                logger.warning("!" * 80 + "\n")
            else:
                logger.info(f"📂 [STORAGE] Data mount active: {len(contents)} items found in /data")
        else:
            logger.error("🚨 [STORAGE ERROR] The '/data' directory does not exist inside the container.")
    except Exception as e:
        logger.error(f"⚠️ Failed to validate data mount: {e}")
