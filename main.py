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
            "SELECT id, name, ip, created_at FROM devices ORDER BY id"
        )
        devices = cursor.fetchall()

        return {
            "total": len(devices),
            "devices": [dict(device) for device in devices]
        }

@app.get("/devices/{device_id}")
def get_device(device_id: int):
    with get_connection() as connection:
        cursor = connection.execute(
            "SELECT id, name, ip, created_at FROM devices WHERE id = ?",
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

