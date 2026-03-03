from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EngineerPerformance(Base):
    __tablename__ = "engineer_performance"
    __table_args__ = (
        UniqueConstraint(
            "engineer_name",
            "period_start",
            "period_end",
            name="uq_engineer_performance_period",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    engineer_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    total_incidents: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    resolved_incidents: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    breached_slas: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    sla_adherence_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    mttr_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    mtta_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    breach_p1: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    breach_p2: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    breach_p3: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    breach_p4: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    backlog_over_7_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    reopened_incidents: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    avg_resolution_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class VendorPerformance(Base):
    __tablename__ = "vendor_performance"
    __table_args__ = (
        UniqueConstraint("vendor", "period_start", "period_end", name="uq_vendor_performance_period"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    vendor: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    total_incidents: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    resolved_incidents: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    breached_slas: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    sla_adherence_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    mttr_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    mtta_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    breach_p1: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    breach_p2: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    breach_p3: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    breach_p4: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    backlog_over_7_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    reopened_incidents: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    avg_resolution_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
