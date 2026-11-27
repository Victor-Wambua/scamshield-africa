"""Append-only, hash-chained audit log."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import DDL, event, select
from sqlalchemy.orm import Session

from .models import AuditLog, utcnow


class AuditImmutable(RuntimeError):
    pass


@event.listens_for(AuditLog, "before_update")
def _no_update(*_: Any) -> None:
    raise AuditImmutable("audit_log is append-only")


@event.listens_for(AuditLog, "before_delete")
def _no_delete(*_: Any) -> None:
    raise AuditImmutable("audit_log is append-only")


# Database-level protection (SQLite here; PostgreSQL trigger is in the Alembic migration)
for _name, _ev in (("noupd", "UPDATE"), ("nodel", "DELETE")):
    event.listen(
        AuditLog.__table__,
        "after_create",
        DDL(
            f"CREATE TRIGGER audit_{_name} BEFORE {_ev} ON audit_log "
            f"BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END"
        ).execute_if(dialect="sqlite"),
    )


def compute_hash(prev: str, row: AuditLog) -> str:
    payload = "|".join(
        [
            prev,
            row.ts.isoformat(),
            str(row.actor_id or ""),
            row.action,
            row.target_type,
            row.target_id,
            row.reason,
            json.dumps(row.detail, sort_keys=True, separators=(",", ":")),
        ]
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def record(
    db: Session,
    actor_id: int | None,
    action: str,
    target_type: str = "",
    target_id: Any = "",
    reason: str = "",
    detail: dict[str, Any] | None = None,
) -> AuditLog:
    last = db.scalar(select(AuditLog).order_by(AuditLog.id.desc()).limit(1))
    row = AuditLog(
        ts=utcnow(),
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        reason=reason,
        detail=detail or {},
        prev_hash=last.hash if last else "",
    )
    row.hash = compute_hash(row.prev_hash, row)
    db.add(row)
    db.flush()
    return row


def verify_chain(db: Session) -> tuple[bool, int, int | None]:
    """Return (ok, rows_checked, first_bad_id)."""
    prev = ""
    n = 0
    for row in db.scalars(select(AuditLog).order_by(AuditLog.id)):
        n += 1
        if row.prev_hash != prev or compute_hash(prev, row) != row.hash:
            return False, n, row.id
        prev = row.hash
    return True, n, None
