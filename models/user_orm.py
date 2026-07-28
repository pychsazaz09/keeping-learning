from datetime import datetime

from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column

from models.__init__ import Base


class UserTable(Base):

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(12), primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
