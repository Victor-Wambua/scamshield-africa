"""Sandbox mailer: logs to the mail_outbox table. No email is delivered (mock integration).

A real SMTP/provider backend would implement the same `send` signature; none is connected here.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from .models import MailOutbox


def send(db: Session, to_addr: str, subject: str, body: str) -> MailOutbox:
    row = MailOutbox(to_addr=to_addr, subject=subject[:200], body=body, origin="mock integration")
    db.add(row)
    db.flush()
    return row
