"""ISP internet package catalogue (Phase 4).

Packages are administrator-configured. Nothing commercial is hard-coded —
operators add ISP / plan rows with advertised download and upload speeds.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class InternetPackage(Base):
    """One advertised broadband package for an ISP."""

    __tablename__ = "internet_packages"
    __table_args__ = (
        UniqueConstraint("isp_name", "package_name", name="uq_package_isp_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    isp_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    package_name: Mapped[str] = mapped_column(String(120), nullable=False)
    advertised_download_mbps: Mapped[float] = mapped_column(Float, nullable=False)
    advertised_upload_mbps: Mapped[float] = mapped_column(Float, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
        server_default=func.now(),
    )
