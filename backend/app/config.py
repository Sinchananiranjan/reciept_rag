import os
from pydantic import ConfigDict
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "ReceiptRAG"
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "receiptrag_super_secret_jwt_key_2026_change_in_prod"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    DATABASE_URL: str = "sqlite:///./receiptrag.db"
    UPLOAD_DIR: str = os.path.abspath("./uploads")
    VECTOR_DB_DIR: str = os.path.abspath("./chroma_db")

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    LLM_MODEL: str = "gpt-4o-mini"

    # OCR settings
    TESSERACT_CMD: str = os.getenv("TESSERACT_CMD", "")

settings = Settings()

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.VECTOR_DB_DIR, exist_ok=True)
