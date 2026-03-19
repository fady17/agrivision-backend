from typing import Optional
from pydantic_settings import BaseSettings
from urllib.parse import quote_plus


class Settings(BaseSettings):
    API_TITLE: str = "AgriVision Architect API"
    API_VERSION: str = "v1"

    # ------------------------------------------------------------------
    # AI Provider selection
    # ------------------------------------------------------------------
    # Options: "gemini" | "ollama" | "lmstudio"
    AI_PROVIDER: str = "gemini"

    # --- Gemini (cloud) ---
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # --- Ollama (local) ---
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llava-llama3"

    # --- LM Studio (local) ---
    LM_STUDIO_BASE_URL: str = "http://localhost:1234"
    LM_STUDIO_MODEL: str = "llava-v1.6-mistral-7b"

    LOCAL_AI_TIMEOUT: float = 180.0

    # ------------------------------------------------------------------
    # MinIO / Storage
    # ------------------------------------------------------------------
    MINIO_ENDPOINT: str          # Docker-internal, e.g. "minio:9000"
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET_NAME: str = "plant-disease-images"
    MINIO_SECURE: bool = False

    # The hostname:port that clients OUTSIDE Docker use to reach MinIO.
    # Presigned URLs are signed with this host so the signature is valid
    # when Flutter (or a browser) fetches the URL directly.
    #
    # Examples:
    #   - iOS Simulator / local dev  → "localhost:9000"
    #   - Physical device on LAN     → "192.168.1.100:9000"
    #   - Production                 → "media.yourdomain.com"
    #
    # Defaults to "localhost:9000" so local development works out of the box.
    MINIO_PUBLIC_ENDPOINT: str = "localhost:9000"

    # ------------------------------------------------------------------
    # Database (PostgreSQL)
    # ------------------------------------------------------------------
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SERVER: str
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str

    # ------------------------------------------------------------------
    # Auth / JWT
    # ------------------------------------------------------------------
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ------------------------------------------------------------------
    # Computed properties
    # ------------------------------------------------------------------
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        encoded_password = quote_plus(self.POSTGRES_PASSWORD)
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{encoded_password}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()  # type: ignore[call-arg]
# from typing import Optional
# from pydantic_settings import BaseSettings
# from urllib.parse import quote_plus


# class Settings(BaseSettings):
#     API_TITLE: str = "AgriVision Architect API"
#     API_VERSION: str = "v1"

#     # ------------------------------------------------------------------
#     # AI Provider selection
#     # ------------------------------------------------------------------
#     # Options: "gemini" | "ollama" | "lmstudio"
#     AI_PROVIDER: str = "gemini"

#     # --- Gemini (cloud) ---
#     GEMINI_API_KEY: Optional[str] = None
#     GEMINI_MODEL: str = "gemini-2.5-flash"

#     # --- Ollama (local) ---
#     OLLAMA_BASE_URL: str = "http://localhost:11434"
#     # Recommended vision models: llava, llava-llama3, moondream, bakllava
#     OLLAMA_MODEL: str = "qwen/qwen3.5-9b"

#     # --- LM Studio (local) ---
#     LM_STUDIO_BASE_URL: str = "http://localhost:1234"
#     # Must match the model name shown in LM Studio's Local Server tab
#     LM_STUDIO_MODEL: str = "qwen/qwen3.5-9b"

#     # Shared timeout (seconds) for local model requests — they're slow
#     LOCAL_AI_TIMEOUT: float = 180.0

#     # ------------------------------------------------------------------
#     # MinIO / Storage
#     # ------------------------------------------------------------------
#     MINIO_ENDPOINT: str
#     MINIO_ACCESS_KEY: str
#     MINIO_SECRET_KEY: str
#     MINIO_BUCKET_NAME: str = "plant-disease-images"
#     MINIO_SECURE: bool = False

#     # ------------------------------------------------------------------
#     # Database (PostgreSQL)
#     # ------------------------------------------------------------------
#     POSTGRES_USER: str
#     POSTGRES_PASSWORD: str
#     POSTGRES_SERVER: str
#     POSTGRES_PORT: str = "5432"
#     POSTGRES_DB: str

#     # ------------------------------------------------------------------
#     # Auth / JWT
#     # ------------------------------------------------------------------
#     SECRET_KEY: str
#     ALGORITHM: str = "HS256"
#     ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

#     # ------------------------------------------------------------------
#     # Computed properties
#     # ------------------------------------------------------------------
#     @property
#     def SQLALCHEMY_DATABASE_URI(self) -> str:
#         encoded_password = quote_plus(self.POSTGRES_PASSWORD)
#         return (
#             f"postgresql+asyncpg://{self.POSTGRES_USER}:{encoded_password}"
#             f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
#         )

#     class Config:
#         env_file = ".env"
#         extra = "ignore"


# settings = Settings()  # type: ignore[call-arg]
# # from pydantic_settings import BaseSettings
# # from urllib.parse import quote_plus 
# # class Settings(BaseSettings):
# #     API_TITLE: str = "AgriVision Architect API"
# #     API_VERSION: str = "v1"
    
# #     # MinIO Settings
# #     MINIO_ENDPOINT: str
# #     MINIO_ACCESS_KEY: str
# #     MINIO_SECRET_KEY: str
# #     MINIO_BUCKET_NAME: str = "plant-disease-images"
# #     MINIO_SECURE: bool = False
# #     # New Gemini Setting
# #     GEMINI_API_KEY: str

# #      # Database 
# #     POSTGRES_USER: str
# #     POSTGRES_PASSWORD: str
# #     POSTGRES_SERVER: str
# #     POSTGRES_PORT: str = "5432"
# #     POSTGRES_DB: str
    
# #     # Auth
# #     SECRET_KEY: str
# #     ALGORITHM: str = "HS256"
# #     ACCESS_TOKEN_EXPIRE_MINUTES: int = 30


# #     @property
# #     def SQLALCHEMY_DATABASE_URI(self) -> str:
   
# #         encoded_password = quote_plus(self.POSTGRES_PASSWORD)
        
# #         return f"postgresql+asyncpg://{self.POSTGRES_USER}:{encoded_password}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

# #     class Config:
# #         env_file = ".env"
   
# #         extra = "ignore"
    

# # settings = Settings() # type: ignore