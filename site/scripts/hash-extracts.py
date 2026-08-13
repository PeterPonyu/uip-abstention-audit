#!/usr/bin/env python3
"""Extract-hash job. Hashes site/data/*.json; no-ops with a log if empty."""

from __future__ import annotations

import hashlib
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
files = sorted(p for p in DATA.glob("*.json"))
if not files:
    print("no extracts yet")
    raise SystemExit(0)
for path in files:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    print(f"{digest}  {path.name}")
sidecar = DATA / "extract.sha256"
if sidecar.exists():
    print(f"sidecar  {sidecar.name}  {sidecar.stat().st_size} bytes")
else:
    print("sidecar missing (allowed if no extracts yet)")
