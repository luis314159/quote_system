from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
from pathlib import Path
load_dotenv(dotenv_path=env_path)
import os

class Settings:
    # Variables de configuración
    PORT: int = int(os.getenv("PORT", 8080))
    MAIL_FROM_NAME: str = os.getenv("MAIL_FROM_NAME")
    MAIL_FROM_EMAIL: str = os.getenv("MAIL_FROM_EMAIL")
    MAIL_SERVER: str = os.getenv("MAIL_SERVER")
    MAIL_PORT: int = int(os.getenv("MAIL_PORT", 587))  # Valor predeterminado 587
    MAIL_USERNAME: str = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD: str = os.getenv("MAIL_PASSWORD")
    MAIL_TLS: bool = os.getenv("MAIL_TLS", "True").lower() in ("true", "1")
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    INTERNAL_QUOTE_EMAIL: str= os.getenv("INTERNAL_QUOTE_EMAIL")
    QUOTE_REPLY_EMAIL: str = os.getenv("QUOTE_REPLY_EMAIL")
settings = Settings()