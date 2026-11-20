"""Route × identity authorization matrix. Writes last-run/authz-matrix.md for SECURITY_AUDIT_REPORT.md."""

from __future__ import annotations

import pathlib
from typing import Any

import httpx

from conftest import Actor
from test_01_authentication import concrete, operations

OUT = pathlib.Path(__file__).parent / "last-run"
SKIP_FOR_ADMINS = ("/storage/cleanup",)  # real side effect on the local DB; covered by backend tests


def test_authorization_matrix(openapi: dict[str, Any], anon: httpx.Client, pending: Actor, user_a: Actor, plain_admin: Actor, admin: Actor) -> None:
    identities = [("ANON", None), ("PENDING", pending), ("INSPECTOR", user_a), ("ADMIN", plain_admin), ("SUPER", admin)]
    lines = ["| Route | " + " | ".join(n for n, _ in identities) + " | Expectation |", "|---|" + "---|" * (len(identities) + 1)]
    violations: list[str] = []
    for method, path in sorted(operations(openapi), key=lambda x: (x[1], x[0])):
        cells = []
        statuses: dict[str, int] = {}
        for name, who in identities:
            if who is not None and name in ("ADMIN", "SUPER") and path.endswith(SKIP_FOR_ADMINS):
                cells.append("–")
                continue
            body = {} if method != "GET" else None
            r = anon.request(method, concrete(path), json=body) if who is None else who.req(method, concrete(path), json=body)
            statuses[name] = r.status_code
            cells.append(str(r.status_code))
        if path in ("/api/v1/me",):
            exp = "any signed-in user"
        elif path.startswith("/api/v1/admin"):
            exp = "admin only"
            for n in ("ANON", "PENDING", "INSPECTOR"):
                if statuses[n] not in (401, 403):
                    violations.append(f"{n} {method} {path} -> {statuses[n]}")
        else:
            exp = "active inspector/admin"
            for n in ("ANON", "PENDING"):
                if statuses[n] not in (401, 403):
                    violations.append(f"{n} {method} {path} -> {statuses[n]}")
        lines.append(f"| `{method} {path}` | " + " | ".join(cells) + f" | {exp} |")
    OUT.mkdir(exist_ok=True)
    (OUT / "authz-matrix.md").write_text("\n".join(lines) + "\n")
    assert not violations, "\n".join(violations)
