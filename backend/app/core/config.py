from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # points to backend/

class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"

    class Config:
        env_file = BASE_DIR / ".env"  # resolves to backend/.env

settings = Settings()

# Optional: print to verify
print(settings.DATABASE_URL)
print(settings.JWT_SECRET)
