""" Seed Data Script — Populates the database with realistic demo data.

Usage:
    cd backend
    python -m database.seeds.seed_data

This creates:
- 1 admin user (admin@techcorp.local / admin123)
- 1 viewer user (viewer@techcorp.local / viewer123)
- 5 demo devices with realistic hardware specs
- 1 agent credential (for testing the monitoring agent)
- ~24 hours of simulated metrics for each device
- Some alerts and maintenance recommendations

ALL DATA IS CLEARLY LABELED AS DEMO DATA.
"""

import asyncio
import random
import uuid
import hashlib
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
import sqlalchemy as sa


# ============================================================
# CONFIGURATION
# ============================================================
DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/proactive_maintenance"
DEMO_DEVICES = 5
HOURS_OF_METRICS = 24  # Simulate 24 hours of data
METRICS_INTERVAL_SECONDS = 60  # One metric row per minute


# ============================================================
# DEMO DATA DEFINITIONS
# ============================================================

DEMO_USERS = [
    {
        "email": "admin@techcorp.local",
        "password_plain": "admin123",
        "full_name": "Administrateur Système",
        "role": "admin",
    },
    {
        "email": "viewer@techcorp.local",
        "password_plain": "viewer123",
        "full_name": "Jean Dupont",
        "role": "viewer",
    },
]

DEMO_DEVICE_SPECS = [
    {
        "hostname": "PC-ACCOUNTING-01",
        "os_name": "Windows 10 Pro",
        "os_version": "22H2 (19045.3803)",
        "os_architecture": "AMD64",
        "ip_address": "192.168.1.101",
        "mac_address": "AA:BB:CC:11:22:33",
        "cpu_model": "Intel Core i5-10400",
        "cpu_cores": 6,
        "ram_total_gb": 8.0,
        "disk_info": [
            {"mount": "C:", "total_gb": 256, "disk_type": "SSD"},
            {"mount": "D:", "total_gb": 1000, "disk_type": "HDD"},
        ],
        "status": "online",
        "health_score": 85.50,
        "risk_level": "low",
        # Normal usage pattern: moderate CPU/RAM
        "metric_profile": "normal",
    },
    {
        "hostname": "PC-DEV-01",
        "os_name": "Windows 11 Pro",
        "os_version": "23H2 (22631.3007)",
        "os_architecture": "AMD64",
        "ip_address": "192.168.1.102",
        "mac_address": "AA:BB:CC:44:55:66",
        "cpu_model": "AMD Ryzen 7 5800X",
        "cpu_cores": 8,
        "ram_total_gb": 32.0,
        "disk_info": [
            {"mount": "C:", "total_gb": 512, "disk_type": "NVMe SSD"},
        ],
        "status": "online",
        "health_score": 72.30,
        "risk_level": "medium",
        # High CPU/RAM (developer machine with IDEs, Docker, etc.)
        "metric_profile": "high_usage",
    },
    {
        "hostname": "PC-RECEPTION",
        "os_name": "Windows 10 Home",
        "os_version": "21H2 (19044.3803)",
        "os_architecture": "AMD64",
        "ip_address": "192.168.1.103",
        "mac_address": "AA:BB:CC:77:88:99",
        "cpu_model": "Intel Core i3-10100",
        "cpu_cores": 4,
        "ram_total_gb": 4.0,
        "disk_info": [
            {"mount": "C:", "total_gb": 256, "disk_type": "HDD"},
        ],
        "status": "warning",
        "health_score": 45.00,
        "risk_level": "high",
        # Old machine with high disk usage and occasional CPU spikes
        "metric_profile": "degraded",
    },
    {
        "hostname": "SRV-FILE-01",
        "os_name": "Windows Server 2022 Standard",
        "os_version": "21H2 (20348.2031)",
        "os_architecture": "AMD64",
        "ip_address": "192.168.1.200",
        "mac_address": "AA:BB:CC:AA:BB:CC",
        "cpu_model": "Intel Xeon E-2388G",
        "cpu_cores": 8,
        "ram_total_gb": 64.0,
        "disk_info": [
            {"mount": "C:", "total_gb": 256, "disk_type": "SSD"},
            {"mount": "D:", "total_gb": 4000, "disk_type": "HDD RAID"},
        ],
        "status": "online",
        "health_score": 92.00,
        "risk_level": "low",
        # File server — moderate CPU, low RAM, varying disk I/O
        "metric_profile": "server",
    },
    {
        "hostname": "PC-DIR-01",
        "os_name": "Windows 11 Pro",
        "os_version": "23H2 (22631.3007)",
        "os_architecture": "AMD64",
        "ip_address": "192.168.1.104",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "cpu_model": "Intel Core i7-12700K",
        "cpu_cores": 12,
        "ram_total_gb": 16.0,
        "disk_info": [
            {"mount": "C:", "total_gb": 512, "disk_type": "NVMe SSD"},
            {"mount": "D:", "total_gb": 2048, "disk_type": "SSD"},
        ],
        "status": "online",
        "health_score": 98.00,
        "risk_level": "low",
        # Executive machine — mostly idle, occasional Office usage
        "metric_profile": "idle",
    },
]

# Metric generation profiles (mean, std_dev) for realistic variation
METRIC_PROFILES = {
    "normal": {
        "cpu": (35, 12),
        "ram": (55, 8),
        "disk": (60, 0.5),
        "cpu_temp": (52, 4),
        "processes": (85, 10),
    },
    "high_usage": {
        "cpu": (72, 15),
        "ram": (82, 6),
        "disk": (55, 0.3),
        "cpu_temp": (68, 8),
        "processes": (150, 20),
    },
    "degraded": {
        "cpu": (55, 25),  # High variance = occasional spikes
        "ram": (78, 10),
        "disk": (89, 0.3),  # High disk usage
        "cpu_temp": (72, 12),  # Overheating tendency
        "processes": (120, 30),
    },
    "server": {
        "cpu": (25, 15),
        "ram": (45, 8),
        "disk": (65, 2),
        "cpu_temp": (45, 5),
        "processes": (60, 8),
    },
    "idle": {
        "cpu": (8, 6),
        "ram": (35, 5),
        "disk": (42, 0.2),
        "cpu_temp": (38, 3),
        "processes": (65, 5),
    },
}


def generate_metric_value(profile: dict, key: str) -> float:
    """Generate a realistic metric value using normal distribution."""
    mean, std = profile[key]
    value = random.gauss(mean, std)
    # Clamp to realistic bounds
    value = max(0, min(100, value))
    return round(value, 2)


def generate_api_key() -> tuple[str, str, str]:
    """Generate a random API key. Returns (plaintext, hash, prefix)."""
    import secrets
    plaintext = f"pk_live_{secrets.token_hex(24)}"
    key_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    prefix = plaintext[:8]
    return plaintext, key_hash, prefix


async def seed_database():
    """Main seeding function."""
    engine = create_async_engine(DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        print("[SEED] Starting database seeding...")

        # ------ 1. USERS ------
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        user_ids = {}
        for user_data in DEMO_USERS:
            user_id = uuid.uuid4()
            user_ids[user_data["role"]] = user_id
            await session.execute(
                sa.insert(sa.table("users")).values(
                    id=user_id,
                    email=user_data["email"],
                    password_hash=pwd_context.hash(user_data["password_plain"]),
                    full_name=user_data["full_name"],
                    role=user_data["role"],
                    is_active=True,
                )
            )
            print(f"[SEED]   User: {user_data['email']} ({user_data['role']})")

        # ------ 2. DEVICES ------
        device_ids = []
        now = datetime.now(timezone.utc)

        for spec in DEMO_DEVICE_SPECS:
            device_id = uuid.uuid4()
            device_ids.append(device_id)
            await session.execute(
                sa.insert(sa.table("devices")).values(
                    id=device_id,
                    hostname=spec["hostname"],
                    os_name=spec["os_name"],
                    os_version=spec["os_version"],
                    os_architecture=spec["os_architecture"],
                    ip_address=spec["ip_address"],
                    mac_address=spec["mac_address"],
                    cpu_model=spec["cpu_model"],
                    cpu_cores=spec["cpu_cores"],
                    ram_total_gb=spec["ram_total_gb"],
                    disk_info=spec["disk_info"],
                    status=spec["status"],
                    health_score=spec["health_score"],
                    risk_level=spec["risk_level"],
                    last_seen=now,
                    agent_version="1.0.0-demo",
                )
            )
            print(f"[SEED]   Device: {spec['hostname']} ({spec['status']}, health={spec['health_score']})")

        # ------ 3. METRICS (simulated time-series) ------
        total_metrics = 0
        for i, spec in enumerate(DEMO_DEVICE_SPECS):
            profile = METRIC_PROFILES[spec["metric_profile"]]
            device_id = device_ids[i]
            rows_per_device = (HOURS_OF_METRICS * 3600) // METRICS_INTERVAL_SECONDS

            # Batch insert for performance (1000 rows at a time)
            batch = []
            for j in range(rows_per_device):
                ts = now - timedelta(seconds=(rows_per_device - j) * METRICS_INTERVAL_SECONDS)
                cpu = generate_metric_value(profile, "cpu")
                ram = generate_metric_value(profile, "ram")
                disk = generate_metric_value(profile, "disk")
                temp = generate_metric_value(profile, "cpu_temp")
                procs = int(generate_metric_value(profile, "processes"))

                # Simulate some anomalies for the degraded machine
                if spec["metric_profile"] == "degraded" and random.random() < 0.05:
                    cpu = min(100, cpu + random.uniform(20, 35))

                batch.append({
                    "device_id": device_id,
                    "timestamp": ts,
                    "cpu_percent": cpu,
                    "ram_percent": ram,
                    "ram_used_gb": round(spec["ram_total_gb"] * ram / 100, 2),
                    "disk_percent": disk,
                    "disk_health": "Warning" if disk > 85 else "OK",
                    "cpu_temp": temp,
                    "net_bytes_sent": random.randint(100_000, 50_000_000),
                    "net_bytes_recv": random.randint(500_000, 200_000_000),
                    "process_count": procs,
                    "uptime_seconds": random.randint(86400, 2592000),
                })

                if len(batch) >= 1000:
                    await session.execute(sa.insert(sa.table("metrics")).values(batch))
                    total_metrics += len(batch)
                    batch = []

            if batch:
                await session.execute(sa.insert(sa.table("metrics")).values(batch))
                total_metrics += len(batch)

            print(f"[SEED]   Metrics: {spec['hostname']} - {rows_per_device} rows")

        print(f"[SEED]   Total metrics inserted: {total_metrics}")

        # ------ 4. AGENT CREDENTIAL ------
        api_key_plain, api_key_hash, api_key_prefix = generate_api_key()
        await session.execute(
            sa.insert(sa.table("agent_credentials")).values(
                id=uuid.uuid4(),
                device_id=device_ids[0],
                label="Demo Agent Key - PC-ACCOUNTING-01",
                api_key_hash=api_key_hash,
                api_key_prefix=api_key_prefix,
                is_active=True,
            )
        )
        print(f"[SEED]   Agent Credential: prefix={api_key_prefix}")
        print(f"[SEED]   >>> SAVE THIS API KEY (shown only once): {api_key_plain}")

        # ------ 5. SAMPLE ALERTS ------
        sample_alerts = [
            {
                "device_id": device_ids[2],  # PC-RECEPTION (degraded)
                "severity": "high",
                "title": "Disk usage critically high",
                "message": "Disk C: is at 89% usage. Consider cleaning up or expanding storage.",
                "alert_source": "threshold",
                "metric_name": "disk_percent",
                "current_value": 89.0,
                "threshold_value": 85.0,
                "status": "active",
            },
            {
                "device_id": device_ids[2],
                "severity": "critical",
                "title": "CPU temperature elevated",
                "message": "CPU temperature reached 84.3C. Check cooling system and ventilation.",
                "alert_source": "ai",
                "metric_name": "cpu_temp",
                "current_value": 84.3,
                "threshold_value": 75.0,
                "status": "active",
            },
            {
                "device_id": device_ids[1],  # PC-DEV-01
                "severity": "medium",
                "title": "High RAM usage detected",
                "message": "RAM usage has been above 80% for the last 2 hours. Consider closing unused applications or upgrading RAM.",
                "alert_source": "ai",
                "metric_name": "ram_percent",
                "current_value": 88.5,
                "threshold_value": 80.0,
                "status": "acknowledged",
            },
        ]

        for alert_data in sample_alerts:
            await session.execute(
                sa.insert(sa.table("alerts")).values(
                    id=uuid.uuid4(),
                    created_at=now - timedelta(hours=random.randint(1, 48)),
                    **alert_data,
                )
            )
        print(f"[SEED]   Alerts: {len(sample_alerts)} sample alerts")

        # ------ 6. SAMPLE RECOMMENDATIONS ------
        sample_recs = [
            {
                "device_id": device_ids[2],
                "title": "Replace failing hard drive",
                "description": "PC-RECEPTION has an HDD showing signs of degradation (high disk usage, slow response times). Recommend replacing with an SSD and migrating OS.",
                "priority": "urgent",
                "category": "hardware",
                "status": "pending",
                "due_date": (now + timedelta(days=7)).date(),
            },
            {
                "device_id": device_ids[2],
                "title": "Clean dust from cooling system",
                "description": "Elevated CPU temperatures suggest inadequate cooling. Clean dust from fans and heatsink, verify thermal paste.",
                "priority": "high",
                "category": "hardware",
                "status": "pending",
                "due_date": (now + timedelta(days=3)).date(),
            },
            {
                "device_id": device_ids[1],
                "title": "Upgrade RAM to 64GB",
                "description": "Development workstation consistently uses >80% RAM with IDE, Docker, and browser tabs open. Upgrading to 64GB would improve developer productivity.",
                "priority": "medium",
                "category": "hardware",
                "status": "pending",
                "due_date": (now + timedelta(days=30)).date(),
            },
        ]

        for rec_data in sample_recs:
            await session.execute(
                sa.insert(sa.table("maintenance_recommendations")).values(
                    id=uuid.uuid4(),
                    assigned_to=user_ids["admin"],
                    **rec_data,
                )
            )
        print(f"[SEED]   Recommendations: {len(sample_recs)} sample recommendations")

        # ------ COMMIT ------
        await session.commit()
        print("\n[SEED] ============================================")
        print("[SEED] Database seeded successfully!")
        print("[SEED] ============================================")
        print(f"[SEED]   Users: {len(DEMO_USERS)}")
        print(f"[SEED]   Devices: {len(DEMO_DEVICE_SPECS)}")
        print(f"[SEED]   Metrics: {total_metrics}")
        print(f"[SEED]   Alerts: {len(sample_alerts)}")
        print(f"[SEED]   Recommendations: {len(sample_recs)}")
        print(f"[SEED]")
        print(f"[SEED]   Admin login: admin@techcorp.local / admin123")
        print(f"[SEED]   Viewer login: viewer@techcorp.local / viewer123")
        print(f"[SEED]   Agent API Key: {api_key_plain}")
        print(f"[SEED] ============================================")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_database())
