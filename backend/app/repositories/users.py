"""Users, invitations (pre-authorised emails) and activity tracking."""

from __future__ import annotations

import re
from datetime import timedelta
from typing import Any

from pymongo import ReturnDocument

from app.errors import AppError, forbidden, not_found
from app.principal import Principal
from app.repositories import audit
from app.repositories.base import col, ensure_admin, now, paginate

_last_touch: dict[str, float] = {}


async def get(uid: str) -> dict[str, Any] | None:
    return await col("users").find_one({"_id": uid})


async def ensure_profile(
    uid: str,
    email: str,
    name: str,
    photo_url: str | None,
    email_verified: bool,
    super_admin_email: str | None,
) -> dict[str, Any]:
    """Create the profile on first sign-in. Pending by default (BR-09); bootstrap Super Admin by
    verified email (D-08); honour an admin's invitation for this email."""
    existing = await get(uid)
    email_l = email.lower()
    if existing:
        if (
            super_admin_email
            and email_verified
            and email_l == super_admin_email
            and (existing.get("role") != "super_admin" or existing.get("status") != "active")
            and existing.get("status") != "disabled"
        ):
            existing = await col("users").find_one_and_update(
                {"_id": uid},
                {
                    "$set": {
                        "role": "super_admin",
                        "status": "active",
                        "updated_at": now(),
                        "approved_at": now(),
                        "approved_by": "bootstrap",
                    }
                },
                return_document=ReturnDocument.AFTER,
            )
            assert existing is not None
        return existing

    role: str | None = None
    status = "pending"
    approved_by: str | None = None
    if super_admin_email and email_verified and email_l == super_admin_email:
        role, status, approved_by = "super_admin", "active", "bootstrap"
    elif email_verified:
        invite = await col("user_invites").find_one_and_delete({"_id": email_l})
        if invite:
            role, status, approved_by = invite["role"], "active", invite.get("created_by")

    doc: dict[str, Any] = {
        "_id": uid,
        "email": email_l,
        "name": name or email_l.split("@")[0],
        "photo_url": photo_url,
        "role": role,
        "status": status,
        "designation": "",
        "office": "",
        "phone": "",
        "created_at": now(),
        "updated_at": now(),
        "approved_at": now() if status == "active" else None,
        "approved_by": approved_by,
        "last_active_at": now(),
    }
    await col("users").insert_one(doc)
    return doc


async def update_profile(p: Principal, changes: dict[str, Any]) -> dict[str, Any]:
    allowed = {k: v for k, v in changes.items() if k in {"name", "designation", "office", "phone"}}
    allowed["updated_at"] = now()
    doc = await col("users").find_one_and_update(
        {"_id": p.uid}, {"$set": allowed}, return_document=ReturnDocument.AFTER
    )
    if not doc:
        raise not_found("User")
    return doc


async def touch_active(uid: str) -> None:
    """Record activity at most every 10 minutes per process (for DAU/WAU/MAU)."""
    import time

    t = time.monotonic()
    if t - _last_touch.get(uid, 0) < 600:
        return
    _last_touch[uid] = t
    ts = now()
    await col("users").update_one({"_id": uid}, {"$set": {"last_active_at": ts}})
    await col("usage_metrics").update_one(
        {"uid": uid, "day": ts.strftime("%Y-%m-%d")},
        {"$set": {"active": True}, "$setOnInsert": {"ai_calls": 0}},
        upsert=True,
    )


# ---------------------------------------------------------------- admin functions


def _user_filter(q: str | None, role: str | None, status: str | None) -> dict[str, Any]:
    flt: dict[str, Any] = {}
    if q:
        rx = {"$regex": re.escape(q), "$options": "i"}
        flt["$or"] = [{"name": rx}, {"email": rx}, {"office": rx}]
    if role:
        flt["role"] = role
    if status:
        flt["status"] = status
    return flt


async def list_users(
    admin: Principal, q: str | None, role: str | None, status: str | None, page: int, page_size: int
) -> tuple[list[dict[str, Any]], int]:
    ensure_admin(admin)
    items, total = await paginate(
        "users", _user_filter(q, role, status), page, page_size, [("created_at", -1)]
    )
    counts: dict[str, int] = {}
    if items:
        uids = [u["_id"] for u in items]
        async for row in await col("inspections").aggregate(
            [
                {"$match": {"owner_uid": {"$in": uids}}},
                {"$group": {"_id": "$owner_uid", "n": {"$sum": 1}}},
            ]
        ):
            counts[row["_id"]] = row["n"]
    for u in items:
        u["uid"] = u["_id"]
        u["inspections"] = counts.get(u["_id"], 0)
    return items, total


async def user_detail(admin: Principal, uid: str) -> dict[str, Any]:
    ensure_admin(admin)
    u = await get(uid)
    if not u:
        raise not_found("User")
    u["uid"] = u["_id"]
    u["inspections"] = await col("inspections").count_documents({"owner_uid": uid})
    u["completed_inspections"] = await col("inspections").count_documents(
        {"owner_uid": uid, "status": "completed"}
    )
    u["proposals"] = await col("product_proposals").count_documents({"owner_uid": uid})
    cur = (
        col("inspections")
        .find({"owner_uid": uid}, {"_id": 1, "summary": 1, "status": 1, "created_at": 1})
        .sort("created_at", -1)
        .limit(5)
    )
    u["recent"] = [
        {
            "id": d["_id"],
            "product": (d.get("summary") or {}).get("product_name") or "Untitled",
            "status": d.get("status", ""),
            "date": d["created_at"].strftime("%d %b %Y"),
        }
        async for d in cur
    ]
    return u


def _check_role_change(admin: Principal, target: dict[str, Any], new_role: str | None) -> None:
    if target["_id"] == admin.uid:
        raise forbidden("You cannot change your own role or status.")
    privileged = {"admin", "super_admin"}
    if (target.get("role") in privileged or new_role in privileged) and not admin.is_super_admin:
        raise forbidden("Only a Super Admin can grant or change administrator roles.")


async def _count_super_admins() -> int:
    return await col("users").count_documents({"role": "super_admin", "status": "active"})


async def approve(admin: Principal, uid: str, role: str) -> dict[str, Any]:
    ensure_admin(admin)
    target = await get(uid)
    if not target:
        raise not_found("User")
    if target.get("status") not in ("pending", "declined"):
        raise AppError(409, "conflict", "This account is not awaiting approval.")
    _check_role_change(admin, target, role)
    doc = await col("users").find_one_and_update(
        {"_id": uid},
        {
            "$set": {
                "role": role,
                "status": "active",
                "approved_at": now(),
                "approved_by": admin.uid,
                "updated_at": now(),
            }
        },
        return_document=ReturnDocument.AFTER,
    )
    assert doc is not None
    await audit.log(
        admin,
        "user.approve",
        "user",
        uid,
        f"Approved {doc['email']} as {role}",
        {"role": [target.get("role"), role], "status": [target.get("status"), "active"]},
    )
    return doc


async def decline(admin: Principal, uid: str) -> dict[str, Any]:
    ensure_admin(admin)
    target = await get(uid)
    if not target:
        raise not_found("User")
    if target.get("status") != "pending":
        raise AppError(409, "conflict", "Only pending accounts can be declined.")
    doc = await col("users").find_one_and_update(
        {"_id": uid},
        {"$set": {"status": "declined", "updated_at": now()}},
        return_document=ReturnDocument.AFTER,
    )
    assert doc is not None
    await audit.log(
        admin,
        "user.decline",
        "user",
        uid,
        f"Declined {doc['email']}",
        {"status": ["pending", "declined"]},
    )
    return doc


async def patch_user(admin: Principal, uid: str, changes: dict[str, Any]) -> dict[str, Any]:
    ensure_admin(admin)
    target = await get(uid)
    if not target:
        raise not_found("User")
    new_role = changes.get("role")
    new_status = changes.get("status")
    if new_role is not None or new_status is not None:
        _check_role_change(admin, target, new_role)
        if target.get("status") in ("pending", "declined") and new_status == "active":
            raise AppError(409, "conflict", "Use Approve for pending accounts.")
        if (
            target.get("role") == "super_admin"
            and ((new_role and new_role != "super_admin") or new_status == "disabled")
            and await _count_super_admins() <= 1
        ):
            raise AppError(409, "conflict", "The last Super Admin cannot be demoted or disabled.")
    upd = {k: v for k, v in changes.items() if v is not None}
    if not upd:
        return target
    upd["updated_at"] = now()
    doc = await col("users").find_one_and_update(
        {"_id": uid}, {"$set": upd}, return_document=ReturnDocument.AFTER
    )
    assert doc is not None
    diff = {
        k: [target.get(k), v] for k, v in upd.items() if k != "updated_at" and target.get(k) != v
    }
    action = (
        "user.disable"
        if new_status == "disabled"
        else (
            "user.enable"
            if new_status == "active"
            else ("user.role_change" if new_role else "user.update")
        )
    )
    await audit.log(admin, action, "user", uid, f"Updated {doc['email']}", diff)
    return doc


async def create_invite(admin: Principal, email: str, name: str, role: str) -> dict[str, Any]:
    ensure_admin(admin)
    if role in ("admin", "super_admin") and not admin.is_super_admin:
        raise forbidden("Only a Super Admin can add administrators.")
    email_l = email.lower()
    if await col("users").find_one({"email": email_l}):
        raise AppError(409, "conflict", "A user with this email already exists.")
    doc = {
        "_id": email_l,
        "email": email_l,
        "name": name,
        "role": role,
        "created_by": admin.uid,
        "created_by_name": admin.name,
        "created_at": now(),
    }
    await col("user_invites").replace_one({"_id": email_l}, doc, upsert=True)
    await audit.log(
        admin,
        "user.invite",
        "user",
        email_l,
        f"Pre-authorised {email_l} as {role}",
        {"role": [None, role]},
    )
    return doc


async def list_invites(admin: Principal) -> list[dict[str, Any]]:
    ensure_admin(admin)
    return [d async for d in col("user_invites").find({}).sort("created_at", -1).limit(200)]


async def delete_invite(admin: Principal, email: str) -> None:
    ensure_admin(admin)
    res = await col("user_invites").delete_one({"_id": email.lower()})
    if not res.deleted_count:
        raise not_found("Invitation")
    await audit.log(admin, "user.invite_revoke", "user", email.lower(), "Revoked invitation")


async def counts() -> dict[str, int]:
    out = {"total": await col("users").count_documents({})}
    async for row in await col("users").aggregate(
        [{"$group": {"_id": "$status", "n": {"$sum": 1}}}]
    ):
        out[f"status_{row['_id']}"] = row["n"]
    async for row in await col("users").aggregate(
        [{"$match": {"status": "active"}}, {"$group": {"_id": "$role", "n": {"$sum": 1}}}]
    ):
        out[f"role_{row['_id']}"] = row["n"]
    return out


async def active_counts() -> dict[str, int]:
    today = now()

    def day(n: int) -> str:
        return (today - timedelta(days=n)).strftime("%Y-%m-%d")

    res: dict[str, int] = {}
    for key, days in (("dau", 1), ("wau", 7), ("mau", 30)):
        uids = await col("usage_metrics").distinct(
            "uid", {"day": {"$gt": day(days)}, "active": True}
        )
        res[key] = len(uids)
    return res


async def pending_list(limit: int = 6) -> list[dict[str, Any]]:
    cur = (
        col("users")
        .find({"status": "pending"}, {"email": 1, "name": 1, "created_at": 1})
        .sort("created_at", 1)
        .limit(limit)
    )
    return [
        {
            "uid": d["_id"],
            "email": d["email"],
            "name": d.get("name", ""),
            "created_at": d.get("created_at"),
        }
        async for d in cur
    ]
