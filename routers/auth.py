from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_db
from schemas.user import (
    RefreshRequest,
    ResponseToken,
    UserCreate,
    UserLogin,
    UserResponse,
)
from services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    exist = await auth_service.get_user_by_name(db, user.username)
    if exist:
        raise HTTPException(400, detail="用户已注册")
    userTable = await auth_service.create_user(db, user)
    return userTable


@router.post("/login", response_model=ResponseToken)
async def login(user: UserLogin, db: AsyncSession = Depends(get_db)):
    userTable = await auth_service.authenticate_user(db, user.username, user.password)
    if not userTable:
        raise HTTPException(401, detail="用户名或密码错误")
    token_data = {"sub": userTable.id, "username": userTable.username}
    return ResponseToken(
        access_token=auth_service.create_access_token(token_data),
        refresh_token=auth_service.create_refresh_token(token_data),
    )


@router.post("/refresh", response_model=ResponseToken)
async def refresh(refresh: RefreshRequest):
    two_tokens = auth_service.refresh_token(refresh.refresh_token)
    if not two_tokens:
        raise HTTPException(401, "token过期,请重新登录")
    access_token, refresh_token = two_tokens
    return ResponseToken(access_token=access_token, refresh_token=refresh_token)
