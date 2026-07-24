#!/usr/bin/env python3
"""Build a sanitized public release tree from an explicit file allowlist."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path, PurePosixPath

REPO = Path(__file__).resolve().parent.parent
ALLOWLIST = REPO / "PUBLIC_RELEASE_FILES.txt"
TEXT_SUFFIXES = {".cff", ".json", ".md", ".py", ".R", ".sh", ".tex", ".txt", ".bib", ".bbl", ""}
FORBIDDEN_PATH_PARTS = {
    ".claude", ".omc", "_archive", "archive", "notes", "digital_discovery", "jcim",
}
FORBIDDEN_NAMES = {
    "AGENTS.md", "FABLE-HANDOFF.md", "NEXT-EXPERIMENTS.md", "RUNME_CONTAINER.md",
    "PORTAL_PACK.txt", "DESK-CHECK-JCP-2026-07-17.md", "FINAL-VALIDATION-JCP-2026-07-18.md",
}
FORBIDDEN_CONTENT = re.compile(
    r"/home/zeyufu|/Users/|TODO(?:-USER)?|FIXME|careful-adopt|fallback kit|"
    r"venue switch|GBP\s*2[, ]?200|same-session|audit-trail|self-inferr|"
    r"self-inference|harness artifact|contaminated earlier run|self-reported|"
    r"FABLE-HANDOFF|AGENTS\.md",
    re.IGNORECASE,
)
PATH_REPLACEMENTS = {
    "/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research": "$REPO_ROOT",
    "/home/zeyufu/Desktop/ml-reliability-research/reliability-commons": "$VENDORED_RELMETRICS",
    "/home/zeyufu": "$HOME",
}
CONTENT_EXEMPT = {
    "tools/build_release.py",  # scanner definitions necessarily contain forbidden patterns
    "manuscripts/jcp/build_submission_package.py",  # JCP package scanner definitions
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def entries() -> list[str]:
    result: list[str] = []
    for raw in ALLOWLIST.read_text(encoding="utf-8").splitlines():
        item = raw.strip()
        if not item or item.startswith("#"):
            continue
        posix = PurePosixPath(item)
        if posix.is_absolute() or ".." in posix.parts:
            raise SystemExit(f"Unsafe allowlist path: {item}")
        if any(part in FORBIDDEN_PATH_PARTS for part in posix.parts) or posix.name in FORBIDDEN_NAMES:
            raise SystemExit(f"Forbidden allowlist member: {item}")
        if item in result:
            raise SystemExit(f"Duplicate allowlist member: {item}")
        result.append(item)
    if result != sorted(result):
        raise SystemExit("PUBLIC_RELEASE_FILES.txt must be sorted")
    return result


def normalized_bytes(relative: str, source: Path) -> bytes:
    if source.suffix not in TEXT_SUFFIXES:
        return source.read_bytes()
    text = source.read_text(encoding="utf-8")
    if source.suffix == ".json":
        for old, new in PATH_REPLACEMENTS.items():
            text = text.replace(old, new)
        json.loads(text)
    if relative not in CONTENT_EXEMPT:
        match = FORBIDDEN_CONTENT.search(text)
        if match:
            raise SystemExit(f"Forbidden content {match.group()!r} in {relative}")
    return text.encode("utf-8")


def build(destination: Path) -> None:
    members = entries()
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    manifest: list[dict[str, object]] = []
    for relative in members:
        source = REPO / relative
        if not source.is_file():
            raise SystemExit(f"Missing allowlisted file: {relative}")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(normalized_bytes(relative, source))
        manifest.append({"path": relative, "bytes": target.stat().st_size, "sha256": digest(target)})
    release_manifest = destination / "RELEASE_MANIFEST.json"
    release_manifest.write_text(
        json.dumps({"version": "0.3.0", "files": manifest}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"built {destination} with {len(manifest)} allowlisted files")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    build(args.destination.resolve())


if __name__ == "__main__":
    main()
