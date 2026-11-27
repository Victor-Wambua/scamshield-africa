"""Single tenant-isolation query layer.

Every organisation-owned table is read and written ONLY through ``TenantScope``. Routes and API
handlers never build org-scoped queries themselves; tests assert cross-tenant access fails.
"""

from __future__ import annotations

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from .models import AlertSubscription, ApiKey, Case, CaseIndicator, CaseNote, Evidence, Report, utcnow


class TenantViolation(PermissionError):
    pass


class TenantScope:
    def __init__(self, db: Session, org_id: int | None) -> None:
        if org_id is None:
            raise TenantViolation("user is not attached to an organisation")
        self.db = db
        self.org_id = org_id

    # --- reports owned by this org (raw evidence visible only here, Decision 2) ---
    def reports(self) -> Select[Report]:
        return select(Report).where(Report.owning_org_id == self.org_id)

    def report(self, report_id: int) -> Report:
        r = self.db.scalar(self.reports().where(Report.id == report_id))
        if r is None:
            raise TenantViolation("report not in your organisation")
        return r

    def evidence_item(self, evidence_id: int) -> Evidence:
        ev = self.db.get(Evidence, evidence_id)
        if ev is None:
            raise TenantViolation("evidence not available")
        rep = self.db.scalar(self.reports().where(Report.id == ev.report_id))
        if rep is None:
            raise TenantViolation("evidence not in your organisation")
        return ev

    # --- cases ---
    def cases(self) -> Select[Case]:
        return select(Case).where(Case.org_id == self.org_id)

    def case(self, case_id: int) -> Case:
        c = self.db.scalar(self.cases().where(Case.id == case_id))
        if c is None:
            raise TenantViolation("case not in your organisation")
        return c

    def create_case(self, title: str, user_id: int) -> Case:
        c = Case(org_id=self.org_id, title=title, created_by=user_id)
        self.db.add(c)
        self.db.flush()
        return c

    def link_indicator(self, case: Case, indicator_id: int) -> None:
        self.case(case.id)
        exists = self.db.scalar(select(CaseIndicator).where(CaseIndicator.case_id == case.id, CaseIndicator.indicator_id == indicator_id))
        if not exists:
            self.db.add(CaseIndicator(case_id=case.id, org_id=self.org_id, indicator_id=indicator_id))
            self.db.flush()

    def case_indicator_ids(self, case_id: int) -> list[int]:
        self.case(case_id)
        return list(self.db.scalars(select(CaseIndicator.indicator_id).where(CaseIndicator.case_id == case_id, CaseIndicator.org_id == self.org_id)))

    def add_note(self, case_id: int, author_id: int, body: str) -> CaseNote:
        self.case(case_id)
        n = CaseNote(case_id=case_id, org_id=self.org_id, author_id=author_id, body=body)
        self.db.add(n)
        self.db.flush()
        return n

    def notes(self, case_id: int) -> list[CaseNote]:
        self.case(case_id)
        return list(self.db.scalars(select(CaseNote).where(CaseNote.case_id == case_id, CaseNote.org_id == self.org_id).order_by(CaseNote.id.desc())))

    def set_case_status(self, case_id: int, status: str) -> Case:
        c = self.case(case_id)
        c.status = status
        self.db.flush()
        return c

    # --- API keys ---
    def keys(self) -> Select[ApiKey]:
        return select(ApiKey).where(ApiKey.org_id == self.org_id)

    def key(self, key_id: int) -> ApiKey:
        k = self.db.scalar(self.keys().where(ApiKey.id == key_id))
        if k is None:
            raise TenantViolation("key not in your organisation")
        return k

    def revoke_key(self, key_id: int) -> ApiKey:
        k = self.key(key_id)
        k.revoked_at = utcnow()
        self.db.flush()
        return k

    # --- alert subscriptions ---
    def alerts(self) -> Select[AlertSubscription]:
        return select(AlertSubscription).where(AlertSubscription.org_id == self.org_id)

    def alert(self, alert_id: int) -> AlertSubscription:
        a = self.db.scalar(self.alerts().where(AlertSubscription.id == alert_id))
        if a is None:
            raise TenantViolation("alert not in your organisation")
        return a
