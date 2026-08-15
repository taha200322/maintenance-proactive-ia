from sqlalchemy import Numeric, Boolean, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ENUM, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
import uuid

from app.core.database import Base


class Prediction(Base):
    """
    AI/ML analysis result for a device at a point in time.
    
    Every time the AI service analyzes a device's metrics,
    a row is inserted here. This provides:
    
    1. Audit trail: what did the AI say, and when?
    2. Trending: how has the anomaly score changed over time?
    3. Explainability: contributing_features shows WHY it flagged something.
    
    anomaly_score: Isolation Forest output.
      - Close to -1: clearly normal (deep in a dense region)
      - Close to +1: clearly anomalous (easily isolated)
      - Close to 0: on the boundary
    
    contributing_features JSONB format:
    [
      {"feature": "cpu_percent", "importance": 0.35, "value": 95.2},
      {"feature": "ram_percent", "importance": 0.28, "value": 92.1},
      ...
    ]
    """
    __tablename__ = "predictions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # AI output
    anomaly_score: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, default=False)
    health_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    risk_level: Mapped[str] = mapped_column(
        ENUM("low", "medium", "high", "critical", name="risk_level"), nullable=False
    )

    # Explainability
    contributing_features: Mapped[dict | None] = mapped_column(JSONB, default=list)

    # Model metadata
    model_version: Mapped[str] = mapped_column(String(50), default="isolation-forest-v1")
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 4))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    device = relationship("Device", back_populates="predictions")
    recommendations = relationship(
        "MaintenanceRecommendation", back_populates="prediction"
    )
