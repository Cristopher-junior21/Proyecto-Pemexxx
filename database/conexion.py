"""Conexión local a la BD del sistema. Nunca subir .env a GitHub."""
import os
from pathlib import Path
from contextlib import contextmanager

import mysql.connector
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _config():
    return {
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", "cristopher"),
        "database": os.getenv("DB_NAME", "sistema_capacitacion_cangrejera"),
        "connection_timeout": 6,
        "charset": "utf8mb4",
    }


@contextmanager
def connection():
    conn = mysql.connector.connect(**_config())
    try:
        yield conn
    finally:
        conn.close()


def fetchall(query, params=()):
    with connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, params)
            return cursor.fetchall()
        finally:
            cursor.close()


def execute(query, params=()):
    with connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()


def test_connection():
    rows = fetchall("SELECT DATABASE() AS db_name")
    return rows[0]["db_name"]
