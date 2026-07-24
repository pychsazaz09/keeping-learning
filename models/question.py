from uuid import uuid4

from pydantic import BaseModel, Field


class Question(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    title: str
    tags: list[str] = Field(default_factory=list)
    difficulty: str = "medium"
    answer: str = ""
