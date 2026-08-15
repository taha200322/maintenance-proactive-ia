from sqlalchemy import BigInteger, Numeric, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
import uuid

from app.core.database import Base


class Metric(Base):
    """
    A single snapshot of performance metrics from one device.
    
    One row is inserted every collection_interval seconds per device.
    At 60s interval, 50 devices = ~72,000 rows/day.
    
    Indexed on (device_id, timestamp DESC) for fast time-range queries.
    """
    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )

    # Core metrics (always present)
    cpu_percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    ram_percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    ram_used_gb: Mapped[float | None] = mapped_column(Numeric(8, 2))
    disk_percent: Mapped[float | None] = mapped_column(Numeric(5, 2))

    # Extended metrics (nullable — may not be available on all systems)
    disk_health: Mapped[str | None] = mapped_column()
    cpu_temp: Mapped[float | None] = mapped_column(Numeric(5, 1))
    net_bytes_sent: Mapped[int | None] = mapped_column(BigInteger)
    net_bytes_recv: Mapped[int | None] = mapped_column(BigInteger)
    process_count: Mapped[int | None] = mapped_column()
    uptime_seconds: Mapped[int | None] = mapped_column(BigInteger)
    top_processes: Mapped[dict | None] = mapped_column(JSONB)

    # Relationship
    device = relationship("Device", back_populates="metrics")
