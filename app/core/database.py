from sqlalchemy.ext.asyncio import create_async_engine,  async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings



print("--- DEBUG DATABASE CONFIG ---")
print(f"URI: {settings.SQLALCHEMY_DATABASE_URI}")
print("---------------------------")

# 1. Create Async Engine
engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=False,
)

# 2. Create Session Factory

SessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,

) 

# 3. Base class for Models
Base = declarative_base()

# 4. Dependency for FastAPI routes
async def get_db():

    async with SessionLocal() as session:
        yield session
     