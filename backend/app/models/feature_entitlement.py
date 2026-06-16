from __future__ import annotations

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class FeatureEntitlement(Base):
    __tablename__ = "feature_entitlements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    feature_key: Mapped[str] = mapped_column(String(64), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    limit_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
