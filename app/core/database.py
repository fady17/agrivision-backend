from sqlalchemy.ext.asyncio import create_async_engine,  async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# 1. Create Async Engine
engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=False,
)

# 2. Create Session Factory
# FIX: Use 'async_sessionmaker' instead of 'sessionmaker'
SessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    # Note: 'autocommit' is not supported in async_sessionmaker and removed in SQLAlchemy 2.0
) 

# 3. Base class for Models
Base = declarative_base()

# 4. Dependency for FastAPI routes
async def get_db():
    # Pylance will now correctly recognize this as an AsyncSession context manager
    async with SessionLocal() as session:
        yield session
        # No need for finally/close; context manager handles it