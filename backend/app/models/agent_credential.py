from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
import uuid

from app.core.database import Base


class AgentCredential(Base):
    """
    API key credential for a monitoring agent.
    
    Security model:
    - Agent receives a plaintext API key ONCE during registration
    - Only the SHA-256 HASH is stored in the database
    - api_key_prefix (first 8 chars) is stored for identification
    - On each request, agent sends key in Authorization header
    - Backend hashes the received key and compares to stored hash
    
    This is the same pattern as password storage, but using SHA-256
    instead of bcrypt because:
    1. API keys are already high-entropy (not susceptible to dictionary attacks)
    2. We need fast verification (agents send requests every 60 seconds)
    3. bcrypt's 100ms delay would add unnecessary latency at scale
    """
    __tablename__ = "agent_credentials"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="SET NULL")
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key_prefix: Mapped[str] = mapped_column(String(8), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationship
    device = relationship("Device", back_populates="agent_credential")
