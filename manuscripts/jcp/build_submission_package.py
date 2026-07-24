#!/usr/bin/env python3
"""Build and verify the flat JCP LaTeX source package."""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import tempfile
import zipfile
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILD_DATE = date(2026, 7, 23)
STAMP = (2026, 7, 23, 12, 0, 0)
STEM = f"jcp_submission_latex_{BUILD_DATE.isoformat()}"

SOURCES = {
    "paper_jcp.tex": HERE / "paper_jcp.tex",
    "paper_jcp.bbl": HERE / "paper_jcp.bbl",
    "refs.bib": HERE / "refs.bib",
    "shared.bib": HERE / "shared.bib",
    "figures/fig0_overview.pdf": HERE.parent / "figures" / "fig0_overview.pdf",
    "figures/F1_daf_coverage.pdf": HERE.parent / "figures" / "F1_daf_coverage.pdf",
    "figures/F2_interaction_heatmap.pdf": HERE.parent / "figures" / "F2_interaction_heatmap.pdf",
    "figures/F3_robustness_panel.pdf": HERE.parent / "figures" / "F3_robustness_panel.pdf",
    "figures/F4_shuffle_null.pdf": HERE.parent / "figures" / "F4_shuffle_null.pdf",
    "figures/F5_committee_variance.pdf": HERE.parent / "figures" / "F5_committee_variance.pdf",
    "figures/e2_family_blocked_ci.pdf": HERE.parent / "figures" / "e2_family_blocked_ci.pdf",
    "figures/candidate_cases.pdf": HERE / "candidate_cases.pdf",
}

FORBIDDEN_MEMBER_PARTS = (
    ".bak",
    "_archive",
    "PORTAL_PACK",
    "cover_letter.md",
    "DESK-CHECK",
    "FINAL-VALIDATION",
    ".omc",
    ".claude",
)
FORBIDDEN_TEXT = re.compile(
    r"/home/|/Users/|TODO(?:-USER)?|FIXME|same-session|audit-trail|"
    r"self-inferr|self-inference|harness artifact|contaminated earlier run|"
    r"self-reported|fallback kit|careful-adopt|venue switch|GBP\s*2[, ]?200",
    re.IGNORECASE,
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_readme(path: Path) -> None:
    path.write_text(
        "The Journal of Chemical Physics source package\n"
        f"Built from the active manuscript source on {BUILD_DATE.strftime('%d %B %Y')}.\n\n"
        "Build command:\n"
        "  latexmk -pdf -interaction=nonstopmode -halt-on-error paper_jcp.tex\n\n"
        "The compiled manuscript PDF and cover letter are uploaded separately.\n"
        "This package contains the manuscript source, bibliography, compiled BBL,\n"
        "and exactly the eight referenced figure PDFs. SHA256SUMS covers every\n"
        "payload member except SHA256SUMS itself.\n",
        encoding="utf-8",
    )


def zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, STAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def main() -> None:
    missing = [str(path) for path in SOURCES.values() if not path.is_file()]
    if missing:
        raise SystemExit("Missing package inputs:\n" + "\n".join(missing))

    tex = SOURCES["paper_jcp.tex"].read_text(encoding="utf-8")
    referenced = set(re.findall(r"\\includegraphics(?:\[[^]]*\])?\{([^}]+\.pdf)\}", tex))
    packaged_figures = {Path(name).name for name in SOURCES if name.startswith("figures/")}
    if referenced != packaged_figures:
        raise SystemExit(
            f"Figure allowlist mismatch: referenced={sorted(referenced)}, "
            f"packaged={sorted(packaged_figures)}"
        )

    zip_path = HERE / f"{STEM}.zip"
    sidecar = HERE / f"{STEM}.sha256"
    with tempfile.TemporaryDirectory(prefix=f"{STEM}-") as tmp:
        stage = Path(tmp)
        for member, source in SOURCES.items():
            target = stage / member
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        write_readme(stage / "README.txt")

        payload = sorted([*SOURCES, "README.txt"])
        for member in payload:
            if any(part.lower() in member.lower() for part in FORBIDDEN_MEMBER_PARTS):
                raise SystemExit(f"Forbidden package member: {member}")
            path = stage / member
            if path.suffix.lower() in {".tex", ".bib", ".bbl", ".txt"}:
                match = FORBIDDEN_TEXT.search(path.read_text(encoding="utf-8", errors="replace"))
                if match:
                    raise SystemExit(f"Forbidden text {match.group()!r} in {member}")

        sums = stage / "SHA256SUMS"
        sums.write_text(
            "".join(f"{sha256(stage / member)}  {member}\n" for member in payload),
            encoding="utf-8",
        )
        members = sorted([*payload, "SHA256SUMS"])
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for member in members:
                archive.writestr(zip_info(member), (stage / member).read_bytes())

    with zipfile.ZipFile(zip_path) as archive:
        if archive.testzip() is not None:
            raise SystemExit("ZIP CRC verification failed")
        names = archive.namelist()
        if names != sorted([*SOURCES, "README.txt", "SHA256SUMS"]):
            raise SystemExit(f"Unexpected ZIP members: {names}")

    sidecar.write_text(f"{sha256(zip_path)}  {zip_path.name}\n", encoding="utf-8")
    subprocess.run(["sha256sum", "-c", sidecar.name], cwd=HERE, check=True)
    print(f"built {zip_path.name} ({zip_path.stat().st_size} bytes)")
    print(f"sha256 {sha256(zip_path)}")


if __name__ == "__main__":
    main()
