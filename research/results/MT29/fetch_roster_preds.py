#!/usr/bin/env python
"""MT29 roster-expansion fetch + convert (Path B: direct Figshare API, md5-gated).

Downloads the published per-WBM-structure formation-energy predictions for the full
universal-MLIP leaderboard from Figshare article 28187990 ("Matbench Discovery - Model
Predictions for Discovery", version 25, published 2026-07-10) and converts each to the
pipeline schema `material_id, e_form_pred` (256,963 WBM rows).

WHY Path B (not the matbench_discovery package Model enum): PyPI's latest
`matbench-discovery` is 1.3.1, which predates the OMat/OAM generation and exposes no
`Model` enum in `matbench_discovery.data`. The Figshare v25 dataset is the same
credential-free source the four frozen legacy anchors came from, so we fetch directly.

CONVERTER RECIPE (validated): every published file carries a `e_form_per_atom_<model>`
column = the MP2020-corrected predicted formation energy on the SAME convention as the
ground-truth `e_form_per_atom_mp2020_corrected`. We take that column (never the
`*_uncorrected` variant) and rename to `e_form_pred`. Verified byte-identical to the
on-disk frozen anchor CSVs for chgnet (max abs diff 0.0 over 256,963 rows).

figshare-202 md5 GATE: Figshare occasionally returns HTTP 202 ("processing") and a naive
download silently writes a 0-byte / partial file. Every download is retried until the
byte size is non-zero AND md5sum == supplied_md5 (per the figshare-202-api-fetch recipe).

CPU/network only. No GPU, no self-inference, no model weights.
"""
import os, sys, json, hashlib, subprocess, time, platform
import numpy as np
import pandas as pd

ARTICLE = 28187990
FIGSHARE_VERSION = 25
NDOWNLOADER = "https://ndownloader.figshare.com/files/{fid}"
OUT_DIR = os.path.expanduser("~/mt_uip_roster25")   # roster inputs, kept separate from frozen ~/mt_uip
WBM = os.path.expanduser("~/mt_stage0/data/2023-12-13-wbm-summary.csv.gz")
N_WBM = 256963
ANCHOR_ONDISK = os.path.expanduser("~/mt_uip")       # frozen legacy-4 for cross-check
HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST_OUT = os.path.join(
    "/home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research/"
    "results_expansion_2026-07-13", "ROSTER25_DATA_MANIFEST.json")

# ---------------------------------------------------------------------------
# ROSTER: short_name -> (figshare_file_id, supplied_md5, generation, klass, note)
#   generation: 'MP'   = trained on MP / MPtrj / MP-relaxed ONLY (pre-additional-materials era)
#               'OMat' = trained on OMat24 / Alexandria(sAlex) / OpenLAM / OAM / OMA (additional-materials era)
#               'special' = proprietary/other training corpus (GNoME) -> reported, excluded from the 2-arm contrast
#   klass: 'anchor' (the 4 frozen legacy UIPs), 'uip' (modern GNN/equivariant UIP), 'classical' (2020-era regression/relaxer baseline)
# Generation tags follow the model's documented training corpus (encoded in the leaderboard
# name: mp/mptrj -> MP; oam/omat/openlam/oma/salex/mpa -> OMat); each tag is auditable from the
# filename + the matbench-discovery model registry.
# ---------------------------------------------------------------------------
ROSTER = {
    # ---- anchors (frozen legacy 4; MP-trained) ----
    "chgnet":         (51607268, "e1119bcc0ba012f898a1e8d11c6ad2de", "MP",   "anchor", "CHGNet 0.3.0 (MPtrj)"),
    "m3gnet":         (51607277, "b309e4a28d8f91814e7fb7ca1160bc8c", "MP",   "anchor", "M3GNet (MP)"),
    "mace_mp_0":      (51607280, "f7560864b7e01bb874cce23d24e79b27", "MP",   "anchor", "MACE-MP-0 (MPtrj); frozen anchor 'mace'"),
    "orb_mptrj":      (51607310, "f7a397217a85955bdc45e51f6a434f73", "MP",   "anchor", "Orb-v2 MPtrj-only (MPtrj); frozen anchor 'orb'"),
    # ---- classical 2020-era baselines (MP-trained) ----
    "cgcnn":          (51607271, "f09ab902adc5dddc835bea8a12b2df5f", "MP",   "classical", "CGCNN ens=10"),
    "cgcnn_p":        (51607274, "643a08063075ee1e08bb4590b7ab6cdb", "MP",   "classical", "CGCNN+P perturb=5"),
    "megnet":         (51607286, "15377f3afc773d651828304593ce12e7", "MP",   "classical", "MEGNet"),
    "wrenformer":     (51607298, "e97f674e75592c1a214c154e25107280", "MP",   "classical", "Wrenformer ens=10"),
    "voronoi_rf":     (51607295, "00c5673afe34dcdd5a951ee451a2a462", "MP",   "classical", "Voronoi random forest"),
    "alignn":         (51607262, "c7a1cb4f2c3db99e2124a17ce0ac8554", "MP",   "classical", "ALIGNN"),
    "bowsr_megnet":   (51607265, "f2375f53cdd947b38a55c7c2b6925779", "MP",   "classical", "BOWSR-MEGNet"),
    # ---- modern MP / MPtrj-trained UIPs ----
    "mattersim":      (51607304, "71e876fdc0a30358a9993c12d1fb02e3", "MP",   "uip", "MatterSim v1 5M (MPtrj)"),
    "sevennet_0":     (51607289, "967e72b791a24263b9ea4b759c9f64f8", "MP",   "uip", "SevenNet-0 (MPtrj)"),
    "sevennet_l3i5":  (51607292, "f4bba4fe40115c3d3a380e53ddc1389a", "MP",   "uip", "SevenNet-l3i5 (MPtrj)"),
    "grace_2l_mptrj": (51607319, "1e016a258e6752c1cbf8d94724f6627e", "MP",   "uip", "GRACE-2L-MPtrj r6"),
    "eqv2_s_mp":      (51607313, "bfbcec81b6dfbf2d3a569c4d93d86cda", "MP",   "uip", "eqV2-S-DeNS-MP"),
    "esen_mp":        (53054669, "6045fe6e7ca6ccde450d13929634abc4", "MP",   "uip", "eSEN-30M-MP"),
    "dpa3_v1_mptrj":  (52057082, "2546f9ac577e4a4e3abee720a991b5eb", "MP",   "uip", "DPA3-v1-MPtrj"),
    "dpa3_v2_mptrj":  (53018801, "ed31fd4c1f1979534094dd33a72bd8c1", "MP",   "uip", "DPA3-v2-MPtrj"),
    "matris_mptrj":   (53000174, "eabc8c9046a068271b483b1750f60ffd", "MP",   "uip", "MatRIS-0.5.0-MPtrj"),
    "matris_10m_mp":  (59233859, "17eeacc2bc71919899cbba03611ad59e", "MP",   "uip", "MatRIS-10m-MP"),
    "nequip_mp":      (57574483, "1e5e18ca9ec3173243f77c0a58dd354e", "MP",   "uip", "NequIP-MP-L-0.1"),
    "nequix_mp":      (57262712, "b2896ac7db2d4bd87595347dccb15d62", "MP",   "uip", "Nequix-mp-1"),
    "hienet":         (55909421, "456ab3c4d7cf47a04b492c0bccd566dd", "MP",   "uip", "HIENet (MPtrj)"),
    "allegro_mp":     (57575095, "26a7104fb04891f3ce97e9d625bdddad", "MP",   "uip", "Allegro-MP-L-0.1"),
    "eqnorm_mptrj":   (55546649, "77c84e44c1d9a0782eb480c1c8ebf5ec", "MP",   "uip", "eqnorm-mptrj"),
    "alphanet_mp":    (52869026, "5d792a7fca2f1c8d02d2dc5948a1bc95", "MP",   "uip", "AlphaNet-MP"),
    # ---- OMat / OAM / OpenLAM / sAlex-trained UIPs (the contrast arm) ----
    "mace_mpa":       (51607283, "35704766adccc536abce620dfc773f6d", "OMat", "uip", "MACE-MPA-0 (MP+sAlex)"),
    "orb_v2_omat":    (51607307, "d00f381dac27d367133452a24f17a4e5", "OMat", "uip", "Orb-v2 (OMat)"),
    "orb_v3":         (53461037, "78077b6dfca8c7dd75e9d42debefbeb9", "OMat", "uip", "Orb-v3 (OMat+MPtrj, con-inf-mpa)"),
    "eqv2_m_omat":    (51607316, "86642db564ecf51263e2c0a553603154", "OMat", "uip", "eqV2-M-OMat (OMat24+MP+sAlex)"),
    "esen_oam":       (53054666, "24fb43481b18de790a25cd7390e19673", "OMat", "uip", "eSEN-30M-OAM"),
    "grace_1l_oam":   (52204898, "74adff441dafe8284cb07886579a3512", "OMat", "uip", "GRACE-1L-OAM"),
    "grace_2l_oam":   (52204901, "faab80007c7849e59509e4ed6e2f8b3e", "OMat", "uip", "GRACE-2L-OAM"),
    "grace_2l_oam_l": (59046947, "d5df9111eb0a6e55648a02df6eb5415c", "OMat", "uip", "GRACE-2L-OAM-L"),
    "grace_3l_oam":   (66505397, "191365046bbdf54692d87e9587f17400", "OMat", "uip", "GRACE-3L-OAM-L"),
    "dpa3_v1_openlam":(52057085, "ed95c35a9646d2658bead2260050b7ef", "OMat", "uip", "DPA3-v1-OpenLAM"),
    "dpa3_v2_openlam":(53018804, "7ac30d578026b62eda7badaad6704e52", "OMat", "uip", "DPA3-v2-OpenLAM"),
    "dpa31_ft":       (55410167, "b3ace9a07c898ddd873bec1890939058", "OMat", "uip", "DPA-3.1-3m-ft (OpenLAM)"),
    "matris_oam":     (59233856, "f747fbfb1ac7259d930fce415f46bc58", "OMat", "uip", "MatRIS-10m-OAM"),
    "nequip_oam":     (57574462, "d6c5679e0cf47d09b6211552e0734ca6", "OMat", "uip", "NequIP-OAM-L-0.1"),
    "nequip_oam_xl":  (60007793, "fdc6b855d30d40e368119a469b93de1f", "OMat", "uip", "NequIP-OAM-XL-0.1"),
    "allegro_oam":    (57574801, "8290925829369f8e763fb9eeb1623976", "OMat", "uip", "Allegro-OAM-L-0.1"),
    "alphanet_oma":   (56871809, "4216cae0261a1ed6441f2197bd90d7d3", "OMat", "uip", "AlphaNet-OMA (2025-07-24)"),
    # NOTE: GNoME (Figshare 51607301) is EXCLUDED — its published file exposes only a relaxed
    # total energy (`e_gnome_after_relax`), not a MP2020-corrected formation energy, so it cannot
    # be converted to the pipeline schema without re-deriving formation energies (out of scope).
}

ANCHORS = ["chgnet", "m3gnet", "mace_mp_0", "orb_mptrj"]
ANCHOR_ONDISK_NAME = {"chgnet": "chgnet", "m3gnet": "m3gnet", "mace_mp_0": "mace", "orb_mptrj": "orb"}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download_gated(fid, want_md5, dest, tries=4):
    """Download with the figshare-202 md5 gate; retry on 0-byte/partial/202."""
    url = NDOWNLOADER.format(fid=fid)
    if os.path.exists(dest) and os.path.getsize(dest) > 0 and md5_of(dest) == want_md5:
        return True, os.path.getsize(dest)  # already cached & verified
    for attempt in range(1, tries + 1):
        subprocess.run(["curl", "-sL", "--max-time", "300", "-o", dest, url], check=False)
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            got = md5_of(dest)
            if got == want_md5:
                return True, os.path.getsize(dest)
        time.sleep(4 * attempt)
    return False, (os.path.getsize(dest) if os.path.exists(dest) else 0)


def pred_column(df):
    """Pick the MP2020-corrected predicted-formation-energy column across the several published
    schemas: single model column `e_form_per_atom_<model>`, or an ensemble mean `*_pred_ens`.
    Excludes the ground truth, `*_uncorrected`, aleatoric/epistemic/std columns, ensemble members
    (`*_pred_n<k>`), and index columns."""
    cols = list(df.columns)

    def bad(c):
        cl = c.lower()
        return ("uncorrected" in cl or "_ale" in cl or "aleatoric" in cl or "std" in cl
                or "epistemic" in cl or cl.startswith("unnamed")
                or c == "e_form_per_atom_mp2020_corrected")

    # 1) explicit ensemble mean of the predicted formation energy (cgcnn/wrenformer-style)
    ens = [c for c in cols if c.startswith("e_form_per_atom") and c.endswith("_pred_ens") and not bad(c)]
    if ens:
        named = [c for c in ens if "mp2020_corrected" not in c]  # prefer model-named ens if present
        return (named or ens)[0]
    # 2) single model-named formation-energy column. Accept `e_form_per_atom_<x>` and the
    #    `pred_e_form_per_atom_<x>` variant (eSEN-style). grace's `_uncorrected` filtered by bad().
    simple = [c for c in cols if "e_form_per_atom" in c and not bad(c)
              and "_pred_n" not in c and not c.endswith("_pred")]
    if len(simple) == 1:
        return simple[0]
    raise ValueError(f"ambiguous prediction column among {cols} -> ens={ens} simple={simple}")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(MANIFEST_OUT), exist_ok=True)
    raw_dir = os.path.join(OUT_DIR, "_raw")
    os.makedirs(raw_dir, exist_ok=True)

    wbm_ids = set(pd.read_csv(WBM, usecols=["material_id"])["material_id"])
    print(f"WBM material_ids: {len(wbm_ids)} (expect {N_WBM})", flush=True)

    records = {}
    failures = []
    anchor_crosscheck = {}
    for short, (fid, md5, gen, klass, note) in ROSTER.items():
        raw = os.path.join(raw_dir, f"{short}.csv.gz")
        out = os.path.join(OUT_DIR, f"{short}_pred.csv")

        if klass == "anchor":
            # ANCHORS use the FROZEN on-disk CSV (byte-identical to the manuscript headline).
            # The v25 file is still fetched to record version drift, but is NOT the canonical input:
            # v25 re-ran m3gnet/mace/orb upstream (~0.03-0.05 eV/atom aggregate shift), so using it
            # would silently change the frozen anchor numbers.
            odp = os.path.join(ANCHOR_ONDISK, f"{ANCHOR_ONDISK_NAME[short]}_pred.csv")
            frozen = pd.read_csv(odp)[["material_id", "e_form_pred"]].dropna().drop_duplicates("material_id")
            frozen.to_csv(out, index=False)
            outsha = sha256(out)
            coverage = len(frozen)
            drift = None
            ok, sz = download_gated(fid, md5, raw)
            if ok:
                dfv = pd.read_csv(raw)
                colv = pred_column(dfv)
                v = dfv[["material_id", colv]].rename(columns={colv: "v25"}).dropna().drop_duplicates("material_id")
                mrg = frozen.rename(columns={"e_form_pred": "frozen"}).merge(v, on="material_id", how="inner")
                dd = (mrg["frozen"] - mrg["v25"]).abs()
                drift = dict(n=len(mrg), mean_abs=float(dd.mean()), median_abs=float(dd.median()),
                             max_abs=float(dd.max()), identical=bool(dd.max() == 0.0), v25_rows=len(v))
                anchor_crosscheck[short] = drift
            rec = dict(figshare_id=fid, supplied_md5=md5, generation=gen, klass=klass, note=note,
                       source="frozen_ondisk", pred_col="e_form_pred(frozen)", out_rows=coverage,
                       coverage_of_wbm=round(coverage / N_WBM, 6), out_sha256=outsha,
                       v25_drift=drift)
            records[short] = rec
            di = "identical" if (drift and drift["identical"]) else (f"drift mean|d|={drift['mean_abs']:.3g}" if drift else "no-v25")
            print(f"  OK*   {short:16s} [{gen:7s}/{klass:9s}] FROZEN rows={coverage}  v25:{di}", flush=True)
            continue

        ok, sz = download_gated(fid, md5, raw)
        if not ok:
            print(f"  FAIL  {short:16s} md5-gate failed (size={sz})", flush=True)
            failures.append(short)
            continue
        df = pd.read_csv(raw)
        try:
            col = pred_column(df)
        except ValueError as e:
            print(f"  FAIL  {short:16s} {e}", flush=True)
            failures.append(short)
            continue
        conv = df[["material_id", col]].rename(columns={col: "e_form_pred"})
        conv = conv[conv["material_id"].isin(wbm_ids)].drop_duplicates("material_id")
        n_nonnan = int(conv["e_form_pred"].notna().sum())
        conv = conv.dropna(subset=["e_form_pred"])
        conv.to_csv(out, index=False)
        outsha = sha256(out)
        coverage = len(conv)
        rec = dict(figshare_id=fid, supplied_md5=md5, generation=gen, klass=klass, note=note,
                   source="figshare_v25", pred_col=col, raw_bytes=sz, out_rows=coverage,
                   out_nonnan=n_nonnan, coverage_of_wbm=round(coverage / N_WBM, 6), out_sha256=outsha)
        records[short] = rec
        flag = "" if coverage == N_WBM else f"  <-- coverage {coverage}/{N_WBM} ({coverage/N_WBM:.4f})"
        print(f"  OK    {short:16s} [{gen:7s}/{klass:9s}] col={col:34s} rows={coverage}{flag}", flush=True)

    manifest = dict(
        article=ARTICLE, figshare_version=FIGSHARE_VERSION, out_dir=OUT_DIR, n_wbm=N_WBM,
        wbm_sha256=sha256(WBM),
        n_models=len(records), n_failures=len(failures), failures=failures,
        generations={g: sorted([s for s, r in records.items() if r["generation"] == g])
                     for g in ("MP", "OMat", "special")},
        anchor_crosscheck=anchor_crosscheck,
        models=records,
        versions=dict(python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__),
        platform=platform.platform(),
    )
    with open(MANIFEST_OUT, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nWrote {MANIFEST_OUT}")
    print(f"models converted: {len(records)}  failures: {failures}")
    print("generation split:",
          {g: len(v) for g, v in manifest["generations"].items()})
    allident = all(v["identical"] for v in anchor_crosscheck.values())
    print(f"ALL 4 ANCHORS byte-identical to frozen on-disk inputs: {allident}")


if __name__ == "__main__":
    main()
