import sqlite3

DATABASE = "routevexa.db"


def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                ip TEXT NOT NULL UNIQUE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(devices)")
        }

        if "status" not in columns:
            connection.execute(
                "ALTER TABLE devices ADD COLUMN status TEXT DEFAULT 'unknown'"
            )

        if "last_checked" not in columns:
            connection.execute(
                "ALTER TABLE devices ADD COLUMN last_checked TEXT DEFAULT 'unknown'"
            )

        connection.execute("""
            CREATE TABLE IF NOT EXISTS monitoring_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                latency_ms REAL,
                checked_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (device_id)
                    REFERENCES devices(id)
                    ON DELETE CASCADE
            )
        """)