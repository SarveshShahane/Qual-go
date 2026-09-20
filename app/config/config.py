import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self):
        self.DATABASE_HOST = os.getenv("DATABASE_HOST")
        self.DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
        self.DATABASE_NAME = os.getenv("DATABASE_NAME")
        self.DATABASE_USER = os.getenv("DATABASE_USER")
        self.DATABASE_PORT = int(os.getenv("DATABASE_PORT", 5432))

        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
        self.JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-jwt-key-qual-dev-change-in-production")
        self.JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
        self.ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 15))
        self.REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))
        self.COOKIE_SECURE = os.getenv("COOKIE_SECURE", str(self.ENVIRONMENT == "production")).lower() == "true"

    @property
    def DATABASE_URL(self):
        URL = f"postgresql+asyncpg://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        return URL
    
settings = Settings()