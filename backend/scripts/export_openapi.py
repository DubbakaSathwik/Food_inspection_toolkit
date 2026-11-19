"""Write the OpenAPI schema used to generate frontend types: `uv run python -m scripts.export_openapi`."""

from __future__ import annotations

import json
import pathlib

from app.main import app

if __name__ == "__main__":
    out = pathlib.Path(__file__).resolve().parents[1] / "openapi.json"
    out.write_text(json.dumps(app.openapi(), indent=1, sort_keys=True))
    print(f"wrote {out}")
