"""Command line: python -m scamshield <command>."""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

from . import audit, notify
from .config import get_settings
from .db import Base, Database


def _db() -> Database:
    s = get_settings()
    s.storage_dir.mkdir(parents=True, exist_ok=True)
    if s.database_url.startswith("sqlite:///./"):
        Path(s.database_url.replace("sqlite:///./", "")).parent.mkdir(parents=True, exist_ok=True)
    return Database(s.database_url)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="scamshield")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("migrate", help="apply Alembic migrations")
    sd = sub.add_parser("seed", help="load SYNTHETIC demo data")
    sd.add_argument("--reset", action="store_true", help="SQLite dev only: drop and recreate all tables first")
    cu = sub.add_parser("create-user", help="create a user (password read from SS_NEW_PASSWORD or prompt)")
    cu.add_argument("email")
    cu.add_argument("role", choices=["reporter", "moderator", "platform_admin", "org_admin", "org_analyst"])
    cu.add_argument("--org-id", type=int)
    sub.add_parser("digest", help="send due alert digests (sandbox mailer)")
    sub.add_parser("audit-verify", help="verify the audit hash chain")
    sv = sub.add_parser("serve", help="run the dev server")
    sv.add_argument("--port", type=int, default=4300)
    ev = sub.add_parser("evaluate", help="run the offline evaluation on the synthetic labelled set")
    ev.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    settings = get_settings()

    if args.cmd == "migrate":
        _db()
        cfg = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
        cfg.set_main_option("script_location", str(Path(__file__).resolve().parents[2] / "migrations"))
        cfg.set_main_option("sqlalchemy.url", settings.database_url)
        command.upgrade(cfg, "head")
        print("migrated")
        return 0
    if args.cmd == "serve":
        import uvicorn

        uvicorn.run("scamshield.main:app_factory", factory=True, host="127.0.0.1", port=args.port)
        return 0
    if args.cmd == "evaluate":
        from .evaluation import run_evaluation

        return run_evaluation(write=args.write)
    db = _db()
    if args.cmd == "seed":
        from .seed import seed

        if args.reset:
            if not settings.database_url.startswith("sqlite"):
                print("--reset is only allowed on SQLite", file=sys.stderr)
                return 2
            Base.metadata.drop_all(db.engine)
            Base.metadata.create_all(db.engine)
        with db.factory() as session:
            creds = seed(session, settings, Path("data/demo-credentials.txt"))
            session.commit()
        print("Synthetic demo data loaded. Credentials written to data/demo-credentials.txt (local only).")
        print("Demo password:", creds["password (all demo accounts)"])
        return 0
    with db.factory() as session:
        if args.cmd == "create-user":
            import os

            from . import accounts

            pw = os.environ.get("SS_NEW_PASSWORD") or getpass.getpass("Password: ")
            u = accounts.register(session, args.email, pw, "", True, role=args.role, org_id=args.org_id)
            session.commit()
            print(f"created {u.email} ({u.role}); MFA is enrolled at first sign-in for staff roles")
        elif args.cmd == "digest":
            print("digests sent:", notify.run_digest(session))
            session.commit()
        elif args.cmd == "audit-verify":
            ok, n, bad = audit.verify_chain(session)
            print("audit chain", "OK" if ok else f"BROKEN at {bad}", f"({n} entries)")
            return 0 if ok else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
