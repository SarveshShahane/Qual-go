import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self):
        self.DATABASE_HOST = os.getenv("DATABASE_HOST") or os.getenv("Database_HOST") or "localhost"
        self.DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD") or os.getenv("Database_PASSWORD") or ""
        self.DATABASE_NAME = os.getenv("DATABASE_NAME") or os.getenv("Database_NAME") or "postgres"
        self.DATABASE_USER = os.getenv("DATABASE_USER") or os.getenv("Database_USER") or "postgres"
        self.DATABASE_PORT = int(os.getenv("DATABASE_PORT") or os.getenv("Database_PORT") or 5432)

        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
        self.JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-jwt-key-qual-dev-change-in-production")
        self.JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
        self.ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 15))
        self.REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))
        self.COOKIE_SECURE = os.getenv("COOKIE_SECURE", str(self.ENVIRONMENT == "production")).lower() == "true"
        self.GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
        self.GROQ_LLM_MODEL = os.getenv("GROQ_LLM_MODEL", "llama-3.3-70b-versatile")

        cors_env = os.getenv("CORS_ORIGINS", "")
        if cors_env:
            self.CORS_ORIGINS = [orig.strip() for orig in cors_env.split(",") if orig.strip()]
        else:
            self.CORS_ORIGINS = [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "http://localhost:80",
                "http://localhost",
            ]

    @property
    def DATABASE_URL(self):
        env_url = os.getenv("DATABASE_URL")
        if env_url:
            if env_url.startswith("postgresql://"):
                return env_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif env_url.startswith("postgres://"):
                return env_url.replace("postgres://", "postgresql+asyncpg://", 1)
            return env_url
        URL = f"postgresql+asyncpg://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        return URL
    
settings = Settings()