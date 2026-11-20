# ruff: noqa: ASYNC240, ASYNC250  (interactive one-off CLI: blocking file/input calls are fine here)
"""DANGEROUS one-off tool: empty the application's data and (optionally) create exactly one Super Admin.

Run by hand, once, never from startup, CI or a deployment hook. It reads connection details from the environment
(backend/.env) exactly like the app does and never prints passwords, keys, e-mail addresses or document contents.

  uv run python -m scripts.reset_data inventory                     # read-only counts (+ RESET_INVENTORY.md)
  uv run python -m scripts.reset_data backup --dir ~/crate-backup    # export everything OUTSIDE the repository
  uv run python -m scripts.reset_data reset --backup-dir ~/crate-backup --confirm-db <db> --confirm-project <id> \
        [--include-reference-data] [--create-admin --admin-email-verified]
  uv run python -m scripts.reset_data verify                         # counts after the reset

What is cleared : every application collection (users, invites, inspections, notes, proposals, chat, audit logs, usage, counters,
                  GridFS photo/report/image stores) and every Firebase Auth user.
What is kept    : collections themselves, validators, indexes, `_migrations`, `settings`; Firebase project configuration.
Optional        : --include-reference-data also clears `reference_records` and `compliance_rules` (the DEMO reference data).
Super Admin     : this app signs in with Google only, so no password is created (SUPER_ADMIN_PASSWORD is ignored). The admin is
                  created in Firebase (verified e-mail, no password), given the exact claims the API checks, and gets a matching
                  profile; the owner then signs in with that Google account.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from bson import json_util
from firebase_admin import auth as fb_auth

from app.auth import init_firebase
from app.config import get_settings
from app.db import close_client, get_db

CLEAR = [
    "users",
    "user_invites",
    "inspections",
    "inspection_notes",
    "product_proposals",
    "chat_messages",
    "audit_logs",
    "usage_metrics",
    "counters",
]
KEEP = ["_migrations", "settings"]
OPTIONAL = ["reference_records", "compliance_rules"]
REPO = Path(__file__).resolve().parents[2]
ADMIN_ROLES = ("admin", "super_admin")


def _gridfs(names: list[str]) -> list[str]:
    return sorted(n for n in names if n.endswith(".files") or n.endswith(".chunks"))


async def _names() -> list[str]:
    return sorted(await get_db().list_collection_names())


def _firebase_users() -> tuple[int, int]:
    total = admins = 0
    for u in fb_auth.list_users().iterate_all():
        total += 1
        if (u.custom_claims or {}).get("role") in ADMIN_ROLES:
            admins += 1
    return total, admins


async def inventory() -> dict[str, Any]:
    db = get_db()
    names = await _names()
    classified = set(CLEAR + KEEP + OPTIONAL) | set(_gridfs(names))
    rows = []
    for n in names:
        info = (await (await db.list_collections(filter={"name": n})).to_list(1))[0]
        validator = bool((info.get("options") or {}).get("validator"))
        idx = len(await db[n].index_information())
        kind = (
            "CLEAR"
            if n in CLEAR or n in _gridfs(names)
            else "KEEP"
            if n in KEEP
            else "OPTIONAL"
            if n in OPTIONAL
            else "UNCLASSIFIED"
        )
        rows.append(
            {
                "name": n,
                "docs": await db[n].count_documents({}),
                "validator": validator,
                "indexes": idx,
                "class": kind,
            }
        )
    storage = {}
    for b in sorted({n.rsplit(".", 1)[0] for n in _gridfs(names)}):
        cursor = await db[f"{b}.files"].aggregate(
            [{"$group": {"_id": None, "bytes": {"$sum": "$length"}}}]
        )
        agg = await cursor.to_list(1)
        storage[b] = int(agg[0]["bytes"]) if agg else 0
    fb_total, fb_admins = _firebase_users()
    return {
        "database": get_settings().mongodb_db_name,
        "firebase_project": get_settings().firebase_project_id,
        "collections": rows,
        "unclassified": sorted(set(names) - classified),
        "storage_bytes": storage,
        "firebase_users": fb_total,
        "firebase_admins": fb_admins,
    }


def render_inventory(inv: dict[str, Any]) -> str:
    out = [
        "# RESET_INVENTORY (counts only — no contents, no e-mails)",
        "",
        f"- Database: `{inv['database']}`",
        f"- Firebase project: `{inv['firebase_project']}`",
        f"- Firebase Auth users: {inv['firebase_users']} (admin claims: {inv['firebase_admins']})",
        "",
        "| Collection | Documents | Validator | Indexes | Plan |",
        "|---|---|---|---|---|",
    ]
    out += [
        f"| {r['name']} | {r['docs']} | {'yes' if r['validator'] else 'no'} | {r['indexes']} | {r['class']} |"
        for r in inv["collections"]
    ]
    out += [
        "",
        "GridFS size by store (bytes): "
        + (", ".join(f"{k}={v}" for k, v in inv["storage_bytes"].items()) or "none"),
    ]
    if inv["unclassified"]:
        out += [
            "",
            f"**UNCLASSIFIED collections (the reset will refuse to run): {', '.join(inv['unclassified'])}**",
        ]
    return "\n".join(out) + "\n"


async def backup(dest: Path) -> None:
    dest = dest.expanduser().resolve()
    if REPO in dest.parents or dest == REPO:
        raise SystemExit(
            "Refusing: the backup folder must be OUTSIDE the repository (it contains personal data)."
        )
    dest.mkdir(parents=True, exist_ok=True)
    db = get_db()
    total = 0
    for n in await _names():
        with (dest / f"{n}.jsonl").open("w", encoding="utf-8") as f:
            async for d in db[n].find({}):
                f.write(json_util.dumps(d) + "\n")
                total += 1
    users = [
        {
            "uid": u.uid,
            "email": u.email,
            "disabled": u.disabled,
            "claims": u.custom_claims,
            "providers": [p.provider_id for p in u.provider_data],
        }
        for u in fb_auth.list_users().iterate_all()
    ]
    (dest / "firebase_users.json").write_text(json.dumps(users, indent=1))
    size = sum(p.stat().st_size for p in dest.iterdir())
    print(
        f"Backup written: {total} MongoDB documents, {len(users)} Firebase users, {size / 1_048_576:.1f} MB in {dest}"
    )
    print("It contains PERSONAL DATA: delete it when you no longer need it.")


async def reset(a: argparse.Namespace) -> None:
    s = get_settings()
    inv = await inventory()
    if inv["unclassified"]:
        raise SystemExit(
            f"Refusing: unclassified collections {inv['unclassified']}. Decide whether to clear or keep them first."
        )
    if a.confirm_db != s.mongodb_db_name or a.confirm_project != s.firebase_project_id:
        raise SystemExit(
            "Refusing: --confirm-db / --confirm-project do not match the configured target "
            f"(database '{s.mongodb_db_name}', Firebase project '{s.firebase_project_id}')."
        )
    if not a.skip_backup:
        bd = Path(a.backup_dir).expanduser() if a.backup_dir else None
        if not bd or not (bd / "firebase_users.json").exists():
            raise SystemExit(
                "Refusing: no backup found. Run the `backup` step first, or pass --skip-backup if you do not need one."
            )
    print(
        f"TARGET: MongoDB database '{s.mongodb_db_name}', Firebase project '{s.firebase_project_id}'"
    )
    if not a.yes:
        typed = input(f"Type the database name ({s.mongodb_db_name}) to DELETE ALL DATA: ").strip()
        if typed != s.mongodb_db_name:
            raise SystemExit("Not confirmed. Nothing was deleted.")
    db = get_db()
    names = await _names()
    targets = (
        [n for n in CLEAR if n in names]
        + _gridfs(names)
        + ([n for n in OPTIONAL if n in names] if a.include_reference_data else [])
    )
    for n in targets:
        res = await db[n].delete_many({})  # never drop: validators and indexes stay
        print(f"  cleared {n}: {res.deleted_count} documents")
    deleted = failed = 0
    batch: list[str] = []
    for u in fb_auth.list_users().iterate_all():
        batch.append(u.uid)
        if len(batch) == 1000:
            r = fb_auth.delete_users(batch)
            deleted, failed, batch = deleted + r.success_count, failed + r.failure_count, []
    if batch:
        r = fb_auth.delete_users(batch)
        deleted, failed = deleted + r.success_count, failed + r.failure_count
    print(f"  Firebase users deleted: {deleted} (failures: {failed})")
    if a.create_admin:
        await create_admin(a.admin_email_verified)


async def create_admin(email_verified: bool) -> None:
    from app.repositories import users as users_repo

    email = (
        (os.environ.get("SUPER_ADMIN_EMAIL") or get_settings().super_admin_email or "")
        .strip()
        .lower()
    )
    if not email:
        raise SystemExit("SUPER_ADMIN_EMAIL is not set.")
    if os.environ.get("SUPER_ADMIN_PASSWORD"):
        print(
            "  note: SUPER_ADMIN_PASSWORD is ignored — this app signs in with Google only (no password accounts)."
        )
    if not email_verified:
        raise SystemExit(
            "Refusing to create the Super Admin: pass --admin-email-verified to confirm the address is yours "
            "(the API only honours a VERIFIED address for the Super Admin)."
        )
    user = fb_auth.create_user(email=email, email_verified=True)
    fb_auth.set_custom_user_claims(user.uid, {"role": "super_admin", "active": True})
    await users_repo.ensure_profile(user.uid, email, "", None, True, email)
    print(
        "  Super Admin created (Firebase user + claims + profile). Sign in with that Google account."
    )


async def verify() -> None:
    inv = await inventory()
    for r in inv["collections"]:
        print(f"  {r['name']}: {r['docs']} ({r['class']})")
    print(f"  Firebase users: {inv['firebase_users']} (admin claims: {inv['firebase_admins']})")
    users = await get_db()["users"].find({}, {"role": 1, "status": 1}).to_list(5)
    print(f"  profiles: {len(users)}; roles: {[u.get('role') for u in users]}")


async def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    inv_p = sub.add_parser("inventory")
    inv_p.add_argument("--out", default=str(REPO / "RESET_INVENTORY.md"))
    bk = sub.add_parser("backup")
    bk.add_argument("--dir", required=True)
    rs = sub.add_parser("reset")
    rs.add_argument("--confirm-db", required=True)
    rs.add_argument("--confirm-project", required=True)
    rs.add_argument("--backup-dir")
    rs.add_argument("--skip-backup", action="store_true")
    rs.add_argument("--include-reference-data", action="store_true")
    rs.add_argument("--create-admin", action="store_true")
    rs.add_argument("--admin-email-verified", action="store_true")
    rs.add_argument(
        "--yes",
        action="store_true",
        help="skip the typed confirmation (the --confirm-* values are still required)",
    )
    sub.add_parser("verify")
    a = ap.parse_args()
    init_firebase()
    try:
        if a.cmd == "inventory":
            inv = await inventory()
            text = render_inventory(inv)
            print(text)
            Path(a.out).write_text(text)
        elif a.cmd == "backup":
            await backup(Path(a.dir))
        elif a.cmd == "reset":
            await reset(a)
        else:
            await verify()
    finally:
        await close_client()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
