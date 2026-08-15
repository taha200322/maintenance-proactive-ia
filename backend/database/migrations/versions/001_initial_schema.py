"""initial schema - all tables, enums, indexes, views, triggers

Revision ID: 001_initial
Revises: None
Create Date: 2025-01-01

This is the initial migration that creates the complete database schema.
It mirrors database/schema.sql exactly.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ========== ENUM TYPES ==========
    user_role_enum = postgresql.ENUM(
        'admin', 'viewer', name='user_role', create_type=False
    )
    device_status_enum = postgresql.ENUM(
        'online', 'offline', 'warning', 'critical', 'maintenance',
        name='device_status', create_type=False
    )
    alert_severity_enum = postgresql.ENUM(
        'low', 'medium', 'high', 'critical', name='alert_severity', create_type=False
    )
    alert_status_enum = postgresql.ENUM(
        'active', 'acknowledged', 'resolved', 'suppressed',
        name='alert_status', create_type=False
    )
    risk_level_enum = postgresql.ENUM(
        'low', 'medium', 'high', 'critical', name='risk_level', create_type=False
    )
    rec_priority_enum = postgresql.ENUM(
        'low', 'medium', 'high', 'urgent', name='recommendation_priority', create_type=False
    )
    rec_category_enum = postgresql.ENUM(
        'hardware', 'software', 'security', 'performance', 'storage', 'network',
        name='recommendation_category', create_type=False
    )
    rec_status_enum = postgresql.ENUM(
        'pending', 'in_progress', 'completed', 'dismissed',
        name='recommendation_status', create_type=False
    )
    event_level_enum = postgresql.ENUM(
        'info', 'warning', 'error', 'critical', name='event_level', create_type=False
    )

    user_role_enum.create(op.get_bind(), checkfirst=True)
    device_status_enum.create(op.get_bind(), checkfirst=True)
    alert_severity_enum.create(op.get_bind(), checkfirst=True)
    alert_status_enum.create(op.get_bind(), checkfirst=True)
    risk_level_enum.create(op.get_bind(), checkfirst=True)
    rec_priority_enum.create(op.get_bind(), checkfirst=True)
    rec_category_enum.create(op.get_bind(), checkfirst=True)
    rec_status_enum.create(op.get_bind(), checkfirst=True)
    event_level_enum.create(op.get_bind(), checkfirst=True)

    # ========== TABLES ==========

    # --- users ---
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('role', user_role_enum, nullable=False, server_default='admin'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_users_email', 'users', ['email'])

    # --- devices ---
    op.create_table(
        'devices',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('hostname', sa.String(255), unique=True, nullable=False),
        sa.Column('os_name', sa.String(255)),
        sa.Column('os_version', sa.String(255)),
        sa.Column('os_architecture', sa.String(50)),
        sa.Column('ip_address', postgresql.INET),
        sa.Column('mac_address', sa.String(17)),
        sa.Column('cpu_model', sa.String(255)),
        sa.Column('cpu_cores', sa.Integer()),
        sa.Column('ram_total_gb', sa.Numeric(6, 2)),
        sa.Column('disk_info', postgresql.JSONB, server_default='{}'),
        sa.Column('gpu_info', sa.String(255)),
        sa.Column('status', device_status_enum, nullable=False, server_default='offline'),
        sa.Column('health_score', sa.Numeric(5, 2), server_default='100.00'),
        sa.Column('risk_level', risk_level_enum, nullable=False, server_default='low'),
        sa.Column('last_seen', sa.DateTime(timezone=True)),
        sa.Column('agent_version', sa.String(50)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_devices_status', 'devices', ['status'])
    op.create_index('idx_devices_risk_level', 'devices', ['risk_level'])
    op.create_index('idx_devices_hostname', 'devices', ['hostname'])

    # --- metrics ---
    op.create_table(
        'metrics',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('device_id', postgresql.UUID(as_uuid=True),
                   sa.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('cpu_percent', sa.Numeric(5, 2), nullable=False),
        sa.Column('ram_percent', sa.Numeric(5, 2), nullable=False),
        sa.Column('ram_used_gb', sa.Numeric(8, 2)),
        sa.Column('disk_percent', sa.Numeric(5, 2)),
        sa.Column('disk_health', sa.String(50)),
        sa.Column('cpu_temp', sa.Numeric(5, 1)),
        sa.Column('net_bytes_sent', sa.BigInteger()),
        sa.Column('net_bytes_recv', sa.BigInteger()),
        sa.Column('process_count', sa.Integer()),
        sa.Column('uptime_seconds', sa.BigInteger()),
        sa.Column('top_processes', postgresql.JSONB),
    )
    op.create_index('idx_metrics_device_timestamp', 'metrics', ['device_id', sa.text('timestamp DESC')])
    op.create_index('idx_metrics_timestamp', 'metrics', [sa.text('timestamp DESC')])

    # --- system_events ---
    op.create_table(
        'system_events',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('device_id', postgresql.UUID(as_uuid=True),
                   sa.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('event_level', event_level_enum, nullable=False),
        sa.Column('event_source', sa.String(255), nullable=False),
        sa.Column('event_id', sa.Integer()),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_events_device_timestamp', 'system_events', ['device_id', sa.text('timestamp DESC')])
    op.create_index('idx_events_level', 'system_events', ['event_level'])

    # --- agent_credentials ---
    op.create_table(
        'agent_credentials',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('device_id', postgresql.UUID(as_uuid=True),
                   sa.ForeignKey('devices.id', ondelete='SET NULL')),
        sa.Column('label', sa.String(255), nullable=False),
        sa.Column('api_key_hash', sa.String(255), nullable=False),
        sa.Column('api_key_prefix', sa.String(8), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('last_used_at', sa.DateTime(timezone=True)),
        sa.Column('expires_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_agent_creds_prefix', 'agent_credentials', ['api_key_prefix'])
    op.create_index('idx_agent_creds_active', 'agent_credentials', ['is_active'],
                    postgresql_where=sa.text('is_active = true'))

    # --- alerts ---
    op.create_table(
        'alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('device_id', postgresql.UUID(as_uuid=True),
                   sa.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False),
        sa.Column('severity', alert_severity_enum, nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('alert_source', sa.String(50), server_default='threshold'),
        sa.Column('metric_name', sa.String(100)),
        sa.Column('current_value', sa.Numeric(10, 2)),
        sa.Column('threshold_value', sa.Numeric(10, 2)),
        sa.Column('status', alert_status_enum, nullable=False, server_default='active'),
        sa.Column('acknowledged_by', postgresql.UUID(as_uuid=True),
                   sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True)),
        sa.Column('resolved_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_alerts_device', 'alerts', ['device_id'])
    op.create_index('idx_alerts_status', 'alerts', ['status'])
    op.create_index('idx_alerts_severity', 'alerts', ['severity'])
    op.create_index('idx_alerts_created', 'alerts', [sa.text('created_at DESC')])

    # --- predictions ---
    op.create_table(
        'predictions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('device_id', postgresql.UUID(as_uuid=True),
                   sa.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('anomaly_score', sa.Numeric(8, 4), nullable=False),
        sa.Column('is_anomaly', sa.Boolean(), server_default='false'),
        sa.Column('health_score', sa.Numeric(5, 2), nullable=False),
        sa.Column('risk_level', risk_level_enum, nullable=False),
        sa.Column('contributing_features', postgresql.JSONB, server_default='[]'),
        sa.Column('model_version', sa.String(50), server_default='isolation-forest-v1'),
        sa.Column('confidence', sa.Numeric(5, 4)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_predictions_device_timestamp', 'predictions',
                    ['device_id', sa.text('timestamp DESC')])

    # --- maintenance_recommendations ---
    op.create_table(
        'maintenance_recommendations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('device_id', postgresql.UUID(as_uuid=True),
                   sa.ForeignKey('devices.id', ondelete='CASCADE'), nullable=False),
        sa.Column('prediction_id', postgresql.UUID(as_uuid=True),
                   sa.ForeignKey('predictions.id', ondelete='SET NULL')),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('priority', rec_priority_enum, server_default='medium'),
        sa.Column('category', rec_category_enum, nullable=False),
        sa.Column('status', rec_status_enum, server_default='pending'),
        sa.Column('assigned_to', postgresql.UUID(as_uuid=True),
                   sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('due_date', sa.Date()),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_recs_device', 'maintenance_recommendations', ['device_id'])
    op.create_index('idx_recs_status', 'maintenance_recommendations', ['status'])
    op.create_index('idx_recs_priority', 'maintenance_recommendations', ['priority'])

    # ========== TRIGGER: updated_at auto-update ==========
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER trg_users_updated_at
            BEFORE UPDATE ON users
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)
    op.execute("""
        CREATE TRIGGER trg_devices_updated_at
            BEFORE UPDATE ON devices
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)
    op.execute("""
        CREATE TRIGGER trg_recs_updated_at
            BEFORE UPDATE ON maintenance_recommendations
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)

    # ========== VIEWS ==========
    op.execute("""
        CREATE OR REPLACE VIEW v_latest_metrics AS
        SELECT DISTINCT ON (device_id)
            device_id, cpu_percent, ram_percent, ram_used_gb, disk_percent,
            disk_health, cpu_temp, net_bytes_sent, net_bytes_recv,
            process_count, uptime_seconds, timestamp
        FROM metrics
        ORDER BY device_id, timestamp DESC;
    """)

    op.execute("""
        CREATE OR REPLACE VIEW v_device_health AS
        SELECT
            d.id AS device_id, d.hostname, d.os_name, d.ip_address,
            d.status, d.health_score, d.risk_level, d.last_seen,
            lm.cpu_percent, lm.ram_percent, lm.disk_percent, lm.cpu_temp,
            (SELECT COUNT(*) FROM alerts a WHERE a.device_id = d.id AND a.status = 'active')
                AS active_alerts_count
        FROM devices d
        LEFT JOIN v_latest_metrics lm ON lm.device_id = d.id;
    """)


def downgrade() -> None:
    # Drop in reverse order (views, triggers, tables, enums)
    op.execute("DROP VIEW IF EXISTS v_device_health")
    op.execute("DROP VIEW IF EXISTS v_latest_metrics")
    op.execute("DROP TRIGGER IF EXISTS trg_recs_updated_at ON maintenance_recommendations")
    op.execute("DROP TRIGGER IF EXISTS trg_devices_updated_at ON devices")
    op.execute("DROP TRIGGER IF EXISTS trg_users_updated_at ON users")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")

    op.drop_table('maintenance_recommendations')
    op.drop_table('predictions')
    op.drop_table('alerts')
    op.drop_table('agent_credentials')
    op.drop_table('system_events')
    op.drop_table('metrics')
    op.drop_table('devices')
    op.drop_table('users')

    # Drop enums
    for enum_name in [
        'recommendation_status', 'recommendation_category', 'recommendation_priority',
        'risk_level', 'alert_status', 'alert_severity', 'event_level',
        'device_status', 'user_role'
    ]:
        postgresql.ENUM(name=enum_name).drop(op.get_bind(), checkfirst=True)
