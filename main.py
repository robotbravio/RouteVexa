from fastapi import FastAPI
from datetime import datetime, timezone
from network import ping_device

app = FastAPI(
    title="RouteVexa",
    description="Open-source network monitoring and management platform",
    version="0.2.0",
)


@app.get("/")
def home():
    return {
        "application": "RouteVexa",
        "status": "running",
        "version": "0.2.0",
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