"""Bootstrap accounts without the API (the first admin has to come from somewhere).

python -m backend.manage create-user admin --role admin
python -m backend.manage create-user kysu --role engineer
python -m backend.manage create-user an --role driver --driver-id drv-001
python -m backend.manage create-device cam-001 --driver-id drv-001   # prints the key once

Data policy (docs/data-policy.md):
python -m backend.manage purge                               # delete metadata past its retention period now
python -m backend.manage delete-driver-data drv-001 --yes    # a driver left / asked for deletion
"""

from __future__ import annotations

import argparse
import getpass
import sqlite3
import sys
from datetime import UTC, datetime

from backend import db
from backend.schemas import DeviceIn, UserIn
from backend.security import hash_device_key, hash_password, new_device_key
from backend.settings import BackendSettings


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", default=None, help="SQLite path (default: DG_DB_PATH or data/driverguard.db)")
    sub = p.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("create-user")
    u.add_argument("username")
    u.add_argument("--role", required=True, choices=["admin", "engineer", "manager", "driver"])
    u.add_argument("--driver-id", default=None)
    u.add_argument("--password", default=None, help="omit to be prompted (keeps it out of shell history)")
    d = sub.add_parser("create-device")
    d.add_argument("device_id")
    d.add_argument("--driver-id", default=None)
    sub.add_parser("purge", help="delete metadata past DG_RETENTION_*_DAYS now")
    x = sub.add_parser("delete-driver-data", help="delete every event, sample, summary and status of one driver")
    x.add_argument("driver_id")
    x.add_argument("--yes", action="store_true", help="really delete (cannot be undone)")
    args = p.parse_args(argv)

    settings = BackendSettings()
    db_path = args.db or settings.db_path
    db.init_db(db_path)
    with db.closing(db_path) as conn:
        try:
            if args.cmd == "purge":
                deleted = db.purge_expired(
                    conn, datetime.now(UTC), settings.retention_events_days, settings.retention_summaries_days
                )
                print(f"deleted {deleted}")
            elif args.cmd == "delete-driver-data":
                if not args.yes:
                    print("nothing deleted: add --yes to delete this driver's data (cannot be undone)", file=sys.stderr)
                    return 1
                print(f"deleted for '{args.driver_id}': {db.delete_driver_data(conn, args.driver_id)}")
            elif args.cmd == "create-user":
                password = args.password or getpass.getpass("password (min 8 chars): ")
                user = UserIn(username=args.username, password=password, role=args.role, driver_id=args.driver_id)
                db.create_user(conn, user.username, hash_password(user.password), user.role, user.driver_id)
                print(f"created {user.role} '{user.username}'")
            else:
                dev = DeviceIn(device_id=args.device_id, driver_id=args.driver_id)
                key = new_device_key()
                db.create_device(conn, dev.device_id, hash_device_key(key), dev.driver_id)
                print(f"created device '{dev.device_id}'. Device key (shown only once):\n{key}")
        except sqlite3.IntegrityError:
            print("already exists", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
