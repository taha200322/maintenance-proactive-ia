from sqlalchemy import String, Integer, Numeric, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, INET, ENUM, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
import uuid

from app.core.database import Base


class Device(Base):
    """
    A monitored computer in the IT fleet.
    
    Central entity — metrics, alerts, predictions, and recommendations
    all reference this table via foreign keys.
    
    Key fields:
    - health_score: 0-100, computed by AI service, updated after each analysis
    - risk_level: low/medium/high/critical, derived from health_score + anomalies
    - status: online/offline/warning/critical/maintenance, updated by agent heartbeat
    - last_seen: timestamp of the last metric received from this device
    """
    __tablename__ = "devices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    hostname: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    os_name: Mapped[str | None] = mapped_column(String(255))
    os_version: Mapped[str | None] = mapped_column(String(255))
    os_architecture: Mapped[str | None] = mapped_column(String(50))
    ip_address: Mapped[str | None] = mapped_column(INET)
    mac_address: Mapped[str | None] = mapped_column(String(17))
    cpu_model: Mapped[str | None] = mapped_column(String(255))
    cpu_cores: Mapped[int | None] = mapped_column(Integer)
    ram_total_gb: Mapped[float | None] = mapped_column(Numeric(6, 2))
    disk_info: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    gpu_info: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(
        ENUM("online", "offline", "warning", "critical", "maintenance", name="device_status"),
        default="offline",
    )
    health_score: Mapped[float] = mapped_column(Numeric(5, 2), default=100.00)
    risk_level: Mapped[str] = mapped_column(
        ENUM("low", "medium", "high", "critical", name="risk_level"),
        default="low",
    )
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    agent_version: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    metrics = relationship("Metric", back_populates="device", cascade="all, delete-orphan")
    system_events = relationship("SystemEvent", back_populates="device", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="device", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="device", cascade="all, delete-orphan")
    recommendations = relationship("MaintenanceRecommendation", back_populates="device", cascade="all, delete-orphan")
    agent_credential = relationship("AgentCredential", back_populates="device", uselist=False)
