
    # Removed the stray line causing NameError before settings is imported

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings
import os
from dotenv import load_dotenv
load_dotenv()

# Use TEST_DATABASE_URL if present, else fallback to main DB
db_url = settings.DATABASE_URL

engine = create_async_engine(db_url, echo=False)
SessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession
)

Base = declarative_base()

async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        await db.close()



