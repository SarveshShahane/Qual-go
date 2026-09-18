import os
from dotenv import load_dotenv
load_dotenv()
class Settings():
    def __init__(self):
        self.DATABASE_HOST = os.getenv("DATABASE_HOST")
        self.DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
        self.DATABASE_NAME = os.getenv("DATABASE_NAME")
        self.DATABASE_USER = os.getenv("DATABASE_USER")
        self.DATABASE_PORT = int(os.getenv("DATABASE_PORT"))
    
    @property
    def DATABASE_URL(self):
        URL = f"postgresql+asyncpg://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        return URL
    
settings = Settings()