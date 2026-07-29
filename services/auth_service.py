import json
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import bcrypt
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user_orm import UserTable
from schemas.user import UserCreate

from models.question_orm import QuestionTable

# ================= 密码哈希 =================


def hash_password(password: str) -> str:
    """把明文密码哈希为 bcrypt 格式的不可逆字符串。

    Args:
        password: 明文密码，长度 6-128

    Returns:
        bcrypt 哈希值，$2b$12$... 格式

    Raises:
        ValueError: 密码为空时抛出
    """
    if not password:
        raise ValueError("密码不能为空")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码是否匹配 bcrypt 哈希值。

    Args:
        plain_password: 用户输入的明文密码
        hashed_password: 数据库中存储的 bcrypt 哈希

    Returns:
        True 表示密码正确，False 表示不匹配
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


# ================= JWT 签发和验证 =================

SECRET_KEY = os.getenv("JWT_SECRET_KEY") or "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


def create_access_token(data: dict) -> str:
    """签发 access token（短期有效，30 分钟）。

    Args:
        data: 要编码到 token 中的数据，如 {"sub": user_id, "username": "alice"}

    Returns:
        JWT 字符串，30 分钟后过期
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """签发 refresh token（长期有效，7 天）。

    Args:
        data: 要编码到 token 中的数据

    Returns:
        JWT 字符串，7 天后过期
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    """解码并验证 JWT token。

    Args:
        token: JWT 字符串

    Returns:
        解码后的 payload 字典；token 无效或过期时返回 None
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


# ================= 用户 CRUD =================


async def create_user(db: AsyncSession, data: UserCreate) -> UserTable:
    """创建新用户并写入数据库。

    Args:
        db: 异步数据库会话
        data: 注册表单数据（username + password）

    Returns:
        创建成功的 UserTable ORM 对象
    """
    
    user = UserTable(
        id=uuid4().hex[:12],
        username=data.username,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    #await db.commit()
    await db.flush()

    q=QuestionTable(
        id=uuid4().hex[0:12],
        title="装饰器是干什么用的",
        tags=json.dumps(["装饰器","python基础"]),
        answer="注册函数返回函数地址并加强或只注册"
    )
    db.add(q)
    await db.commit()
    await db.refresh(user)#顺序有讲究
    
    return user


async def get_user_by_name(db: AsyncSession, username: str) -> UserTable | None:
    """按用户名查找用户。

    Args:
        db: 异步数据库会话
        username: 用户名

    Returns:
        UserTable 对象，不存在时返回 None
    """
    stmt = select(UserTable).where(UserTable.username == username)
    result = await db.execute(stmt)
    return result.scalars().first()


async def authenticate_user(
    db: AsyncSession, username: str, password: str
) -> UserTable | None:
    """验证用户名密码，通过则返回用户对象。

    Args:
        db: 异步数据库会话
        username: 用户名
        password: 明文密码

    Returns:
        验证通过返回 UserTable，失败返回 None
    """
    user = await get_user_by_name(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def refresh_token(refresh: str) -> tuple[str, str] | None:
    """用 refresh token 换取新的 token 对。

    Args:
        refresh: 用户的 refresh token 字符串

    Returns:
        (新 access_token, 新 refresh_token) 元组；refresh token 无效时返回 None
    """
    payload = decode_token(refresh)
    if not payload or payload.get("type") != "refresh":
        return None
    data = {"sub": payload.get("sub"), "username": payload.get("username")}
    return (
        create_access_token(data),
        create_refresh_token(data),
    )
