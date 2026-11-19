"""Data-access-layer rule: routers must never touch MongoDB directly (master prompt §1.4)."""

from __future__ import annotations

import ast
import pathlib

ROUTERS = pathlib.Path(__file__).resolve().parents[1] / "app" / "routers"
FORBIDDEN_MODULES = ("app.db", "pymongo", "gridfs", "motor", "app.repositories.base")
FORBIDDEN_CALLS = {
    "col",
    "get_db",
    "get_client",
    "bucket",
    "find_one",
    "insert_one",
    "update_one",
    "delete_one",
    "delete_many",
    "update_many",
    "aggregate",
    "count_documents",
}


def test_routers_do_not_access_database_directly() -> None:
    problems: list[str] = []
    for path in ROUTERS.glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.module.startswith(FORBIDDEN_MODULES)
            ):
                problems.append(f"{path.name}: imports {node.module}")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(FORBIDDEN_MODULES):
                        problems.append(f"{path.name}: imports {alias.name}")
            if isinstance(node, ast.Call):
                name = (
                    node.func.attr
                    if isinstance(node.func, ast.Attribute)
                    else getattr(node.func, "id", "")
                )
                if name in FORBIDDEN_CALLS:
                    problems.append(f"{path.name}:{node.lineno} calls {name}()")
    assert not problems, "\n".join(problems)


def test_every_protected_route_uses_auth_dependency() -> None:
    from fastapi.routing import APIRoute

    from app.main import app

    public = {"/health", "/api/v1/public/site-images", "/api/v1/public/site-images/{key}"}
    for route in app.routes:
        if not isinstance(route, APIRoute) or route.path in public:
            continue
        deps = {d.call.__name__ for d in route.dependant.dependencies if d.call}
        flat: set[str] = set()
        stack = list(route.dependant.dependencies)
        while stack:
            d = stack.pop()
            if d.call:
                flat.add(d.call.__name__)
            stack.extend(d.dependencies)
        assert flat & {"token_claims", "current_principal"}, (
            f"{route.path} has no auth dependency ({deps})"
        )
