from collections.abc import Iterator
from datetime import UTC, datetime

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config.settings import settings


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None, microsecond=0)


class Base(DeclarativeBase):
    pass


def build_engine() -> Engine:
    options: dict = {"pool_pre_ping": True}
    if settings.db_connection == "sqlite":
        options["connect_args"] = {"check_same_thread": False}
    database_engine = create_engine(settings.database_url, **options)

    if database_engine.dialect.name == "sqlite":

        @event.listens_for(database_engine, "connect")
        def enable_foreign_keys(connection, _record) -> None:
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return database_engine


engine = build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
