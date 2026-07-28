from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """注册请求 — Field 校验用户名和密码长度"""

    username: str = Field(
        min_length=2,
        max_length=30,
        description="用户名，2-30 字符",
    )
    password: str = Field(
        min_length=6,
        max_length=128,
        description="密码，6-128 字符",
    )


class UserLogin(BaseModel):
    """登录请求"""

    username: str = Field(min_length=1, description="用户名")
    password: str = Field(min_length=1, description="密码")


class ResponseToken(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    username: str
