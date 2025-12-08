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

    class Config:
        env_file = ".env"
        # Extract extra env vars without error
        extra = "ignore"

settings = Settings() # type: ignore