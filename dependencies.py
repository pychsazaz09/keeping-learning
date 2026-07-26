from storage.json_storage import JsonStorage

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from database import AsyncSessionLocal
from repositories.sqlalchemy_repo import SqlalchemyRepositories

'''def get_storage()->JsonStorage:
    return JsonStorage("data/questions.json")'''

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def get_storage(db:AsyncSession=Depends(get_db)):
    return SqlalchemyRepositories(db)
    

