"""FastAPI dependency that builds the request context with a managed DB session."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Request

from .deps import Ctx


def ctx_dep(request: Request) -> Iterator[Ctx]:
    db = request.app.state.database.factory()
    try:
        yield Ctx(request, db)
    finally:
        db.close()
