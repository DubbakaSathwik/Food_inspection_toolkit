"""Backup bootstrap (D-08): grant a role to an existing user by email.

`uv run python -m scripts.grant_role someone@example.com super_admin`
The user must have signed in once. Sets the DB role/status and Firebase custom claims."""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime

from firebase_admin import auth as fb_auth

from app.auth import init_firebase
from app.db import close_client, get_db

ROLES = ("inspector", "admin", "super_admin")


async def main(email: str, role: str) -> None:
    init_firebase()
    db = get_db()
    user = await db["users"].find_one({"email": email.lower()})
    if not user:
        raise SystemExit("No profile with that email. Ask the user to sign in once first.")
    await db["users"].update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "role": role,
                "status": "active",
                "approved_at": datetime.now(UTC),
                "approved_by": "grant_role script",
                "updated_at": datetime.now(UTC),
            }
        },
    )
    fb_auth.set_custom_user_claims(user["_id"], {"role": role, "active": True})
    await db["audit_logs"].insert_one(
        {
            "actor_uid": "script",
            "actor_name": "grant_role script",
            "actor_role": None,
            "action": "user.role_change",
            "target_type": "user",
            "target_id": user["_id"],
            "summary": f"Granted {role} to {email}",
            "changes": {"role": [user.get("role"), role]},
            "at": datetime.now(UTC),
        }
    )
    print(
        f"Granted {role} to {email}. They must sign out and in (or reload) to refresh their token."
    )
    await close_client()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("email")
    ap.add_argument("role", choices=ROLES)
    a = ap.parse_args()
    asyncio.run(main(a.email, a.role))
