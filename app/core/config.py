from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_TITLE: str = "AgriVision Architect API"
    API_VERSION: str = "v1"
    
    # MinIO Settings
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET_NAME: str = "plant-disease-images"
    MINIO_SECURE: bool = False
    # New Gemini Setting
    GEMINI_API_KEY: str

     # Database (NEW)
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SERVER: str
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    class Config:
        env_file = ".env"
        # Extract extra env vars without error
        extra = "ignore"
    

settings = Settings() # type: ignore