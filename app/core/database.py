from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# 1. Create Async Engine
engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=False, # Set to True to see SQL queries in logs
)

# 2. Create Session Factory
SessionLocal = sessionmaker(
    bind=engine, # type: ignore
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
) # type: ignore

# 3. Base class for Models
Base = declarative_base()

# 4. Dependency for FastAPI routes
async def get_db():
    async with SessionLocal() as session: # type: ignore
        try:
            yield session
        finally:
            await session.close()