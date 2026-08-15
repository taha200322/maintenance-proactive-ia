from sqlalchemy import BigInteger, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
import uuid

from app.core.database import Base


class SystemEvent(Base):
    """
    An important Windows Event Log entry forwarded by the monitoring agent.
    
    The agent filters events locally (only errors, warnings, critical) and
    sends them to the backend. This provides context BEYOND what metrics
    show — e.g., a disk error event explains WHY disk health is degrading.
    
    Examples of useful events:
    - Event ID 7 (disk): "The device has a bad block"
    - Event ID 41 (kernel-power): Unexpected shutdown (possible power issue)
    - Event ID 1001 (Windows Error Reporting): Application crash
    """
    __tablename__ = "system_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_level: Mapped[str] = mapped_column(
        ENUM("info", "warning", "error", "critical", name="event_level"), nullable=False
    )
    event_source: Mapped[str] = mapped_column(String(255), nullable=False)
    event_id: Mapped[int | None] = mapped_column(Integer)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationship
    device = relationship("Device", back_populates="system_events")
