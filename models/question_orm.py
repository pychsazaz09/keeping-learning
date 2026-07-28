from datetime import datetime

from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column

from models.__init__ import Base


class QuestionTable(Base):
    __tablename__ = "question"

    id: Mapped[str] = mapped_column(String(12), primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    tags: Mapped[str] = mapped_column(String(500), default="")
    difficulty: Mapped[str] = mapped_column(String(20), default="medium")
    answer: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now()
    )  # 数据库层面默认值
