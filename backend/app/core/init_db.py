import logging
import time

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from app.core.database import SessionLocal
from app.core.exceptions import TechnicalError
from app.core.security import get_password_hash
from app.core.settings import settings
from app.models.user import User

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """
    Initialize the database with default data (e.g. admin user).
    This function is idempotent.
    """
    start_time = time.time()
    func_name = "init_db"

    try:
        async with SessionLocal() as session:
            # Check for existing admin user
            statement = select(User).where(User.email == settings.FIRST_SUPERUSER)
            result = await session.execute(statement)
            user = result.scalar_one_or_none()

            if not user:
                logger.info(f"Context | {func_name} | Msg: Admin user not found. Creating default admin.")

                # P0 Fix: Offload CPU-heavy hashing to threadpool to avoid blocking async loop
                hashed_pw = await run_in_threadpool(get_password_hash, settings.FIRST_SUPERUSER_PASSWORD)

                admin_user = User(
                    email=settings.FIRST_SUPERUSER, hashed_password=hashed_pw, role="admin", is_active=True
                )
                session.add(admin_user)
                await session.commit()
                logger.info(f"Context | {func_name} | Msg: Default admin user created: {settings.FIRST_SUPERUSER}")
            else:
                logger.info(f"Context | {func_name} | Msg: Admin user already exists.")

        elapsed = round((time.time() - start_time) * 1000, 2)
        logger.info(f"FINISH | {func_name} | Status: Success | Duration: {elapsed}ms")

    except SQLAlchemyError as e:
        # Critical failure if we can't seed the DB
        logger.critical(f"❌ FAIL | {func_name} | Database Error: {e}", exc_info=True)
        raise TechnicalError(f"Failed to initialize database: {e}")
    except Exception as e:
        logger.critical(f"❌ FAIL | {func_name} | Error: {e}", exc_info=True)
        raise TechnicalError(f"Unexpected error during database initialization: {e}")
