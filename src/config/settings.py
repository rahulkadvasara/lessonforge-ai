"""Application configuration and environment settings."""
import os
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load .env if present
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")


DEFAULT_LEARNER_PROFILE = {
    "target_audience": "12th-grade graduate from India",
    "english_proficiency": "Limited vocabulary, non-English-medium educational background",
    "technical_background": "Little or no prior technical/programming knowledge",
    "goal": "Wants to begin a career in Artificial Intelligence",
    "teaching_guidelines": [
        "Use simple, conversational English without academic jargon",
        "Explain any new technical term immediately when it appears",
        "Use relatable everyday analogies (e.g., student consulting a college handbook)",
        "Progress step-by-step from intuition to technical components to summary",
        "Include active knowledge checks and practical examples"
    ]
}

DEFAULT_TOPIC = "Introduction to RAG (Retrieval-Augmented Generation)"


class Settings(BaseModel):
    app_name: str = "LessonForge AI"
    app_env: str = os.getenv("APP_ENV", "development")
    
    # LLM Settings
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    llm_timeout_seconds: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
    llm_max_retries: int = int(os.getenv("LLM_MAX_RETRIES", "3"))
    
    # Storage & Persistence
    database_path: str = os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "lessonforge.db"))
    references_dir: str = str(BASE_DIR / "data" / "references")
    exports_dir: str = str(BASE_DIR / "exports")
    
    # Workflow Constraints
    default_max_retries: int = int(os.getenv("DEFAULT_MAX_RETRIES", "2"))
    hard_max_retries: int = 2  # Hard ceiling enforced by requirements
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    model_config = {"arbitrary_types_allowed": True}


def get_settings() -> Settings:
    """Return a singleton-like settings instance."""
    return Settings()
