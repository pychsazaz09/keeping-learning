from pydantic import BaseModel, Field


class QuestionCreate(BaseModel):
    """创建题目 — Field 校验确保数据合法性"""

    title: str = Field(
        min_length=2,
        max_length=500,
        description="题目标题",
    )
    tags: list[str] | None = Field(
        default=None,
        description="标签列表",
    )
    difficulty: str = Field(
        default="medium",
        pattern=r"^(easy|medium|hard)$",
        description="难度：easy / medium / hard",
    )
    answer: str = Field(
        default="",
        max_length=5000,
        description="参考答案",
    )


class QuestionResponse(BaseModel):
    """题目响应 — 返回给客户端的格式"""

    id: str
    title: str
    tags: list[str] | None = None
    difficulty: str = ""
    answer: str = ""
