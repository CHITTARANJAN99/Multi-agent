from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.config.settings import settings
from app.core.logging_config import logger
from app.core.errors import DatabaseError

# Async PostgreSQL Engine Setup
try:
    engine = create_async_engine(
        settings.async_database_url,
        echo=settings.DEBUG,
        pool_pre_ping=True,
        pool_size=20,
        max_overflow=10
    )
    AsyncSessionLocal = async_sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False
    )
except Exception as e:
    logger.critical(f"Failed to create SQLAlchemy engine: {e}")
    raise DatabaseError("SQLAlchemy database engine initialization failed", detail=str(e))

Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency yielding a scoped database session.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Transaction failed, database rollback triggered: {e}", exc_info=True)
            raise DatabaseError("Database transaction failed", detail=str(e))
        finally:
            await session.close()
