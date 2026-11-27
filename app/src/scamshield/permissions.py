"""Role-based access control: one table, used by routes and tested as an authz matrix."""

from __future__ import annotations

PERMISSIONS: dict[str, frozenset[str]] = {
    "reporter": frozenset({"report.submit", "report.own", "notifications.own", "account.own"}),
    "contributor": frozenset({"report.submit", "report.own", "notifications.own", "account.own"}),
    "moderator": frozenset(
        {
            "report.submit", "report.own", "notifications.own", "account.own",
            "moderation.queue", "moderation.decide", "corrections.handle", "audit.read",
            "evidence.view_all", "restrict.reporter",
        }
    ),
    "org_analyst": frozenset(
        {
            "report.submit", "report.own", "notifications.own", "account.own",
            "org.analytics", "org.cases", "org.export", "org.alerts", "org.evidence", "dev.usage",
        }
    ),
    "org_admin": frozenset(
        {
            "report.submit", "report.own", "notifications.own", "account.own",
            "org.analytics", "org.cases", "org.export", "org.alerts", "org.evidence",
            "dev.usage", "dev.keys",
        }
    ),
    "platform_admin": frozenset(
        {
            "report.submit", "report.own", "notifications.own", "account.own",
            "moderation.queue", "moderation.decide", "corrections.handle", "audit.read",
            "evidence.view_all", "restrict.reporter", "admin.users", "admin.orgs", "corrections.remove",
            "legal.takedown",
        }
    ),
}


def can(role: str | None, permission: str) -> bool:
    if role is None:
        return permission == "report.submit"  # visitors may submit reports (rate limited)
    return permission in PERMISSIONS.get(role, frozenset())
