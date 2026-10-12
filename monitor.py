import threading
from database import get_connection
from network import ping_device


MONITOR_INTERVAL = 30


def monitor_devices():
    with get_connection() as connection:
        devices = connection.execute(
            "SELECT id, name, ip FROM devices"
            ).fetchall()

    for device in devices:
        result = ping_device(device["ip"])
        with get_connection() as connection:
            connection.execute(
                "UPDATE devices SET status = ?, last_checked = CURRENT_TIMESTAMP WHERE id = ?",
                (result["status"], device["id"])
            )

        print(
            f"[MONITOR] {device['name']} "
            f"({device['ip']}): {result['status']}"
        )


def start_monitoring(stop_event):
    monitor_thread = threading.Thread(
        target=monitor_loop,
        args=(stop_event,),
        daemon=True
    )
    monitor_thread.start()
    return monitor_thread


def monitor_loop(stop_event):
    while not stop_event.is_set():
        monitor_devices()
        stop_event.wait(MONITOR_INTERVAL)