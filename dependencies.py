# from storage.json_storage import JsonStorage
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal
from repositories.sqlalchemy_repo import SqlalchemyRepositories
from services import auth_service

"""def get_storage()->JsonStorage:
    return JsonStorage("data/questions.json")"""


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def get_storage(db: AsyncSession = Depends(get_db)):
    return SqlalchemyRepositories(db)


security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):

    token = credentials.credentials
    payload = auth_service.decode_token(token)
    if not payload:
        raise HTTPException(401, detail="解析token出错")
    username = payload.get("username")
    if not username:
        raise HTTPException(401, detail="用户信息可能被篡改")
    user = await auth_service.get_user_by_name(db, username)
    if not user:
        raise HTTPException(401, detail="用户不存在")
    return user
