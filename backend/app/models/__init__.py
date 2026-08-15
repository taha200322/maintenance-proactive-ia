"""
ORM Models — Import all models here so Alembic can discover them.

IMPORTANT: Any new model file MUST be imported here,
otherwise Alembic won't detect it for migrations.
"""

from app.models.user import User
from app.models.device import Device
from app.models.metric import Metric
from app.models.system_event import SystemEvent
from app.models.alert import Alert
from app.models.prediction import Prediction
from app.models.maintenance_recommendation import MaintenanceRecommendation
from app.models.agent_credential import AgentCredential

__all__ = [
    "User",
    "Device",
    "Metric",
    "SystemEvent",
    "Alert",
    "Prediction",
    "MaintenanceRecommendation",
    "AgentCredential",
]
