"""Database engine/session setup (SQLite for dev/test, PostgreSQL via SS_DATABASE_URL)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def make_engine(url: str) -> Engine:
    kwargs: dict[str, Any] = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    engine = create_engine(url, future=True, **kwargs)
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _pragma(dbapi_con: Any, _rec: Any) -> None:
            cur = dbapi_con.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

    return engine


class Database:
    def __init__(self, url: str) -> None:
        self.engine = make_engine(url)
        self.factory = sessionmaker(self.engine, expire_on_commit=False, future=True)

    def session(self) -> Iterator[Session]:
        s = self.factory()
        try:
            yield s
        finally:
            s.close()

    def create_all(self) -> None:
        from . import models  # noqa: F401

        Base.metadata.create_all(self.engine)
