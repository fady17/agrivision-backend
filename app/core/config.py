from pydantic_settings import BaseSettings
from urllib.parse import quote_plus 
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

     # Database 
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SERVER: str
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str
    
    # Auth
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30


    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        # Encode password to handle special chars like '@' safely
        encoded_password = quote_plus(self.POSTGRES_PASSWORD)
        
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{encoded_password}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    class Config:
        env_file = ".env"
        # Extract extra env vars without error
        extra = "ignore"
    

settings = Settings() # type: ignore