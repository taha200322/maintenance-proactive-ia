-- ============================================================================
-- Maintenance Proactif du Parc Informatique par IA
-- Database Schema — PostgreSQL
-- ============================================================================
-- 
-- Design Decisions:
-- 1. All tables use UUID primary keys (globally unique, safe for distributed systems)
-- 2. Timestamps use TIMESTAMPTZ (timezone-aware) for multi-location support
-- 3. Metrics table is the largest — indexed on (device_id, timestamp) for fast queries
-- 4. JSONB for contributing_features allows flexible AI output without schema changes
-- 5. Enum types enforce data integrity at the DB level
-- 6. CASCADE deletes ensure referential integrity (e.g., deleting a device cleans metrics)
-- ============================================================================

-- ---------------------------------------------------------------------------
-- ENUM TYPES
-- ---------------------------------------------------------------------------

CREATE TYPE user_role AS ENUM ('admin', 'viewer');

CREATE TYPE device_status AS ENUM (
    'online',
    'offline',
    'warning',
    'critical',
    'maintenance'
);

CREATE TYPE alert_severity AS ENUM (
    'low',
    'medium',
    'high',
    'critical'
);

CREATE TYPE alert_status AS ENUM (
    'active',
    'acknowledged',
    'resolved',
    'suppressed'
);

CREATE TYPE risk_level AS ENUM (
    'low',
    'medium',
    'high',
    'critical'
);

CREATE TYPE recommendation_priority AS ENUM (
    'low',
    'medium',
    'high',
    'urgent'
);

CREATE TYPE recommendation_category AS ENUM (
    'hardware',
    'software',
    'security',
    'performance',
    'storage',
    'network'
);

CREATE TYPE recommendation_status AS ENUM (
    'pending',
    'in_progress',
    'completed',
    'dismissed'
);

CREATE TYPE event_level AS ENUM (
    'info',
    'warning',
    'error',
    'critical'
);

-- ---------------------------------------------------------------------------
-- TABLE: users
-- ---------------------------------------------------------------------------
-- Purpose: Stores admin and viewer accounts for the dashboard.
-- Why: Separate from devices — humans who log into the web interface.
-- ---------------------------------------------------------------------------

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255) NOT NULL,
    role            user_role NOT NULL DEFAULT 'admin',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for login lookups
CREATE INDEX idx_users_email ON users(email);

-- ---------------------------------------------------------------------------
-- TABLE: devices
-- ---------------------------------------------------------------------------
-- Purpose: Registry of all monitored computers.
-- Why: Central reference — metrics, alerts, predictions all link back here.
-- Note: Hardware info is a JSONB blob because different machines have
--       different specs (varying numbers of disks, GPUs, etc.)
-- ---------------------------------------------------------------------------

CREATE TABLE devices (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hostname        VARCHAR(255) NOT NULL UNIQUE,
    os_name         VARCHAR(255),           -- e.g. "Windows 10 Pro"
    os_version      VARCHAR(255),           -- e.g. "22H2 (19045.3803)"
    os_architecture VARCHAR(50),            -- e.g. "AMD64"
    ip_address      INET,                   -- PostgreSQL INET type for IPv4/IPv6
    mac_address     VARCHAR(17),            -- e.g. "AA:BB:CC:DD:EE:FF"
    cpu_model       VARCHAR(255),           -- e.g. "Intel Core i7-10700K"
    cpu_cores       INTEGER,
    ram_total_gb    NUMERIC(6,2),           -- Total RAM in GB
    disk_info       JSONB DEFAULT '{}',     -- [{"mount": "C:", "total_gb": 512}, ...]
    gpu_info        VARCHAR(255),           -- Optional GPU model
    status          device_status NOT NULL DEFAULT 'offline',
    health_score    NUMERIC(5,2) DEFAULT 100.00,  -- 0.00 (dead) to 100.00 (perfect)
    risk_level      risk_level NOT NULL DEFAULT 'low',
    last_seen       TIMESTAMPTZ,
    agent_version   VARCHAR(50),            -- Version of installed agent
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Common query patterns
CREATE INDEX idx_devices_status ON devices(status);
CREATE INDEX idx_devices_risk_level ON devices(risk_level);
CREATE INDEX idx_devices_hostname ON devices(hostname);

-- ---------------------------------------------------------------------------
-- TABLE: metrics
-- ---------------------------------------------------------------------------
-- Purpose: Time-series storage of all collected performance metrics.
-- Why: This is the raw data the AI analyzes. One row per collection cycle per device.
-- Growth: ~1440 rows/day/device at 60s interval. 50 devices = 72,000 rows/day.
-- Retention: We'll implement a cleanup job (default 30 days) in the backend.
-- ---------------------------------------------------------------------------

CREATE TABLE metrics (
    id              BIGSERIAL PRIMARY KEY,
    device_id       UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Core metrics (always available)
    cpu_percent     NUMERIC(5,2) NOT NULL,          -- 0.00 to 100.00
    ram_percent     NUMERIC(5,2) NOT NULL,          -- 0.00 to 100.00
    ram_used_gb     NUMERIC(8,2),                   -- Absolute RAM used in GB
    disk_percent    NUMERIC(5,2),                   -- 0.00 to 100.00 (max across partitions)
    
    -- Extended metrics (may be NULL if not available)
    disk_health     VARCHAR(50),                    -- e.g. "OK", "Warning", "Degraded"
    cpu_temp        NUMERIC(5,1),                   -- Celsius, NULL if sensor unavailable
    net_bytes_sent  BIGINT,                         -- Bytes sent since agent start
    net_bytes_recv  BIGINT,                         -- Bytes received since agent start
    process_count   INTEGER,                        -- Number of running processes
    uptime_seconds  BIGINT,                         -- Seconds since last boot
    
    -- Optional: top processes as JSONB
    top_processes   JSONB                           -- [{"name": "chrome", "cpu": 15.2, "ram": 8.5}, ...]
);

-- CRITICAL: This index makes time-range queries fast.
-- Without it, querying "last 24h of metrics for device X" would do a full table scan.
CREATE INDEX idx_metrics_device_timestamp ON metrics(device_id, timestamp DESC);

-- Index for AI batch queries (fetch all devices' latest metrics)
CREATE INDEX idx_metrics_timestamp ON metrics(timestamp DESC);

-- Partial index for anomaly-related queries (metrics with high CPU)
CREATE INDEX idx_metrics_high_cpu ON metrics(device_id, timestamp DESC) WHERE cpu_percent > 90.0;

-- ---------------------------------------------------------------------------
-- TABLE: system_events
-- ---------------------------------------------------------------------------
-- Purpose: Important Windows Event Log entries forwarded by the agent.
-- Why: Event logs provide context beyond metrics (e.g., disk errors, blue screens,
--       service failures). These help explain *why* anomalies occur.
-- ---------------------------------------------------------------------------

CREATE TABLE system_events (
    id              BIGSERIAL PRIMARY KEY,
    device_id       UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    timestamp       TIMESTAMPTZ NOT NULL,
    event_level     event_level NOT NULL,
    event_source    VARCHAR(255) NOT NULL,         -- e.g. "disk", "kernel-power", "Application Error"
    event_id        INTEGER,                        -- Windows Event ID
    message         TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_events_device_timestamp ON system_events(device_id, timestamp DESC);
CREATE INDEX idx_events_level ON system_events(event_level);

-- ---------------------------------------------------------------------------
-- TABLE: agent_credentials
-- ---------------------------------------------------------------------------
-- Purpose: Stores API keys used by monitoring agents to authenticate.
-- Why: Each agent needs a unique, revocable credential. We store only the HASH
--       of the API key, never the key itself (same principle as password hashing).
-- ---------------------------------------------------------------------------

CREATE TABLE agent_credentials (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id       UUID REFERENCES devices(id) ON DELETE SET NULL,
    label           VARCHAR(255) NOT NULL,         -- Human-readable name for the key
    api_key_hash    VARCHAR(255) NOT NULL,          -- SHA-256 hash of the API key
    api_key_prefix  VARCHAR(8) NOT NULL,            -- First 8 chars for identification (e.g. "pk_live_ab")
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_used_at    TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,                    -- Optional expiration
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_agent_creds_prefix ON agent_credentials(api_key_prefix);
CREATE INDEX idx_agent_creds_active ON agent_credentials(is_active) WHERE is_active = TRUE;

-- ---------------------------------------------------------------------------
-- TABLE: alerts
-- ---------------------------------------------------------------------------
-- Purpose: Stores alerts triggered by threshold breaches or AI-detected anomalies.
-- Why: Provides a persistent record of issues that admins can track, acknowledge,
--       and resolve. Enables alert history and SLA tracking.
-- ---------------------------------------------------------------------------

CREATE TABLE alerts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id       UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    severity        alert_severity NOT NULL,
    title           VARCHAR(500) NOT NULL,
    message         TEXT NOT NULL,
    
    -- What triggered this alert
    alert_source    VARCHAR(50) NOT NULL DEFAULT 'threshold',  -- 'threshold' or 'ai'
    metric_name     VARCHAR(100),                  -- e.g. 'cpu_percent'
    current_value   NUMERIC(10,2),                 -- The value that triggered it
    threshold_value NUMERIC(10,2),                 -- The threshold that was crossed
    
    -- Lifecycle
    status          alert_status NOT NULL DEFAULT 'active',
    acknowledged_by UUID REFERENCES users(id) ON DELETE SET NULL,
    acknowledged_at TIMESTAMPTZ,
    resolved_at     TIMESTAMPTZ,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_alerts_device ON alerts(device_id);
CREATE INDEX idx_alerts_status ON alerts(status);
CREATE INDEX idx_alerts_severity ON alerts(severity);
CREATE INDEX idx_alerts_created ON alerts(created_at DESC);

-- ---------------------------------------------------------------------------
-- TABLE: predictions
-- ---------------------------------------------------------------------------
-- Purpose: Stores AI/ML analysis results for each analysis cycle.
-- Why: Persists anomaly scores, health scores, and feature contributions so we can
--       (1) display them on the dashboard, (2) track trends over time,
--       (3) audit AI decisions for explainability.
-- ---------------------------------------------------------------------------

CREATE TABLE predictions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id               UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    timestamp               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- AI output
    anomaly_score           NUMERIC(8,4) NOT NULL,  -- -1 to 1 (Isolation Forest score)
    is_anomaly              BOOLEAN NOT NULL DEFAULT FALSE,
    health_score            NUMERIC(5,2) NOT NULL,  -- 0.00 to 100.00
    risk_level              risk_level NOT NULL,
    
    -- Explainability: which features contributed most to the anomaly?
    -- Format: [{"feature": "cpu_percent", "importance": 0.35, "value": 95.2}, ...]
    contributing_features   JSONB DEFAULT '[]',
    
    -- Model metadata
    model_version           VARCHAR(50) NOT NULL DEFAULT 'isolation-forest-v1',
    confidence              NUMERIC(5,4),           -- 0.0000 to 1.0000 (how confident)
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- For fetching the latest prediction per device (dashboard overview)
CREATE INDEX idx_predictions_device_timestamp ON predictions(device_id, timestamp DESC);
CREATE INDEX idx_predictions_anomaly ON predictions(is_anomaly) WHERE is_anomaly = TRUE;

-- ---------------------------------------------------------------------------
-- TABLE: maintenance_recommendations
-- ---------------------------------------------------------------------------
-- Purpose: Actionable maintenance suggestions generated from AI analysis.
-- Why: Bridges the gap between "something looks wrong" (prediction) and
--       "here's what you should do about it" (recommendation).
-- ---------------------------------------------------------------------------

CREATE TABLE maintenance_recommendations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id       UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    prediction_id   UUID REFERENCES predictions(id) ON DELETE SET NULL,
    
    title           VARCHAR(500) NOT NULL,
    description     TEXT NOT NULL,
    priority        recommendation_priority NOT NULL DEFAULT 'medium',
    category        recommendation_category NOT NULL,
    
    -- Lifecycle
    status          recommendation_status NOT NULL DEFAULT 'pending',
    assigned_to     UUID REFERENCES users(id) ON DELETE SET NULL,
    due_date        DATE,
    completed_at    TIMESTAMPTZ,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_recs_device ON maintenance_recommendations(device_id);
CREATE INDEX idx_recs_status ON maintenance_recommendations(status);
CREATE INDEX idx_recs_priority ON maintenance_recommendations(priority);

-- ---------------------------------------------------------------------------
-- HELPER FUNCTIONS
-- ---------------------------------------------------------------------------

-- Auto-update updated_at timestamp on row modification
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply the trigger to all tables with updated_at
CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_devices_updated_at BEFORE UPDATE ON devices
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_recs_updated_at BEFORE UPDATE ON maintenance_recommendations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ---------------------------------------------------------------------------
-- VIEWS (for common dashboard queries)
-- ---------------------------------------------------------------------------

-- Latest metrics per device (used by dashboard overview)
-- This avoids the need for complex subqueries in application code.
CREATE OR REPLACE VIEW v_latest_metrics AS
SELECT DISTINCT ON (device_id)
    device_id,
    cpu_percent,
    ram_percent,
    ram_used_gb,
    disk_percent,
    disk_health,
    cpu_temp,
    net_bytes_sent,
    net_bytes_recv,
    process_count,
    uptime_seconds,
    timestamp
FROM metrics
ORDER BY device_id, timestamp DESC;

-- Device health summary (used by dashboard overview)
CREATE OR REPLACE VIEW v_device_health AS
SELECT 
    d.id AS device_id,
    d.hostname,
    d.os_name,
    d.ip_address,
    d.status,
    d.health_score,
    d.risk_level,
    d.last_seen,
    lm.cpu_percent,
    lm.ram_percent,
    lm.disk_percent,
    lm.cpu_temp,
    (SELECT COUNT(*) FROM alerts a WHERE a.device_id = d.id AND a.status = 'active') AS active_alerts_count
FROM devices d
LEFT JOIN v_latest_metrics lm ON lm.device_id = d.id;
