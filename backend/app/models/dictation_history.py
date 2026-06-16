from sqlalchemy import DateTime, Integer, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from ..db import Base


class DictationHistory(Base):
    __tablename__ = "dictation_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(32), nullable=False, default="dictation")
    transcript: Mapped[str] = mapped_column(Text, nullable=False)
    ai_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="auto")
    pasted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    target_app: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
