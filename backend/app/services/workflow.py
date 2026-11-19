"""Inspection workflow orchestration (REQ-011…030). Uses repositories for all persistence."""

from __future__ import annotations

import secrets
from datetime import date
from typing import Any

from app.config import get_settings
from app.errors import AppError, bad_request
from app.principal import Principal
from app.repositories import files, reference, rules, usage
from app.repositories import inspections as repo
from app.repositories import settings as settings_repo
from app.repositories.base import now
from app.services import classification, compliance, images, matching
from app.services.ai import chain
from app.services.ai.prompts import EXTRACTION_PROMPT, PACKAGING_PROMPT
from app.services.fields import (
    CATEGORIES,
    FIELD_KEYS,
    FIELDS,
    confidence_level,
    is_blank,
    validate_field,
)

MAX_PHOTOS = 5
EDITABLE = ["draft", "incomplete", "extracted", "analysed"]


# ---------------------------------------------------------------- serialisation


def to_out(doc: dict[str, Any], notes: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    fields = doc.get("fields") or {}
    out_fields = []
    for f in FIELDS:
        data = fields.get(f.key)
        if data:
            out_fields.append({"key": f.key, "label": f.label, "group": f.group, **data})
    return {
        "id": doc["_id"],
        "status": doc["status"],
        "owner_name": doc.get("owner_name", ""),
        "created_at": doc["created_at"],
        "updated_at": doc.get("updated_at"),
        "photos": doc.get("photos", []),
        "photos_deleted": doc.get("photos_deleted", False),
        "category": doc.get("category"),
        "category_source": doc.get("category_source"),
        "extraction": doc.get("extraction") or {},
        "fields": out_fields,
        "analysis": doc.get("analysis"),
        "findings": doc.get("findings", []),
        "suggestion": doc.get("suggestion"),
        "decision": doc.get("decision"),
        "report": doc.get("report"),
        "notes": [
            {"id": str(n["_id"]), "text": n["text"], "created_at": n["created_at"]}
            for n in notes or []
        ],
        "proposal_id": doc.get("proposal_id"),
    }


def to_summary(doc: dict[str, Any]) -> dict[str, Any]:
    summary = doc.get("summary") or {}
    findings = doc.get("findings") or []
    return {
        "id": doc["_id"],
        "product_name": summary.get("product_name"),
        "brand": summary.get("brand"),
        "category": doc.get("category"),
        "status": doc["status"],
        "classification": (doc.get("decision") or {}).get("classification"),
        "photo_count": len(doc.get("photos") or []),
        "fields_extracted": int(summary.get("fields_extracted") or 0),
        "findings_open": len([f for f in findings if not f.get("decision")]),
        "created_at": doc["created_at"],
        "updated_at": doc.get("updated_at"),
        "has_report": bool(doc.get("report")),
    }


# ---------------------------------------------------------------- photos


async def upload_photo(
    p: Principal, inspection_id: str, data: bytes, filename: str, label: str
) -> dict[str, Any]:
    s = get_settings()
    insp = await repo.get(p, inspection_id)
    if insp["status"] == "completed":
        raise AppError(409, "invalid_state", "This inspection is completed.")
    if len(insp.get("photos", [])) >= MAX_PHOTOS:
        raise AppError(
            409, "too_many_photos", f"An inspection can have up to {MAX_PHOTOS} photographs."
        )
    meta = images.inspect_upload(data, s.max_upload_mb * 1_048_576)
    quality = images.quality_check(data, meta["width"], meta["height"])
    safe_name = (
        f"{inspection_id}-{secrets.token_hex(4)}.{meta['format'].lower().replace('jpeg', 'jpg')}"
    )
    fid = await files.put(
        "photos",
        data,
        safe_name,
        meta["content_type"],
        {
            "owner_uid": p.uid,
            "inspection_id": inspection_id,
            "expires_at": insp["photo_expires_at"],
        },
    )
    photo = {
        "id": fid,
        "label": label,
        "filename": (filename or "")[:120],
        "content_type": meta["content_type"],
        "width": meta["width"],
        "height": meta["height"],
        "size": len(data),
        "quality": quality,
        "crop": None,
        "uploaded_at": now(),
    }
    try:
        return await repo.add_photo(p, inspection_id, photo, MAX_PHOTOS)
    except AppError:
        await files.delete("photos", fid)
        raise


async def delete_photo(p: Principal, inspection_id: str, photo_id: str) -> dict[str, Any]:
    doc = await repo.remove_photo(p, inspection_id, photo_id)
    await files.delete("photos", photo_id)
    return doc


async def load_images(
    p: Principal, insp: dict[str, Any], apply_crop: bool = True
) -> list[images.ImageInput]:
    if insp.get("photos_deleted"):
        raise AppError(
            410,
            "photos_deleted",
            "The original photographs were removed after the report was generated.",
        )
    out: list[images.ImageInput] = []
    for i, ph in enumerate(insp.get("photos", []), start=1):
        data, info = await files.read_bytes("photos", ph["id"], owner_uid=p.uid)
        mime = (info.get("metadata") or {}).get(
            "content_type", ph.get("content_type", "image/jpeg")
        )
        if apply_crop and ph.get("crop"):
            data, mime = images.apply_crop(data, mime, ph["crop"])
        out.append(images.ImageInput(data=data, mime=mime, label=ph.get("label", ""), index=i))
    return out


# ---------------------------------------------------------------- extraction


def _clean_conf(v: Any) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, f))


def build_fields(
    raw: dict[str, Any], photo_count: int, threshold: float, previous: dict[str, Any]
) -> dict[str, Any]:
    raw_fields = raw.get("fields") if isinstance(raw.get("fields"), dict) else {}
    assert isinstance(raw_fields, dict)
    out: dict[str, Any] = {}
    ts = now()
    for key in FIELD_KEYS:
        r = raw_fields.get(key) if isinstance(raw_fields.get(key), dict) else {}
        assert isinstance(r, dict)
        val = r.get("value")
        val = str(val).strip()[:4000] if val is not None and str(val).strip() else None
        if val is not None and is_blank(val):
            val = None
        conf = (
            _clean_conf(r.get("confidence")) if val else min(_clean_conf(r.get("confidence")), 0.3)
        )
        photo = r.get("photo")
        photo = (
            int(photo)
            if isinstance(photo, int | float) and 1 <= int(photo) <= photo_count
            else None
        )
        note = validate_field(key, val)
        ai_note = str(r.get("note"))[:300] if r.get("note") else None
        flag = "not_found" if val is None else ("check" if note else "ok")
        status = "auto" if (flag == "ok" and conf >= threshold) else "pending"
        field: dict[str, Any] = {
            "ai_value": val,
            "ai_confidence": round(conf, 3),
            "confidence_level": confidence_level(conf),
            "source_photo": photo,
            "flag": flag,
            "note": note or ai_note,
            "value": val,
            "status": status,
            "history": [],
        }
        prev = previous.get(key)
        if prev and prev.get("status") in ("confirmed", "edited"):
            field["value"] = prev.get("value")
            field["status"] = prev["status"]
            history: list[dict[str, Any]] = list(prev.get("history") or [])[-20:]
            field["history"] = history
            history.append({"value": val, "at": ts, "by": "AI re-reading (inspector value kept)"})
        out[key] = field
    return out


async def extract(p: Principal, inspection_id: str) -> dict[str, Any]:
    insp = await repo.get(p, inspection_id)
    if insp["status"] not in EDITABLE:
        raise AppError(409, "invalid_state", "This inspection is completed.")
    if not insp.get("photos"):
        raise bad_request("Add at least one photograph first.")
    cfg = await settings_repo.load()
    await usage.consume_ai(p.uid, cfg["limits"]["ai_daily_limit_per_user"])
    imgs = await load_images(p, insp)
    allow_ocr = bool(cfg["ai"].get("ocr_fallback_enabled", True))
    res = await chain.run_extract(imgs, EXTRACTION_PROMPT, allow_ocr)
    attempts = (insp.get("extraction") or {}).get("attempts", [])[-15:] + res.attempts
    if res.data is None:
        return await repo.update(
            p,
            inspection_id,
            {
                "status": "incomplete",
                "extraction": {
                    "status": "failed",
                    "provider": None,
                    "ocr_used": False,
                    "at": now(),
                    "attempts": attempts,
                },
            },
            expect_status=EDITABLE,
        )
    fields = build_fields(
        res.data, len(imgs), cfg["general"]["auto_confirm_threshold"], insp.get("fields") or {}
    )
    sets: dict[str, Any] = {
        "status": "extracted",
        "fields": fields,
        "extraction": {
            "status": "done",
            "provider": res.provider,
            "ocr_used": res.ocr_used,
            "at": now(),
            "attempts": attempts,
            "resized_for_provider": bool(res.data.get("_resized")),
        },
        "summary": {
            "product_name": fields["product_name"]["value"],
            "brand": fields["brand"]["value"],
            "fields_extracted": sum(1 for f in fields.values() if f["value"]),
        },
        "analysis": None,
        "findings": [],
        "suggestion": None,
        "analysis_stale": False,
    }
    cat = res.data.get("category")
    if insp.get("category_source") != "inspector" and cat in CATEGORIES:
        sets["category"] = cat
        sets["category_source"] = "ai"
    return await repo.update(p, inspection_id, sets, expect_status=EDITABLE)


async def update_field(
    p: Principal, inspection_id: str, key: str, value: str | None, confirm: bool
) -> dict[str, Any]:
    if key not in FIELD_KEYS:
        raise bad_request("Unknown field.")
    insp = await repo.get(p, inspection_id)
    if insp["status"] not in ("extracted", "analysed"):
        raise AppError(
            409, "invalid_state", "Fields can be edited after extraction and before the report."
        )
    field = (insp.get("fields") or {}).get(key)
    if not field:
        raise bad_request("Run the AI reading first.")
    value = value.strip() if value and value.strip() else None
    changed = value != field.get("value")
    status = (
        "edited"
        if value != field.get("ai_value")
        else ("confirmed" if confirm else field["status"])
    )
    sets: dict[str, Any] = {f"fields.{key}.value": value, f"fields.{key}.status": status}
    note = validate_field(key, value)
    sets[f"fields.{key}.flag"] = "not_found" if value is None else ("check" if note else "ok")
    sets[f"fields.{key}.note"] = note
    extra = None
    if changed:
        extra = {
            "$push": {
                f"fields.{key}.history": {
                    "$each": [{"value": value, "at": now(), "by": p.name}],
                    "$slice": -30,
                }
            }
        }
        if key in ("product_name", "brand"):
            sets[f"summary.{key}"] = value
        if insp["status"] == "analysed":
            sets["analysis_stale"] = True
    return await repo.update(
        p, inspection_id, sets, expect_status=["extracted", "analysed"], extra=extra
    )


async def confirm_fields(p: Principal, inspection_id: str, keys: list[str]) -> dict[str, Any]:
    insp = await repo.get(p, inspection_id)
    fields = insp.get("fields") or {}
    targets = keys or [k for k, f in fields.items() if f.get("status") == "pending"]
    sets = {
        f"fields.{k}.status": "confirmed"
        for k in targets
        if k in fields and fields[k]["status"] in ("pending", "auto")
    }
    if not sets:
        return insp
    return await repo.update(p, inspection_id, sets, expect_status=["extracted", "analysed"])


async def set_category(p: Principal, inspection_id: str, category: str) -> dict[str, Any]:
    insp = await repo.get(p, inspection_id)
    sets: dict[str, Any] = {"category": category, "category_source": "inspector"}
    if insp["status"] == "analysed":
        sets["analysis_stale"] = True
    return await repo.update(p, inspection_id, sets, expect_status=EDITABLE)


# ---------------------------------------------------------------- analysis


def _values(insp: dict[str, Any]) -> dict[str, str | None]:
    return {k: (f or {}).get("value") for k, f in (insp.get("fields") or {}).items()}


async def _packaging(
    p: Principal, insp: dict[str, Any], record_id: str | None, limit: int
) -> dict[str, Any]:
    if not record_id:
        return {
            "status": "no_reference",
            "summary": "No reference record to compare packaging with.",
            "observations": [],
        }
    rec = await reference.get(record_id)
    versions = [v for v in rec.get("packaging_versions", []) if v.get("images")]
    if not versions:
        return {
            "status": "no_reference_images",
            "summary": "The reference record has no packaging photographs yet.",
            "observations": [],
            "record_id": record_id,
        }
    version = versions[-1]
    ref_imgs: list[images.ImageInput] = []
    for i, im in enumerate(version["images"][:2], start=1):
        data, info = await files.read_bytes("refimages", im["file_id"])
        ref_imgs.append(
            images.ImageInput(
                data,
                (info.get("metadata") or {}).get("content_type", "image/jpeg"),
                im.get("side", ""),
                i,
            )
        )
    uploaded = await load_images(p, insp)
    front = [u for u in uploaded if u.label == "front"] or uploaded[:1]
    await usage.consume_ai(p.uid, limit)
    res = await chain.run_compare(front[:2], ref_imgs, PACKAGING_PROMPT)
    if res.data is None:
        return {
            "status": "not_performed",
            "summary": "AI packaging comparison unavailable; compare visually.",
            "observations": [],
            "record_id": record_id,
            "version": version["label"],
            "attempts": [{k: a[k] for k in ("provider", "ok", "error")} for a in res.attempts],
        }
    obs = []
    for o in (res.data.get("observations") or [])[:12]:
        if isinstance(o, dict) and o.get("observation"):
            sev = o.get("severity") if o.get("severity") in ("info", "warning", "high") else "info"
            obs.append(
                {
                    "area": str(o.get("area") or "Packaging")[:80],
                    "observation": str(o["observation"])[:400],
                    "severity": sev,
                    "photo": o.get("photo") if isinstance(o.get("photo"), int) else None,
                }
            )
    return {
        "status": "compared",
        "summary": str(res.data.get("summary") or "")[:400],
        "observations": obs,
        "provider": res.provider,
        "record_id": record_id,
        "version": version["label"],
        "versions_available": len(versions),
    }


_REF_FINDING = {
    "partial": ("warning", "Partial match"),
    "mismatch": ("high", "Mismatch with reference"),
    "no_record": ("warning", "No reference record"),
    "insufficient": ("warning", "Insufficient information"),
}
_LIC_FINDING = {
    "missing": ("warning", "Licence number not found"),
    "invalid_format": ("high", "Licence format appears invalid"),
    "not_found": ("warning", "Licence not in demo records"),
    "expired": ("high", "Demo record: expired"),
    "suspended": ("high", "Demo record: suspended"),
    "needs_review": ("warning", "Licence holder differs"),
}


def assemble_findings(
    insp: dict[str, Any],
    ref: dict[str, Any],
    lic: dict[str, Any],
    pkg: dict[str, Any],
    results: list[dict[str, Any]],
    previous: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    fields = insp.get("fields") or {}

    def photo_of(key: str) -> int | None:
        return (fields.get(key) or {}).get("source_photo")

    def ai_of(key: str) -> str | None:
        return (fields.get(key) or {}).get("ai_value")

    out: list[dict[str, Any]] = []
    if ref["status"] in _REF_FINDING:
        sev, label = _REF_FINDING[ref["status"]]
        diffs = [r for r in ref.get("comparisons", []) if r["result"] == "differs"]
        out.append(
            {
                "id": "reference",
                "kind": "reference",
                "title": "Reference database match",
                "severity": sev,
                "status_label": label,
                "detail": ref["detail"]
                + (" Differs: " + ", ".join(d["field"] for d in diffs) + "." if diffs else ""),
                "extracted": insp.get("summary", {}).get("product_name"),
                "expected": ref.get("record_label"),
                "evidence_photo": photo_of("product_name"),
                "ai_original": ai_of("product_name"),
            }
        )
    if lic["status"] in _LIC_FINDING:
        sev, label = _LIC_FINDING[lic["status"]]
        out.append(
            {
                "id": "licence",
                "kind": "licence",
                "title": "FSSAI licence (demo check)",
                "severity": sev,
                "status_label": label,
                "detail": lic["detail"],
                "extracted": _values(insp).get("fssai_licence"),
                "evidence_photo": photo_of("fssai_licence"),
                "ai_original": ai_of("fssai_licence"),
            }
        )
    for i, o in enumerate(pkg.get("observations", [])):
        out.append(
            {
                "id": f"packaging-{i + 1}",
                "kind": "packaging",
                "title": f"Packaging: {o['area']}",
                "severity": o["severity"],
                "status_label": "Observation — review",
                "detail": o["observation"],
                "evidence_photo": o.get("photo"),
                "expected": f"Reference version: {pkg.get('version', '')}",
            }
        )
    for r in results:
        if r["result"] not in ("fail", "review"):
            continue
        out.append(
            {
                "id": f"rule-{r['rule_code']}",
                "kind": "claim" if r["claim"] else "compliance",
                "title": r["title"],
                "severity": r["severity"],
                "status_label": "Needs review"
                if r["result"] == "review"
                else "Requirement not met",
                "detail": r["reason"],
                "extracted": r["extracted"],
                "expected": r["requirement"],
                "rule_code": r["rule_code"],
                "rule_reference": r["reference"],
                "evidence_photo": photo_of(r["field"]),
                "ai_original": ai_of(r["field"]),
            }
        )
    prev = {f["id"]: f.get("decision") for f in previous if f.get("decision")}
    for f in out:
        f.setdefault("extracted", None)
        f.setdefault("expected", None)
        f.setdefault("rule_code", None)
        f.setdefault("rule_reference", None)
        f.setdefault("ai_original", None)
        f["decision"] = prev.get(f["id"])
    return out


async def analyse(p: Principal, inspection_id: str) -> dict[str, Any]:
    insp = await repo.get(p, inspection_id)
    if insp["status"] not in ("extracted", "analysed"):
        raise AppError(409, "invalid_state", "Run and review the AI reading first.")
    pending = [k for k, f in (insp.get("fields") or {}).items() if f.get("status") == "pending"]
    if pending:
        raise AppError(
            409,
            "fields_unconfirmed",
            f"Review the remaining {len(pending)} field(s) first.",
            {k: "Needs confirmation" for k in pending},
        )
    if not insp.get("category"):
        raise bad_request("Choose the product category first.")
    cfg = await settings_repo.load()
    vals = _values(insp)
    lic_digits = matching.digits(vals.get("fssai_licence")) or None
    cands = await reference.candidates(
        vals.get("brand"),
        vals.get("product_name"),
        lic_digits,
        matching.digits(vals.get("barcode")) or None,
    )
    ref = matching.match(vals, cands)
    lic_records = (
        await reference.by_licence(lic_digits) if lic_digits and len(lic_digits) == 14 else []
    )
    lic = matching.licence_check(
        vals.get("fssai_licence"), lic_records, vals.get("manufacturer_name")
    )
    pkg = (
        await _packaging(p, insp, ref.get("record_id"), cfg["limits"]["ai_daily_limit_per_user"])
        if ref["status"] in ("exact", "partial", "mismatch")
        else {
            "status": "no_reference",
            "summary": "No reference record to compare packaging with.",
            "observations": [],
        }
    )
    rule_docs = await rules.active_for_category(insp["category"])
    results = compliance.evaluate(rule_docs, vals, date.today())
    findings = assemble_findings(insp, ref, lic, pkg, results, insp.get("findings") or [])
    suggestion = classification.suggest(findings, ref["status"])
    analysis = {
        "at": now(),
        "reference": ref,
        "licence": lic,
        "packaging": pkg,
        "compliance": {
            "results": results,
            "rules_applied": [{"code": r["rule_code"], "version": r["version"]} for r in results],
            "passed": sum(1 for r in results if r["result"] == "pass"),
        },
    }
    return await repo.update(
        p,
        inspection_id,
        {
            "status": "analysed",
            "analysis": analysis,
            "findings": findings,
            "suggestion": suggestion,
            "analysis_stale": False,
        },
        expect_status=["extracted", "analysed"],
    )


async def decide_finding(
    p: Principal, inspection_id: str, finding_id: str, decision: dict[str, Any]
) -> dict[str, Any]:
    insp = await repo.get(p, inspection_id)
    if insp["status"] != "analysed":
        raise AppError(
            409, "invalid_state", "Findings can be reviewed before the report is generated."
        )
    findings = insp.get("findings") or []
    idx = next((i for i, f in enumerate(findings) if f["id"] == finding_id), None)
    if idx is None:
        raise AppError(404, "not_found", "Finding not found.")
    findings[idx]["decision"] = {**decision, "at": now()}
    ref_status = ((insp.get("analysis") or {}).get("reference") or {}).get("status")
    return await repo.update(
        p,
        inspection_id,
        {
            f"findings.{idx}.decision": findings[idx]["decision"],
            "suggestion": classification.suggest(findings, ref_status),
        },
        expect_status=["analysed"],
    )


async def set_decision(
    p: Principal, inspection_id: str, classification_value: str, remarks: str
) -> dict[str, Any]:
    insp = await repo.get(p, inspection_id)
    if insp.get("analysis_stale"):
        raise AppError(
            409, "analysis_stale", "Fields changed after analysis. Run the AI review again first."
        )
    return await repo.update(
        p,
        inspection_id,
        {
            "decision": {"classification": classification_value, "remarks": remarks, "at": now()},
        },
        expect_status=["analysed"],
    )


async def generate_report(p: Principal, inspection_id: str, signature_name: str) -> dict[str, Any]:
    from app.services.report_pdf import build_report

    insp = await repo.get(p, inspection_id)
    if insp["status"] != "analysed" or not insp.get("decision"):
        raise AppError(
            409, "invalid_state", "Select the final classification before generating the report."
        )
    if insp.get("analysis_stale"):
        raise AppError(
            409, "analysis_stale", "Fields changed after analysis. Run the AI review again first."
        )
    originals = await load_images(p, insp, apply_crop=False)
    cfg = await settings_repo.load()
    generated_at = now()
    pdf, pages = build_report(insp, originals, signature_name, generated_at, cfg["general"])
    fid = await files.put(
        "reports",
        pdf,
        f"{inspection_id}.pdf",
        "application/pdf",
        {"owner_uid": p.uid, "inspection_id": inspection_id},
    )
    doc = await repo.update(
        p,
        inspection_id,
        {
            "status": "completed",
            "report": {
                "file_id": fid,
                "generated_at": generated_at,
                "size": len(pdf),
                "signature_name": signature_name,
                "pages": pages,
            },
        },
        expect_status=["analysed"],
    )
    # D-04 / BR-08: originals are deleted once the report (with compressed copies) exists.
    for ph in insp.get("photos", []):
        await files.delete("photos", ph["id"])
    await repo.mark_photos_deleted(p, inspection_id)
    doc["photos_deleted"] = True
    return doc
