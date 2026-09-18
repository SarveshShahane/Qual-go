from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker,AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config.config import settings

DATABASE_URL = settings.DATABASE_URL

engine = create_async_engine(
    url=DATABASE_URL,
    echo = True,
    pool_pre_ping = True
)


AsyncSessionService = async_sessionmaker(
    bind= engine,
    class_=AsyncSession,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionService() as session:
        yield session