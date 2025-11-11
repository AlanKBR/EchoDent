"""
Purge development users created by the /__dev/login_as/<role> helper.

Safety:
- Only runs when FLASK_DEBUG or app.debug is True, unless --force is passed.
- Only deletes usernames in the allowlist:
    - dev_admin
    - dev_dentista
    - dev_secretaria

Usage (PowerShell):
  $env:FLASK_DEBUG=1; python scripts/purge_dev_users.py
  # or
  python scripts/purge_dev_users.py --force
"""

from __future__ import annotations

import argparse
import os

from app import create_app, db
from app.models import Usuario

ALLOWED_USERNAMES: list[str] = [
    "dev_admin",
    "dev_dentista",
    "dev_secretaria",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Purge dev users (safe).")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force purge even if app is not in debug/testing.",
    )
    args = parser.parse_args()

    app = create_app(os.getenv("FLASK_CONFIG") or "default")
    with app.app_context():
        debug_like = bool(app.debug or app.config.get("TESTING"))
        if not debug_like and not args.force:
            print(
                "Refusing to purge: app not in debug/testing. "
                "Use --force to override."
            )
            return 2

        q = Usuario.query.filter(Usuario.username.in_(ALLOWED_USERNAMES))
        users = q.all()
        if not users:
            print("No dev users found.")
            return 0

        count = 0
        for u in users:
            print(f"Deleting {u.username} (id={u.id})")
            db.session.delete(u)
            count += 1
        db.session.commit()
        print(f"Purged {count} dev user(s).")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
