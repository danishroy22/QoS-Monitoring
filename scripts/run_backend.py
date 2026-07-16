#!/usr/bin/env python
"""Run the FastAPI backend from the repository root.

Usage:
    python scripts/run_backend.py                # http://localhost:8000
    python scripts/run_backend.py --reload
    python scripts/run_backend.py --port 9000
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"

# `app.*` imports resolve from the backend directory; `backend.simulator`
# resolves from the project root. Expose both to the (possibly reloaded) worker.
for path in (str(ROOT), str(BACKEND)):
    if path not in sys.path:
        sys.path.insert(0, path)

existing = os.environ.get("PYTHONPATH", "")
os.environ["PYTHONPATH"] = os.pathsep.join(
    p for p in (str(ROOT), str(BACKEND), existing) if p
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the QoS monitoring backend")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        app_dir=str(BACKEND),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
