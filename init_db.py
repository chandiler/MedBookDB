# init_db.py
import asyncio
from app.db.sql import engine
from app.db.base import Base

# IMPORTANT: import all models so that Base.metadata knows them
from app.modules.users import models as users_models
from app.modules.doctors import models as doctors_models
from app.modules.appointments import models as appointments_models

async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    print("Database schema recreated successfully!")


if __name__ == "__main__":
    asyncio.run(init_models())
