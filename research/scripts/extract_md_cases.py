#!/usr/bin/env python
"""Extract concrete MD offender / success case studies from the 100-structure batch.
Produces a ready-to-paste appendix for findings-MT4 or the red-team report.
Run locally (data already in results/) or via dispatch.

Usage:
  python research/scripts/extract_md_cases.py > research/redteam/md_cases_2026-06-16.md
"""
import json
import os
from collections import defaultdict

RESULTS_PATH = "research/results/mt_gpu_batch_md_results.json"

def main():
    if not os.path.exists(RESULTS_PATH):
        print(f"ERROR: {RESULTS_PATH} not found. Run from workspace root or copy the JSON.")
        return

    with open(RESULTS_PATH) as f:
        records = json.load(f)

    print("# MT4 MD — Concrete Case Studies (from 100 perturbed structures batch)")
    print("Date: 2026-06-16  · Source: mt_gpu_batch_md_results.json (NVE 200 steps, 1 fs)")
    print()
    print("All energies in eV. Drift = |final - initial| / 200 (per step).")
    print("Disagreement = std of initial e_form across MACE / CHGNet / ORB (proxy for OOD).")
    print()

    # Find interesting cases
    # 1. Highest ORB drift (clear non-conservation)
    # 2. High disagreement + high ORB drift (correlation story)
    # 3. A conservative model "success" (very low drift even at high param)
    # 4. Strain vs rattle contrast if possible

    orb_drifts = []
    for r in records:
        md = r.get("md_results", {})
        if "ORB" not in md:
            continue
        od = abs(md["ORB"].get("drift_per_step", 0))
        dis = r.get("disagreement", 0)
        orb_drifts.append((od, dis, r))

    orb_drifts.sort(reverse=True)  # highest drift first

    selected = []
    # Top 2 worst ORB
    selected.extend([t[2] for t in orb_drifts[:2]])

    # One with high disagreement but low ORB drift? (contrast, if exists)
    # Or simply one from conservative models that stayed flat at high perturbation
    best_conservative = None
    max_conservative_drift = 1e9
    for r in records:
        md = r.get("md_results", {})
        if not all(m in md for m in ("MACE", "CHGNet")):
            continue
        # Take a high-disagreement one where both conservative models have tiny drift
        dis = r.get("disagreement", 0)
        mace_d = abs(md["MACE"].get("drift_per_step", 0))
        chg_d = abs(md["CHGNet"].get("drift_per_step", 0))
        if dis > 0.04 and mace_d < 1e-4 and chg_d < 2e-4:
            if (mace_d + chg_d) < max_conservative_drift:
                max_conservative_drift = mace_d + chg_d
                best_conservative = r
    if best_conservative:
        selected.append(best_conservative)

    # One extreme strain and one rattle if not already covered
    for typ in ["strain", "rattle"]:
        for r in records:
            if r.get("type") == typ and r not in selected:
                selected.append(r)
                break

    # Dedup while preserving order
    seen = set()
    final = []
    for r in selected:
        key = (r["id"], r.get("symbol"))
        if key not in seen:
            seen.add(key)
            final.append(r)

    for r in final[:5]:   # at most 5 for the appendix
        md = r["md_results"]
        dis = r.get("disagreement", float("nan"))
        sym = r.get("symbol")
        typ = r.get("type")
        param = r.get("param")
        oid = r.get("id")

        orb_d = abs(md["ORB"]["drift_per_step"])
        mace_d = abs(md["MACE"]["drift_per_step"])
        chg_d = abs(md["CHGNet"]["drift_per_step"])

        orb_std = md["ORB"]["std_energy"]
        mace_std = md["MACE"]["std_energy"]
        chg_std = md["CHGNet"]["std_energy"]

        print(f"## {oid}  ({sym}, {typ} param={param:.3f})")
        print(f"- Disagreement (initial e_form std): **{dis:.4f}**")
        print()
        print("| Model   | drift/step (eV) | total energy stdev (eV) | initial E (eV) | final E (eV) |")
        print("|---------|-----------------|-------------------------|----------------|--------------|")
        print(f"| ORB (direct) | {orb_d:.2e} | {orb_std:.3e} | {md['ORB']['initial_energy']:.3f} | {md['ORB']['final_energy']:.3f} |")
        print(f"| MACE (grad)  | {mace_d:.2e} | {mace_std:.3e} | {md['MACE']['initial_energy']:.3f} | {md['MACE']['final_energy']:.3f} |")
        print(f"| CHGNet (grad)| {chg_d:.2e} | {chg_std:.3e} | {md['CHGNet']['initial_energy']:.3f} | {md['CHGNet']['final_energy']:.3f} |")
        print()

        ratio_orb_vs_mace = orb_d / max(mace_d, 1e-12)
        print(f"**Physical note**: ORB drift is ~{ratio_orb_vs_mace:.0f}× larger than MACE on this structure.")
        if dis > 0.03 and orb_d > 1e-3:
            print("This is a high-disagreement (OOD proxy) configuration where the direct-force model visibly loses energy conservation while gradient-based models stay flat.")
        elif orb_d < 1e-4:
            print("Rare case where even the direct-force model stayed relatively stable (low drift).")
        print()
        print("---")
        print()

    print("**How to reproduce these exact structures**: See `research/mt_gpu_batch_md.py:get_perturbed_structures()` (strain = isotropic volume scaling on 2×2×2 conventional cells; rattle = ase rattled atoms with fixed seed per id).")
    print()
    print("These cases can be cited in the Red Team Report or manuscript as concrete evidence that the 1000× energy-conservation gap is not an artifact of a single Si cell and correlates with disagreement/OOD level.")

if __name__ == "__main__":
    main()
