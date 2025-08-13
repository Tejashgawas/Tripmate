from app.core.database import engine,Base
from app.models.user.user import User

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)