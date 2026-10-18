import sqlite3
from pathlib import Path

DATABASE_DIRECTORY = Path(__file__).parent
DATABASE_PATH = DATABASE_DIRECTORY / "gaffer.db"
SCHEMA_PATH = DATABASE_DIRECTORY / "sql" / "schema.sql"


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    with get_connection() as connection:
        connection.executescript(SCHEMA_PATH.read_text())
