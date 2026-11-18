"""Waits for the database, then applies Alembic migrations.

Usage: python migrate.py
"""
import sys
import time
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from database import engine

ROOT = Path(__file__).resolve().parent


def wait_for_database(attempts: int = 30) -> None:
    for attempt in range(1, attempts + 1):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return
        except OperationalError as error:
            if attempt == attempts:
                print(f"Database connection failed: {error}", file=sys.stderr)
                raise SystemExit(1) from error
            print(f"Waiting for database ({attempt}/{attempts})...", file=sys.stderr)
            time.sleep(1)


if __name__ == "__main__":
    wait_for_database()
    command.upgrade(Config(str(ROOT / "alembic.ini")), "head")
