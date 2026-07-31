from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=100, description="出题主题")
    difficulty: str = Field(default="medium", pattern=r"^(easy|medium|hard)$", description="题目难度")
    count: int = Field(default=3, ge=1, le=10, description="生成数量")