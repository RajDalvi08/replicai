import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings:
    def __init__(self) -> None:
        self.app_name = os.getenv("APP_NAME", "replicai")
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./replicai.db")
        self.max_upload_bytes = int(
            os.getenv("MAX_UPLOAD_BYTES", str(20 * 1024 * 1024))
        )
        self.llm_api_key = os.getenv("LLM_API_KEY")
        self.llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.llm_base_url = os.getenv("LLM_BASE_URL")
        self.temp_dir = Path(os.getenv("TEMP_DIR", BASE_DIR / "tmp"))
        self.temp_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
