from sqlalchemy import String, Numeric, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
import uuid

from app.core.database import Base


class Alert(Base):
    """
    An alert triggered by a threshold breach or AI-detected anomaly.
    
    Alert lifecycle:
    active → acknowledged → resolved
    
    - active: new alert, visible in dashboard
    - acknowledged: admin has seen it, working on it
    - resolved: the issue is fixed
    - suppressed: admin chose to ignore (rare)
    
    alert_source distinguishes between:
    - 'threshold': a metric exceeded a static threshold (e.g., CPU > 95%)
    - 'ai': the AI model detected an anomalous pattern
    """
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )
    severity: Mapped[str] = mapped_column(
        ENUM("low", "medium", "high", "critical", name="alert_severity"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    message: Mapped[str] = mapped_column(String, nullable=False)

    # What triggered this alert
    alert_source: Mapped[str] = mapped_column(String(50), default="threshold")
    metric_name: Mapped[str | None] = mapped_column(String(100))
    current_value: Mapped[float | None] = mapped_column(Numeric(10, 2))
    threshold_value: Mapped[float | None] = mapped_column(Numeric(10, 2))

    # Lifecycle
    status: Mapped[str] = mapped_column(
        ENUM("active", "acknowledged", "resolved", "suppressed", name="alert_status"),
        default="active",
    )
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    device = relationship("Device", back_populates="alerts")
    acknowledged_by_user = relationship("User", back_populates="acknowledged_alerts", foreign_keys=[acknowledged_by])
