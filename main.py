import sqlite3
import ipaddress
import threading

from fastapi import FastAPI
from datetime import datetime, timezone
from network import ping_device
from database import init_database
from pydantic import BaseModel
from fastapi import HTTPException
from database import get_connection
from contextlib import asynccontextmanager
from monitor import start_monitoring
from fastapi.responses import FileResponse

@asynccontextmanager
async def lifespan(app):
    init_database()

    stop_event = threading.Event()
    monitor_thread = start_monitoring(stop_event)

    yield

    stop_event.set()
    monitor_thread.join(timeout=5)

app = FastAPI(
    title="RouteVexa",
    description="Open-source network monitoring and management platform",
    version="0.4.0",
    lifespan=lifespan
)

@app.get("/dashboard", include_in_schema=False)
def dashboard():
    return FileResponse("static/dashboard.html")

class DeviceCreate(BaseModel):
    name: str
    ip: str


@app.get("/")
def home():
    return {
        "application": "RouteVexa",
        "status": "running",
        "version": "0.4.0",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

@app.get("/ping/{ip}")
def ping(ip: str):
    return ping_device(ip)

@app.post("/devices", status_code=201)
def create_device(device: DeviceCreate):
    try:
        ip = str(ipaddress.IPv4Address(device.ip))  # Validate IP address
    except ipaddress.AddressValueError:
        raise HTTPException(status_code=400, detail="Invalid IP address format")

    if not device.name.strip():
        raise HTTPException(status_code=400, detail="Device name cannot be empty")

    try:
        with get_connection() as connection:
            cursor = connection.execute("INSERT INTO devices (name, ip) VALUES (?, ?)", (device.name.strip(), ip))
            device_id = cursor.lastrowid

    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Device IP already registered")

    return {"id": device_id, "name": device.name.strip(), "ip": ip, "status": "registered"}

@app.get("/devices")
def list_devices():
    with get_connection() as connection:
        cursor = connection.execute(
            """
            SELECT
                d.id,
                d.name,
                d.ip,
                d.created_at,
                d.status,
                d.last_checked,
                (
                    SELECT mh.latency_ms
                    FROM monitoring_history mh
                    WHERE mh.device_id = d.id
                    ORDER BY mh.id DESC
                    LIMIT 1
                ) AS latency_ms
            FROM devices d
            ORDER BY d.id
            """
        )
        devices = cursor.fetchall()

    return {
        "total": len(devices),
        "devices": [dict(device) for device in devices],
    }

@app.get("/devices/{device_id}")
def get_device(device_id: int):
    with get_connection() as connection:
        cursor = connection.execute(
            "SELECT id, name, ip, created_at, status, last_checked FROM devices WHERE id = ?",
            (device_id,)
        )
        device = cursor.fetchone()

    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")

    return dict(device)

@app.delete("/devices/{device_id}")
def delete_device(device_id: int):
    with get_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM devices WHERE id = ?",
            (device_id,)
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Device not found")

    return {"message": "Device deleted successfully", "id": device_id}

@app.get("/devices/{device_id}/history")
def get_device_history(device_id: int):
    with get_connection() as connection:
        history = connection.execute(
            """
            SELECT id, device_id, status, latency_ms, checked_at
            FROM monitoring_history
            WHERE device_id = ?
            ORDER BY checked_at DESC, id DESC
            """,
            (device_id,)
        ).fetchall()

    return {
        "device_id": device_id,
        "total": len(history),
        "history": [dict(record) for record in history]
    }